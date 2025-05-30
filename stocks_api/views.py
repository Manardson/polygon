from datetime import date, timedelta, datetime

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.exceptions import ParseError, NotFound
from rest_framework.permissions import IsAdminUser, AllowAny,  IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from rest_framework import status, viewsets, permissions, filters

import uuid

from .models import SignificantEvent, StockSymbol, PriceUpdate
from .serializers import SignificantEventSerializer, StockSymbolSerializer, PriceUpdateSerializer
from .services.polygon_service import PolygonService
from .services.analysis_service import StockAnalysisService
from .tasks import fetch_and_process_stock_data_task

class SignificantEventViewSet(viewsets.ReadOnlyModelViewSet): # ReadOnly, events created by background task
    """
    API endpoint to query significant stock price change events.
    Supports filtering by:
    - symbol__ticker (e.g., ?symbol__ticker=GOOGL)
    - event_type (e.g., ?event_type=PRICE_INCREASE)
    - timestamp__gte (e.g., ?timestamp__gte=2023-01-01T00:00:00Z)
    - timestamp__lte
    Supports pagination.
    """
    queryset = SignificantEvent.objects.all().select_related('symbol').order_by('-timestamp')
    serializer_class = SignificantEventSerializer
    permission_classes = [permissions.IsAuthenticated] # Requires JWT token

    # Filtering
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = {
        'symbol__ticker': ['exact', 'in'],
        'event_type': ['exact'],
        'timestamp': ['gte', 'lte', 'exact', 'date__gte', 'date__lte'] # date__gte for just date part
    }
    ordering_fields = ['timestamp', 'symbol__ticker', 'event_type']
    ordering = ['-timestamp'] # Default ordering

class StockSymbolViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint to query available stock symbols.
    """
    queryset = StockSymbol.objects.all().order_by('ticker')
    serializer_class = StockSymbolSerializer
    permission_classes = [permissions.IsAuthenticated]

    filter_backends = [filters.SearchFilter]
    search_fields = ['ticker', 'name']

class PriceHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint to query price history for a specific stock symbol.
    Supports filtering by:
    - symbol__ticker (required, e.g., ?symbol__ticker=GOOGL)
    - timestamp__gte (e.g., ?timestamp__gte=2023-01-01T00:00:00Z)
    - timestamp__lte
    Supports pagination.
    """
    serializer_class = PriceUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]

    # Filtering
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = {
        'symbol__ticker': ['exact'],
        'timestamp': ['gte', 'lte', 'exact', 'date__gte', 'date__lte']
    }
    ordering_fields = ['timestamp']
    ordering = ['timestamp']  # Default ordering - oldest to newest

    def get_queryset(self):
        """
        This view should return price history for a specific symbol.
        Symbol ticker is required.
        """
        queryset = PriceUpdate.objects.all().select_related('symbol')

        # Require symbol__ticker parameter
        symbol_ticker = self.request.query_params.get('symbol__ticker', None)
        if symbol_ticker is None:
            return PriceUpdate.objects.none()  # Return empty queryset if no symbol specified

        return queryset

class EventSummaryView(APIView):
    """
    API endpoint to get a summary of significant events.
    Supports days parameter to specify the time period (default: 7 days).
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, format=None):
        days = int(request.query_params.get('days', 7))
        analysis_service = StockAnalysisService()
        summary = analysis_service.get_significant_events_summary(days=days)
        return Response(summary)

# @method_decorator(login_required, name='dispatch')
class QueryTestPageView(TemplateView):
   template_name = "stocks_api/query_test_page.html"


class FetchLatestStockDataView(APIView):
    """
    Manually triggers the Celery task to fetch and process latest stock data.
    Requires admin privileges.
    """
    permission_classes = [IsAdminUser] # Only admins can trigger this

    def post(self, request, *args, **kwargs):
        try:
            # specific tickers or use default
            # task_id = str(uuid.uuid4()) # Generate a unique ID for this call
            # For Celery, the task_id is part of the AsyncResult object.
            async_result = fetch_and_process_stock_data_task.delay() # Extra arguments
            return Response(
                {"message": "Stock data fetch task initiated.", "task_id": async_result.id},
                status=status.HTTP_202_ACCEPTED
            )
        except Exception as e:
            # Log the exception e
            return Response(
                {"error": "Failed to initiate stock data fetch task.", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class DailyAggregatesView(APIView):
    """
    Retrieves daily Open, High, Low, Close (OHLC) data for a given stock symbol
    from Polygon.io for a specified date range.
    Query parameters:
    - symbol (required): The stock ticker (e.g., GOOGL).
    - date_from (optional): Start date (YYYY-MM-DD). Defaults to 30 days ago.
    - date_to (optional): End date (YYYY-MM-DD). Defaults to yesterday.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        symbol = request.query_params.get('symbol')
        if not symbol:
            return Response({"error": "Symbol query parameter is required."}, status=status.HTTP_400_BAD_REQUEST)

        date_to_str = request.query_params.get('date_to')
        date_from_str = request.query_params.get('date_from')

        try:
            if date_to_str:
                date_to_obj = datetime.strptime(date_to_str, '%Y-%m-%d').date()
            else:
                date_to_obj = date.today() - timedelta(days=1) # Defaults to yesterday

            if date_from_str:
                date_from_obj = datetime.strptime(date_from_str, '%Y-%m-%d').date()
            else:
                date_from_obj = date_to_obj - timedelta(days=29) # Defaults to 30 days of data (ending yesterday)

            if date_from_obj > date_to_obj:
                return Response({"error": "date_from cannot be after date_to."}, status=status.HTTP_400_BAD_REQUEST)

        except ValueError:
            raise ParseError("Invalid date format. Please use YYYY-MM-DD.")

        polygon_service = PolygonService()
        aggregates = polygon_service.get_daily_aggregates(
            symbol.upper(),
            date_from_obj.strftime('%Y-%m-%d'),
            date_to_obj.strftime('%Y-%m-%d')
        )

        if aggregates is None: # Service indicated an error fetching data
            return Response(
                {"error": f"Could not retrieve aggregate data for {symbol} from external service."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE # Or 500
            )
        if not aggregates and aggregates is not None: # Empty list, valid response but no data
             return Response(
                {"message": f"No aggregate data found for {symbol} in the specified range.", "results": []},
                status=status.HTTP_200_OK
            )

        return Response(aggregates, status=status.HTTP_200_OK)
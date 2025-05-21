from django.shortcuts import render

from django.contrib.auth.decorators import login_required
from django.views.generic import TemplateView
from django.utils.decorators import method_decorator
from rest_framework.views import APIView
from rest_framework.response import Response

from rest_framework import viewsets, permissions, filters
from django_filters.rest_framework import DjangoFilterBackend
from .models import SignificantEvent, StockSymbol, PriceUpdate
from .serializers import SignificantEventSerializer, StockSymbolSerializer, PriceUpdateSerializer
from .services.analysis_service import StockAnalysisService

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

@method_decorator(login_required, name='dispatch')
class QueryTestPageView(TemplateView):
   template_name = "stocks_api/query_test_page.html"

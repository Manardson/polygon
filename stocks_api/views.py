from django.shortcuts import render

from django.contrib.auth.decorators import login_required
from django.views.generic import TemplateView
from django.utils.decorators import method_decorator

from rest_framework import viewsets, permissions, filters
from django_filters.rest_framework import DjangoFilterBackend
from .models import SignificantEvent
from .serializers import SignificantEventSerializer

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

    # For manual filtering logic if needed:
    # def get_queryset(self):
    #     queryset = super().get_queryset()
    #     symbol_param = self.request.query_params.get('symbol')
    #     if symbol_param:
    #         queryset = queryset.filter(symbol__ticker__iexact=symbol_param)
    #     # Add more filters
    #     return queryset

@method_decorator(login_required, name='dispatch')
class QueryTestPageView(TemplateView):
   template_name = "stocks_api/query_test_page.html"
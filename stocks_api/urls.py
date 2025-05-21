from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SignificantEventViewSet, PriceHistoryViewSet, StockSymbolViewSet, EventSummaryView
from stocks_api.views import QueryTestPageView

router = DefaultRouter()
router.register(r'significant-events', SignificantEventViewSet, basename='significant-event')
router.register(r'price-history', PriceHistoryViewSet, basename='price-history')
router.register(r'symbols', StockSymbolViewSet, basename='stock-symbol')

urlpatterns = [
    path('', include(router.urls)),
    path('test-query-page/', QueryTestPageView.as_view(), name='test_query_page'),
    path('event-summary/', EventSummaryView.as_view(), name='event-summary'),
]

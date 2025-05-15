from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SignificantEventViewSet
from stocks_api.views import QueryTestPageView

router = DefaultRouter()
router.register(r'significant-events', SignificantEventViewSet, basename='significant-event')

urlpatterns = [
    path('', include(router.urls)),
    path('test-query-page/', QueryTestPageView.as_view(), name='test_query_page'),
]

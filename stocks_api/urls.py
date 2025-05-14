from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SignificantEventViewSet
from stocks_api.views import query_test_page_view

router = DefaultRouter()
router.register(r'significant-events', SignificantEventViewSet, basename='significant-event')

urlpatterns = [
    path('', include(router.urls)),
    path('test-query-page/', query_test_page_view, name='test_query_page'),
]


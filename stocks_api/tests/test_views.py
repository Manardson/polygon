# stocks_api/tests/test_views.py
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from .factories import StockSymbolFactory, SignificantEventFactory
from django.conf import settings

class SignificantEventAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.client = APIClient()
        # self.client.force_authenticate(user=self.user) # Or get token

        # Get token
        response = self.client.post(reverse('token_obtain_pair'), {'username': 'testuser', 'password': 'testpassword'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.access_token = response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')

        self.symbol_googl = StockSymbolFactory(ticker='GOOGL', name='Google')
        self.symbol_msft = StockSymbolFactory(ticker='MSFT', name='Microsoft')
        self.symbol_amzn = StockSymbolFactory(ticker='AMZN', name='Amazon')

        # Create events with specific timestamps for testing
        self.now = timezone.now()
        
        # Create events for GOOGL
        SignificantEventFactory.create_batch(3, symbol=self.symbol_googl, event_type='PRICE_INCREASE')
        SignificantEventFactory(symbol=self.symbol_googl, event_type='PRICE_DECREASE')
        
        # Create events for MSFT
        SignificantEventFactory.create_batch(2, symbol=self.symbol_msft, event_type='PRICE_DECREASE')
        
        # Create events for AMZN
        SignificantEventFactory(symbol=self.symbol_amzn, event_type='PRICE_INCREASE')
        
        # Create an older event for testing date filtering
        self.old_event = SignificantEventFactory(
            symbol=self.symbol_msft, 
            event_type='PRICE_INCREASE',
            timestamp=self.now - timedelta(days=5)
        )

    def test_list_significant_events_unauthenticated(self):
        client = APIClient() # New unauthenticated client
        url = reverse('significant-event-list')
        response = client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_all_significant_events(self):
        url = reverse('significant-event-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 8) # 3 + 1 + 2 + 1 + 1 (old)

    def test_filter_by_symbol_ticker(self):
        url = reverse('significant-event-list') + f'?symbol__ticker={self.symbol_googl.ticker}'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 4) # 3 INCREASE + 1 DECREASE for GOOGL
        for item in response.data['results']:
            self.assertEqual(item['symbol']['ticker'], self.symbol_googl.ticker)

    def test_filter_by_event_type(self):
        url = reverse('significant-event-list') + '?event_type=PRICE_DECREASE'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 3) # 1 GOOGL + 2 MSFT
        for item in response.data['results']:
            self.assertEqual(item['event_type'], 'PRICE_DECREASE')

    def test_filter_by_timestamp_gte(self):
        # Query for events in the last day
        one_day_ago = (self.now - timedelta(days=1)).isoformat()
        url = reverse('significant-event-list') + f'?timestamp__gte={one_day_ago}'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 7) # All except the old event

    def test_filter_by_timestamp_lte(self):
        # Query for events older than 2 days
        two_days_ago = (self.now - timedelta(days=2)).isoformat()
        url = reverse('significant-event-list') + f'?timestamp__lte={two_days_ago}'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1) # Only the old event

    def test_filter_by_date_range(self):
        # Query for events between 6 days ago and 4 days ago
        six_days_ago = (self.now - timedelta(days=6)).isoformat()
        four_days_ago = (self.now - timedelta(days=4)).isoformat()
        url = reverse('significant-event-list') + f'?timestamp__gte={six_days_ago}&timestamp__lte={four_days_ago}'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1) # Only the old event

    def test_combined_filters(self):
        # Filter by symbol and event type
        url = reverse('significant-event-list') + f'?symbol__ticker={self.symbol_msft.ticker}&event_type=PRICE_DECREASE'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2) # Only MSFT PRICE_DECREASE events
        
        for item in response.data['results']:
            self.assertEqual(item['symbol']['ticker'], self.symbol_msft.ticker)
            self.assertEqual(item['event_type'], 'PRICE_DECREASE')

    def test_pagination_works(self):
        # Override PAGE_SIZE for this test
        original_page_size = settings.REST_FRAMEWORK.get('PAGE_SIZE')
        settings.REST_FRAMEWORK['PAGE_SIZE'] = 3
        
        # Create more events to ensure pagination
        SignificantEventFactory.create_batch(5, symbol=self.symbol_amzn, event_type='PRICE_INCREASE')
        
        url = reverse('significant-event-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check pagination data is present
        self.assertIn('count', response.data)
        self.assertIn('next', response.data)
        self.assertIn('previous', response.data)
        self.assertIn('results', response.data)
        
        # Check first page has correct number of results
        self.assertEqual(len(response.data['results']), 3)
        
        # Check total count is correct (8 original + 5 new = 13)
        self.assertEqual(response.data['count'], 13)
        
        # Check next page URL exists
        self.assertIsNotNone(response.data['next'])
        
        # Restore original page size
        settings.REST_FRAMEWORK['PAGE_SIZE'] = original_page_size

    def test_ordering_by_timestamp(self):
        # Test default ordering (newest first)
        url = reverse('significant-event-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check first result is newer than the old event
        first_timestamp = response.data['results'][0]['timestamp']
        self.assertGreater(first_timestamp, self.old_event.timestamp.isoformat())
        
        # Test explicit descending order
        url = reverse('significant-event-list') + '?ordering=-timestamp'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check first result is newer than the old event
        first_timestamp = response.data['results'][0]['timestamp']
        self.assertGreater(first_timestamp, self.old_event.timestamp.isoformat())
        
        # Test ascending order
        url = reverse('significant-event-list') + '?ordering=timestamp'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check first result is the old event
        first_timestamp = response.data['results'][0]['timestamp']
        self.assertEqual(first_timestamp, self.old_event.timestamp.isoformat())

    def test_ordering_by_symbol(self):
        # Test ordering by symbol ticker (A-Z)
        url = reverse('significant-event-list') + '?ordering=symbol__ticker'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check first result is AMZN (alphabetically first)
        first_symbol = response.data['results'][0]['symbol']['ticker']
        self.assertEqual(first_symbol, 'AMZN')
        
        # Test ordering by symbol ticker (Z-A)
        url = reverse('significant-event-list') + '?ordering=-symbol__ticker'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check first result is not AMZN (should be alphabetically last)
        first_symbol = response.data['results'][0]['symbol']['ticker']
        self.assertNotEqual(first_symbol, 'AMZN')

    def test_invalid_filter_parameter(self):
        # Test with an invalid filter parameter
        url = reverse('significant-event-list') + '?invalid_param=value'
        response = self.client.get(url)
        
        # Should still return 200 OK, just ignore the invalid parameter
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 8)  # All events

    def test_token_refresh(self):
        # Test token refresh functionality
        refresh_url = reverse('token_refresh')
        response = self.client.post(refresh_url, {'refresh': self.client.post(reverse('token_obtain_pair'), 
                                                 {'username': 'testuser', 'password': 'testpassword'}, 
                                                 format='json').data['refresh']}, 
                                    format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        
        # Verify the new token works
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {response.data["access"]}')
        url = reverse('significant-event-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

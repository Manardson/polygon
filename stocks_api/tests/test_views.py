# stocks_api/tests/test_views.py
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.contrib.auth.models import User
from .factories import StockSymbolFactory, SignificantEventFactory

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

        SignificantEventFactory.create_batch(3, symbol=self.symbol_googl, event_type='PRICE_INCREASE')
        SignificantEventFactory.create_batch(2, symbol=self.symbol_msft, event_type='PRICE_DECREASE')
        SignificantEventFactory(symbol=self.symbol_googl, event_type='PRICE_DECREASE')

    def test_list_significant_events_unauthenticated(self):
        client = APIClient() # New unauthenticated client
        url = reverse('significant-event-list')
        response = client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_all_significant_events(self):
        url = reverse('significant-event-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 6) # 3 + 2 + 1

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
        self.assertEqual(response.data['count'], 3) # 2 MSFT + 1 GOOGL
        for item in response.data['results']:
            self.assertEqual(item['event_type'], 'PRICE_DECREASE')

    def test_filter_by_timestamp_gte(self):
        # Create an event with an older timestamp for testing
        SpecificEventFactory(symbol=self.symbol_msft, timestamp=timezone.now() - timedelta(days=5))

        # Now total is 7. Query for events in the last day
        one_day_ago = (timezone.now() - timedelta(days=1)).isoformat()
        url = reverse('significant-event-list') + f'?timestamp__gte={one_day_ago}'
        response = self.client.get(url) # Assuming default ordering by -timestamp
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 6) # The 6 created in setUp are recent

    def test_pagination_works(self):
        # Assuming PAGE_SIZE = 2 for this test (override in test or ensure enough data)
        # For this, you might need to adjust settings.REST_FRAMEWORK['PAGE_SIZE'] in the test setUp or ensure > 10 items
        # SignificantEventFactory.create_batch(15) # To ensure pagination
        # url = reverse('significant-event-list')
        # response = self.client.get(url)
        # self.assertEqual(response.status_code, status.HTTP_200_OK)
        # self.assertIsNotNone(response.data.get('next'))
        # self.assertEqual(len(response.data['results']), settings.REST_FRAMEWORK.get('PAGE_SIZE', 10))
        pass # Placeholder, implement with PAGE_SIZE override or more data

    # TODO: combined filters, ordering, invalid inputs, etc.
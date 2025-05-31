from django.test import TestCase
from django.utils import timezone
from decimal import Decimal
from stocks_api.models import StockSymbol, PriceUpdate, SignificantEvent

class StockSymbolModelTest(TestCase):

    def test_create_stock_symbol(self):
        symbol = StockSymbol.objects.create(ticker="TEST", name="Test Company")
        self.assertEqual(symbol.ticker, "TEST")
        self.assertEqual(symbol.name, "Test Company")
        self.assertEqual(str(symbol), "TEST")

    def test_stock_symbol_ticker_is_primary_key(self):
        StockSymbol.objects.create(ticker="UNIQUE", name="Unique Corp")
        with self.assertRaises(Exception): # Should raise IntegrityError
            StockSymbol.objects.create(ticker="UNIQUE", name="Another Corp")

class SignificantEventModelTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.symbol = StockSymbol.objects.create(ticker="MSFT", name="Microsoft Corp.")

    def test_create_significant_event(self):
        now = timezone.now()
        event_details = {
            "previous_price": "150.00",
            "current_price": "155.00",
            "percentage_change": "3.33"
        }
        event = SignificantEvent.objects.create(
            symbol=self.symbol,
            event_type='PRICE_INCREASE',
            details=event_details
            # timestamp is auto_now_add
        )
        self.assertEqual(event.symbol, self.symbol)
        self.assertEqual(event.event_type, 'PRICE_INCREASE')
        self.assertIsNotNone(event.timestamp)
        self.assertGreaterEqual(event.timestamp, now)
        self.assertEqual(event.details, event_details)
        self.assertEqual(str(event), f"Significant event for MSFT at {event.timestamp}")

    def test_significant_event_ordering(self):
        # Create events with slightly different timestamps
        event1_details = {"change": "up"}
        event2_details = {"change": "down"}
        event1 = SignificantEvent.objects.create(symbol=self.symbol, event_type='PRICE_INCREASE', details=event1_details)
        event2 = SignificantEvent.objects.create(symbol=self.symbol, event_type='PRICE_DECREASE', details=event2_details)

        events = SignificantEvent.objects.all()
        if events.count() > 1:
            self.assertGreaterEqual(events[0].timestamp, events[1].timestamp)
            self.assertEqual(events[0], event2)
            self.assertEqual(events[1], event1)

    def test_event_type_choices(self):
        # Creating an event with a valid choice
        event = SignificantEvent.objects.create(
            symbol=self.symbol,
            event_type=SignificantEvent.EVENT_TYPES[0][0],
            details={}
        )
        self.assertEqual(event.event_type, SignificantEvent.EVENT_TYPES[0][0])

class PriceUpdateModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.symbol = StockSymbol.objects.create(ticker="AMZN", name="Amazon.com Inc.")

    def test_create_price_update(self):
        timestamp = timezone.now()
        price = Decimal("3000.50")
        volume = 1000000

        update = PriceUpdate.objects.create(
            symbol=self.symbol,
            timestamp=timestamp,
            price=price,
            volume=volume
        )

        self.assertEqual(update.symbol, self.symbol)
        self.assertEqual(update.timestamp, timestamp)
        self.assertEqual(update.price, price)
        self.assertEqual(update.volume, volume)
        self.assertEqual(str(update), f"AMZN at {timestamp}: ${price}")

    def test_price_update_ordering_and_indexes(self):
        update1_ts = timezone.now() - timezone.timedelta(minutes=5)
        update2_ts = timezone.now()
        PriceUpdate.objects.create(symbol=self.symbol, timestamp=update1_ts, price=Decimal("100.00"))
        PriceUpdate.objects.create(symbol=self.symbol, timestamp=update2_ts, price=Decimal("101.00"))

        updates = PriceUpdate.objects.filter(symbol=self.symbol)
        self.assertEqual(updates[0].timestamp, update2_ts)
        self.assertEqual(updates[1].timestamp, update1_ts)
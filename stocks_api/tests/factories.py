import factory
from factory.django import DjangoModelFactory
from stocks_api.models import StockSymbol, SignificantEvent
from django.utils import timezone
from decimal import Decimal

class StockSymbolFactory(DjangoModelFactory):
    class Meta:
        model = StockSymbol
        django_get_or_create = ('ticker',)

    ticker = factory.Sequence(lambda n: f"SYM{n}")
    name = factory.LazyAttribute(lambda o: f"{o.ticker} Company Inc.")

class SignificantEventFactory(DjangoModelFactory):
    class Meta:
        model = SignificantEvent

    symbol = factory.SubFactory(StockSymbolFactory)
    event_type = SignificantEvent.EVENT_TYPES[0][0] # Default to PRICE_INCREASE
    timestamp = factory.LazyFunction(timezone.now)
    details = factory.LazyAttribute(lambda o: {
        "previous_price": "100.00",
        "current_price": "105.00",
        "percentage_change": "5.00",
        "current_timestamp": timezone.now().isoformat()
    })
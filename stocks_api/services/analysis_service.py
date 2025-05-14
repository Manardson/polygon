import logging
from decimal import Decimal
from django.utils import timezone
from stocks_api.models import StockSymbol, SignificantEvent, PriceUpdate # PriceUpdate if storing all ticks

logger = logging.getLogger(__name__)

# Store the last known price for each symbol.
LAST_PRICES_MEMORY_CACHE = {} # { 'ticker': {'price': Decimal, 'timestamp': datetime} }

SIGNIFICANT_CHANGE_PERCENTAGE_THRESHOLD = Decimal('2.0') # e.g., 2% change

class StockAnalysisService:
    def __init__(self):
        # Load initial last prices from DB + Gonna prepopulate last 300 candles for trend indicators
        pass

    def process_new_price_data(self, symbol_ticker: str, current_price: Decimal, current_timestamp: timezone.datetime):
        """
        Analyzes new price data for a symbol and creates a SignificantEvent if applicable.
        """
        try:
            stock_symbol = StockSymbol.objects.get(ticker=symbol_ticker)
        except StockSymbol.DoesNotExist:
            logger.warning(f"StockSymbol {symbol_ticker} not found. Cannot process.")
            return None

        last_known_data = LAST_PRICES_MEMORY_CACHE.get(symbol_ticker)

        # --- TODO: Query db / Ideally Redis on live production for the last PriceUpdate ---

        event_created = None
        if last_known_data:
            previous_price = last_known_data['price']
            if previous_price == Decimal('0.00000001'):
                percentage_change = Decimal('0')
            else:
                percentage_change = ((current_price - previous_price) / previous_price) * Decimal('100')

            logger.info(
                f"Symbol: {symbol_ticker}, Prev Price: {previous_price}, Curr Price: {current_price}, %Change: {percentage_change:.2f}%"
            )

            if abs(percentage_change) >= SIGNIFICANT_CHANGE_PERCENTAGE_THRESHOLD:
                event_type = 'PRICE_INCREASE' if percentage_change > 0 else 'PRICE_DECREASE'
                details = {
                    'previous_price': str(previous_price),
                    'current_price': str(current_price),
                    'percentage_change': f"{percentage_change:.2f}",
                    'previous_timestamp': last_known_data['timestamp'].isoformat() if last_known_data.get('timestamp') else None,
                    'current_timestamp': current_timestamp.isoformat(),
                }
                event_created = SignificantEvent.objects.create(
                    symbol=stock_symbol,
                    event_type=event_type,
                    timestamp=timezone.now(), # Event detection time
                    details=details
                )
                logger.info(f"Significant event CREATED for {symbol_ticker}: {event_type}, {percentage_change:.2f}%")

        LAST_PRICES_MEMORY_CACHE[symbol_ticker] = {
            'price': current_price,
            'timestamp': current_timestamp
        }
        # TODO: Save update event to PriceUpdate model
        
        return event_created
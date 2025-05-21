import logging
from decimal import Decimal
from django.utils import timezone
from stocks_api.models import StockSymbol, SignificantEvent, PriceUpdate

logger = logging.getLogger(__name__)

# Store the last known price for each symbol.
LAST_PRICES_MEMORY_CACHE = {} # { 'ticker': {'price': Decimal, 'timestamp': datetime} }

SIGNIFICANT_CHANGE_PERCENTAGE_THRESHOLD = Decimal('2.0') # e.g., 2% change

class StockAnalysisService:
    def __init__(self):
        # Load initial last prices from DB
        self._initialize_cache_from_db()
    
    def _initialize_cache_from_db(self):
        """
        Initialize the price cache from the database.
        This ensures we have historical data even after service restart.
        """
        logger.info("Initializing price cache from database...")
        symbols = StockSymbol.objects.all()
        count = 0
        
        for symbol in symbols:
            last_update = PriceUpdate.objects.filter(symbol=symbol).order_by('-timestamp').first()
            if last_update:
                LAST_PRICES_MEMORY_CACHE[symbol.ticker] = {
                    'price': last_update.price,
                    'timestamp': last_update.timestamp
                }
                count += 1
                logger.debug(f"Initialized cache for {symbol.ticker} with price {last_update.price}")
        
        logger.info(f"Price cache initialization complete. Loaded {count} symbols.")

    def process_new_price_data(self, symbol_ticker: str, current_price: Decimal, current_timestamp: timezone.datetime):
        """
        Analyzes new price data for a symbol and creates a SignificantEvent if applicable.
        
        Args:
            symbol_ticker: The ticker symbol (e.g., 'GOOGL')
            current_price: The current price as a Decimal
            current_timestamp: The timestamp of the current price data
            
        Returns:
            SignificantEvent object if created, None otherwise
        """
        try:
            stock_symbol = StockSymbol.objects.get(ticker=symbol_ticker)
        except StockSymbol.DoesNotExist:
            logger.warning(f"StockSymbol {symbol_ticker} not found. Cannot process.")
            return None

        # First try to get the last price from memory cache
        last_known_data = LAST_PRICES_MEMORY_CACHE.get(symbol_ticker)
        
        # If not in memory cache, try to get from database
        if not last_known_data:
            last_price_update = PriceUpdate.objects.filter(symbol=stock_symbol).order_by('-timestamp').first()
            if last_price_update:
                last_known_data = {
                    'price': last_price_update.price,
                    'timestamp': last_price_update.timestamp
                }
                logger.info(f"Retrieved last price for {symbol_ticker} from database: {last_price_update.price}")

        event_created = None
        if last_known_data:
            previous_price = last_known_data['price']
            if previous_price == Decimal('0') or previous_price == Decimal('0.00000001'):
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

        # Update the memory cache
        LAST_PRICES_MEMORY_CACHE[symbol_ticker] = {
            'price': current_price,
            'timestamp': current_timestamp
        }
        
        # Save the price update to the database for historical record
        price_update = PriceUpdate.objects.create(
            symbol=stock_symbol,
            timestamp=current_timestamp,
            price=current_price,
            volume=None  # Could be populated if volume data is available
        )
        logger.debug(f"Saved price update for {symbol_ticker}: {current_price} at {current_timestamp}")
        
        return event_created
    
    def get_price_history(self, symbol_ticker: str, days: int = 7):
        """
        Get price history for a symbol for the specified number of days.
        
        Args:
            symbol_ticker: The ticker symbol (e.g., 'GOOGL')
            days: Number of days of history to retrieve
            
        Returns:
            List of price updates ordered by timestamp
        """
        try:
            stock_symbol = StockSymbol.objects.get(ticker=symbol_ticker)
        except StockSymbol.DoesNotExist:
            logger.warning(f"StockSymbol {symbol_ticker} not found. Cannot retrieve history.")
            return []
        
        start_date = timezone.now() - timezone.timedelta(days=days)
        
        price_updates = PriceUpdate.objects.filter(
            symbol=stock_symbol,
            timestamp__gte=start_date
        ).order_by('timestamp')
        
        return price_updates
    
    def get_significant_events_summary(self, days: int = 7):
        """
        Get a summary of significant events for all symbols for the specified number of days.
        
        Args:
            days: Number of days of history to include
            
        Returns:
            Dictionary with summary statistics
        """
        start_date = timezone.now() - timezone.timedelta(days=days)
        
        # Get all events in the time period
        events = SignificantEvent.objects.filter(timestamp__gte=start_date)
        
        # Count events by type
        increases = events.filter(event_type='PRICE_INCREASE').count()
        decreases = events.filter(event_type='PRICE_DECREASE').count()
        
        # Count events by symbol
        events_by_symbol = {}
        for symbol in StockSymbol.objects.all():
            symbol_events = events.filter(symbol=symbol)
            if symbol_events.exists():
                events_by_symbol[symbol.ticker] = {
                    'total': symbol_events.count(),
                    'increases': symbol_events.filter(event_type='PRICE_INCREASE').count(),
                    'decreases': symbol_events.filter(event_type='PRICE_DECREASE').count()
                }
        
        return {
            'period_days': days,
            'total_events': events.count(),
            'increases': increases,
            'decreases': decreases,
            'by_symbol': events_by_symbol
        }

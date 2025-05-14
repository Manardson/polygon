from celery import shared_task
import logging
from decimal import Decimal
from .services.polygon_service import PolygonService
from .services.analysis_service import StockAnalysisService
from .models import StockSymbol # To fetch all symbols dynamically

logger = logging.getLogger(__name__)

@shared_task
def fetch_and_process_stock_data_task(ticker_symbols=None):
    if ticker_symbols is None:
        # Fetch all symbols from DB if not provided
        ticker_symbols = list(StockSymbol.objects.values_list('ticker', flat=True))

    if not ticker_symbols:
        logger.warning("No ticker symbols provided or found in DB for fetching data.")
        return "No symbols to process."

    polygon_service = PolygonService()
    analysis_service = StockAnalysisService()
    results = []

    logger.info(f"Fetching data for symbols: {ticker_symbols}")
    for ticker in ticker_symbols:
        trade_data = polygon_service.get_last_trade(ticker)
        if trade_data:
            logger.debug(f"Fetched data for {ticker}: Price {trade_data['price']} at {trade_data['timestamp']}")
            try:
                current_price = Decimal(str(trade_data['price'])) # Ensure Decimal conversion
                current_timestamp = trade_data['timestamp']
                event = analysis_service.process_new_price_data(
                    symbol_ticker=ticker,
                    current_price=current_price,
                    current_timestamp=current_timestamp
                )
                if event:
                    results.append(f"Event for {ticker}: {event.event_type}")
                else:
                    results.append(f"No significant event for {ticker}")
            except Exception as e:
                logger.error(f"Error processing data for {ticker}: {e}")
                results.append(f"Error processing {ticker}")
        else:
            logger.warning(f"No trade data received for {ticker}")
            results.append(f"No data for {ticker}")

    summary = f"Processed {len(ticker_symbols)} symbols. Results: {'; '.join(results)}"
    logger.info(summary)
    return summary

# Example task to initialize last prices from DB (run once or periodically)
@shared_task
def initialize_last_prices_cache_task():
    from stocks_api.services.analysis_service import LAST_PRICES_MEMORY_CACHE
    from stocks_api.models import PriceUpdate # Assuming you store all updates

    logger.info("Initializing LAST_PRICES_MEMORY_CACHE from database...")
    symbols = StockSymbol.objects.all()
    for symbol in symbols:
        last_update = PriceUpdate.objects.filter(symbol=symbol).order_by('-timestamp').first()
        if last_update:
            LAST_PRICES_MEMORY_CACHE[symbol.ticker] = {
                'price': last_update.price,
                'timestamp': last_update.timestamp
            }
            logger.info(f"Initialized cache for {symbol.ticker} with price {last_update.price}")
    logger.info("LAST_PRICES_MEMORY_CACHE initialization complete.")
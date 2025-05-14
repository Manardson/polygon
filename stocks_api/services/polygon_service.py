import requests
import logging
from django.conf import settings
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class PolygonService:
    BASE_URL = "https://api.polygon.io"

    def __init__(self, api_key=None):
        self.api_key = api_key or settings.POLYGON_API_KEY
        if not self.api_key:
            raise ValueError("Polygon API key not configured.")

    def get_last_trade(self, ticker_symbol: str):
        """
        Fetches the last trade for a given ticker symbol.
        Docs: https://polygon.io/docs/stocks/get_v2_last_trade__stocksticker
        """
        url = f"{self.BASE_URL}/v2/last/trade/{ticker_symbol}"
        params = {'apiKey': self.api_key}
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status() # Raises HTTPError for bad responses (4XX or 5XX)
            data = response.json()
            if data.get('status') == 'OK' and data.get('results'):
                # Polygon timestamp is in nanoseconds, convert to seconds for datetime
                trade_data = data['results']
                return {
                    'symbol': trade_data['T'],
                    'price': trade_data['p'],
                    'timestamp': datetime.fromtimestamp(trade_data['t'] / 1000.0), # Ensure correct timestamp unit
                    'volume': trade_data.get('s'), # Size/volume
                    # Add other relevant fields
                }
            logger.warning(f"No results or error status for {ticker_symbol}: {data}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching last trade for {ticker_symbol}: {e}")
            return None
        except (KeyError, ValueError) as e:
            logger.error(f"Error parsing data for {ticker_symbol}: {e} - Data: {data if 'data' in locals() else 'N/A'}")
            return None

# TODO: aggregates against daily avg
# Maybe with ws
# /v2/last/trade/ is REST.
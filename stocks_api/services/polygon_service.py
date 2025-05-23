import logging
import requests
from decimal import Decimal
from datetime import datetime, timedelta
from django.conf import settings
from stocks_api.models import StockSymbol, PriceUpdate

logger = logging.getLogger(__name__)

class PolygonService:
    """
    Service for interacting with the Polygon.io API to fetch stock data.
    """
    BASE_URL = "https://api.polygon.io"
    API_KEY = settings.POLYGON_API_KEY

    def __init__(self):
        self.session = requests.Session()
        self.session.params = {'apiKey': self.API_KEY}

    def get_previous_close(self, ticker):
        """
        Get the previous day's closing price for a stock.

        Args:
            ticker (str): The stock ticker symbol

        Returns:
            dict: The previous close data or None if the request failed
        """
        endpoint = f"{self.BASE_URL}/v2/aggs/ticker/{ticker}/prev"

        try:
            response = self.session.get(endpoint)
            response.raise_for_status()
            data = response.json()

            if data.get('status') == 'OK' and data.get('results'):
                return data['results'][0]
            else:
                logger.warning(f"No previous close data found for {ticker}")
                return None

        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching previous close for {ticker}: {str(e)}")
            return None

    def get_daily_open_close(self, ticker, date):
        """
        Get the open, close, high, and low prices for a specific date.

        Args:
            ticker (str): The stock ticker symbol
            date (str): The date in YYYY-MM-DD format

        Returns:
            dict: The daily open/close data or None if the request failed
        """
        endpoint = f"{self.BASE_URL}/v1/open-close/{ticker}/{date}"

        try:
            response = self.session.get(endpoint)
            response.raise_for_status()
            data = response.json()

            if data.get('status') == 'OK':
                return data
            else:
                logger.warning(f"No daily data found for {ticker} on {date}")
                return None

        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching daily data for {ticker} on {date}: {str(e)}")
            return None

    def get_aggregates(self, ticker, multiplier, timespan, from_date, to_date):
        """
        Get aggregated price data for a stock over a specified time range.

        Args:
            ticker (str): The stock ticker symbol
            multiplier (int): The size of the timespan multiplier
            timespan (str): The timespan unit (minute, hour, day, week, month, quarter, year)
            from_date (str): The start date in YYYY-MM-DD format
            to_date (str): The end date in YYYY-MM-DD format

        Returns:
            list: The aggregated price data or empty list if the request failed
        """
        endpoint = f"{self.BASE_URL}/v2/aggs/ticker/{ticker}/range/{multiplier}/{timespan}/{from_date}/{to_date}"

        try:
            response = self.session.get(endpoint)
            response.raise_for_status()
            data = response.json()

            if data.get('status') == 'OK' and data.get('results'):
                return data['results']
            else:
                logger.warning(f"No aggregate data found for {ticker} from {from_date} to {to_date}")
                return []

        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching aggregate data for {ticker}: {str(e)}")
            return []

    def get_daily_aggregates_against_average(self, ticker, days=30):
        """
        Get daily aggregates and compare against the average for the specified period.

        Args:
            ticker (str): The stock ticker symbol
            days (int): Number of days to analyze

        Returns:
            dict: Analysis results including daily data and comparison to average
        """
        today = datetime.now().date()
        from_date = (today - timedelta(days=days)).strftime('%Y-%m-%d')
        to_date = today.strftime('%Y-%m-%d')

        aggregates = self.get_aggregates(ticker, 1, 'day', from_date, to_date)

        if not aggregates:
            return {
                'ticker': ticker,
                'status': 'error',
                'message': f'No data available for {ticker} in the specified date range'
            }

        # Calculate average values
        avg_close = sum(agg.get('c', 0) for agg in aggregates) / len(aggregates)
        avg_volume = sum(agg.get('v', 0) for agg in aggregates) / len(aggregates)

        # Compare each day to the average
        daily_analysis = []
        for agg in aggregates:
            close_price = agg.get('c', 0)
            volume = agg.get('v', 0)

            close_diff_pct = ((close_price - avg_close) / avg_close) * 100 if avg_close else 0
            volume_diff_pct = ((volume - avg_volume) / avg_volume) * 100 if avg_volume else 0

            daily_analysis.append({
                'date': datetime.fromtimestamp(agg.get('t', 0) / 1000).strftime('%Y-%m-%d'),
                'close': close_price,
                'volume': volume,
                'close_vs_avg': {
                    'diff': close_price - avg_close,
                    'diff_pct': close_diff_pct,
                    'is_above_avg': close_price > avg_close
                },
                'volume_vs_avg': {
                    'diff': volume - avg_volume,
                    'diff_pct': volume_diff_pct,
                    'is_above_avg': volume > avg_volume
                }
            })

        return {
            'ticker': ticker,
            'status': 'success',
            'period': {
                'from': from_date,
                'to': to_date,
                'days': days
            },
            'averages': {
                'close': avg_close,
                'volume': avg_volume
            },
            'daily_analysis': daily_analysis
        }

    def update_price_data(self, symbol_obj):
        """
        Update price data for a given stock symbol.

        Args:
            symbol_obj (StockSymbol): The stock symbol object

        Returns:
            bool: True if the update was successful, False otherwise
        """
        ticker = symbol_obj.ticker
        prev_close = self.get_previous_close(ticker)

        if not prev_close:
            return False

        try:
            price = Decimal(str(prev_close.get('c', 0)))
            timestamp = datetime.fromtimestamp(prev_close.get('t', 0) / 1000)

            # Create a new price update
            PriceUpdate.objects.create(
                symbol=symbol_obj,
                price=price,
                timestamp=timestamp,
                volume=prev_close.get('v')
            )

            logger.info(f"Updated price data for {ticker}: ${price} at {timestamp}")
            return True

        except Exception as e:
            logger.error(f"Error saving price data for {ticker}: {str(e)}")
            return False

    def get_daily_aggregates(self, ticker_symbol: str, date_from: str, date_to: str):
        url = f"{self.BASE_URL}/v2/aggs/ticker/{ticker_symbol}/range/1/day/{date_from}/{date_to}"
        params = {
            'apiKey': self.API_KEY,
            'sort': 'asc',
        }
        logger.info(f"PolygonService: Requesting URL: {url} with params (excluding apiKey for log)") # Log URL
        try:
            response = requests.get(url, params=params, timeout=15)
            logger.info(f"PolygonService: Response status code: {response.status_code} for {url}") # Log status code
            if response.status_code != 200:
                logger.error(f"PolygonService: Error response content: {response.text} for {url}") # Log error content
            response.raise_for_status() # This will raise HTTPError for 4xx/5xx

            data = response.json()
            if data.get('status') == 'OK' and 'results' in data:
                return data['results']
            elif data.get('resultsCount') == 0:
                logger.info(f"PolygonService: No results found (resultsCount is 0) for {ticker_symbol} in range. Response: {data}")
                return []
            else: # Status might not be 'OK' or results key is missing
                logger.warning(f"PolygonService: Unexpected response structure or status for {ticker_symbol}. Response: {data}")
                return None
        except requests.exceptions.HTTPError as http_err:
            logger.error(f"HTTP error occurred while fetching daily aggregates for {ticker_symbol}: {http_err} - Response Text: {http_err.response.text if http_err.response else 'No response body'}")
            return None
        except requests.exceptions.RequestException as req_err:
            logger.error(f"Request error occurred while fetching daily aggregates for {ticker_symbol}: {req_err}")
            return None
        except (KeyError, ValueError) as json_err: # For response.json() or data access issues
            logger.error(f"JSON parsing error for daily aggregates {ticker_symbol}: {json_err} - Raw Response (first 500 chars): {response.text[:500] if 'response' in locals() and hasattr(response, 'text') else 'N/A'}")
            return None

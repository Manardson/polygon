from django.test import TestCase, override_settings
from unittest.mock import patch, MagicMock
from decimal import Decimal
from datetime import datetime
import pytz

from stocks_api.tasks import fetch_and_process_stock_data_task
from stocks_api.models import StockSymbol, SignificantEvent

@override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
class FetchStockDataTaskTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        StockSymbol.objects.create(ticker="GOOGL", name="Google")
        StockSymbol.objects.create(ticker="AMZN", name="Amazon")

    def test_fetch_and_process_data_success_no_event(self, MockStockAnalysisService, MockPolygonService):
        mock_polygon_instance = MockPolygonService.return_value
        mock_polygon_instance.get_last_trade.side_effect = [
            {'symbol': 'GOOGL', 'price': Decimal('150.00'), 'timestamp': datetime.now(pytz.utc)},
            {'symbol': 'AMZN', 'price': Decimal('120.00'), 'timestamp': datetime.now(pytz.utc)},
        ]


        mock_analysis_instance = MockStockAnalysisService.return_value
        mock_analysis_instance.process_new_price_data.return_value = None

        # --- Execute Task ---
        result_summary = fetch_and_process_stock_data_task.delay(ticker_symbols=['GOOGL', 'AMZN'])

        # --- Assertions ---
        self.assertEqual(mock_polygon_instance.get_last_trade.call_count, 2)
        mock_polygon_instance.get_last_trade.assert_any_call('GOOGL')
        mock_polygon_instance.get_last_trade.assert_any_call('AMZN')

        self.assertEqual(mock_analysis_instance.process_new_price_data.call_count, 2)

        mock_analysis_instance.process_new_price_data.assert_any_call(
            symbol_ticker='GOOGL',
            current_price=Decimal('150.00'),
            current_timestamp=mock_polygon_instance.get_last_trade.side_effect[0]['timestamp']
        )

        # Check that no SignificantEvent was created
        self.assertEqual(SignificantEvent.objects.count(), 0)
        self.assertIn("No significant event for GOOGL", result_summary)
        self.assertIn("No significant event for AMZN", result_summary)
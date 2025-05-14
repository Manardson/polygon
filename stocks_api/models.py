from django.db import models
from django.contrib.auth.models import User

class StockSymbol(models.Model):
    ticker = models.CharField(max_length=10, unique=True, primary_key=True)
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.ticker

class PriceUpdate(models.Model):
    """
        Maybe store raw price updates if needed for other analysis
    """
    symbol = models.ForeignKey(StockSymbol, on_delete=models.CASCADE, related_name='price_updates')
    timestamp = models.DateTimeField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    volume = models.BigIntegerField(null=True, blank=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['symbol', '-timestamp']),
        ]

    def __str__(self):
        return f"{self.symbol.ticker} at {self.timestamp}: ${self.price}"

class SignificantEvent(models.Model):
    EVENT_TYPES = [
        ('PRICE_INCREASE', 'Price Increase'),
        ('PRICE_DECREASE', 'Price Decrease')
    ]
    symbol = models.ForeignKey(StockSymbol, on_delete=models.CASCADE, related_name='significant_events')
    event_type = models.CharField(max_length=50, choices=EVENT_TYPES)
    timestamp = models.DateTimeField(auto_now_add=True)
    details = models.JSONField() # Store context like old_price, new_price, percentage_change
                                 # e.g., {'previous_price': 100, 'current_price': 110, 'change_percent': 10}

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['symbol', '-timestamp']),
        ]

    def __str__(self):
        return f"Significant event for {self.symbol.ticker} at {self.timestamp}"
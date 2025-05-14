from rest_framework import serializers
from .models import SignificantEvent, StockSymbol

class StockSymbolSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockSymbol
        fields = ['ticker', 'name']

class SignificantEventSerializer(serializers.ModelSerializer):
    symbol = StockSymbolSerializer(read_only=True) # Nested representation
    # Or use symbol = serializers.StringRelatedField() for just the ticker string

    class Meta:
        model = SignificantEvent
        fields = ['id', 'symbol', 'event_type', 'timestamp', 'details']
        # read_only_fields for fields like 'timestamp' if auto_now_add=True
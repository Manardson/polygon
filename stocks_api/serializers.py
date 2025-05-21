from rest_framework import serializers
from .models import SignificantEvent, StockSymbol, PriceUpdate

class StockSymbolSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockSymbol
        fields = ['ticker', 'name']

class SignificantEventSerializer(serializers.ModelSerializer):
    symbol = StockSymbolSerializer(read_only=True) # Nested representation

    class Meta:
        model = SignificantEvent
        fields = ['id', 'symbol', 'event_type', 'timestamp', 'details']
        read_only_fields = ['timestamp']

class PriceUpdateSerializer(serializers.ModelSerializer):
    symbol = StockSymbolSerializer(read_only=True)
    
    class Meta:
        model = PriceUpdate
        fields = ['id', 'symbol', 'timestamp', 'price', 'volume']
        read_only_fields = ['timestamp']

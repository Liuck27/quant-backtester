import pytest
import tempfile
import os
from src.engine import BacktestEngine
from src.data_handler import DataHandler
from src.strategy import BuyAndHoldStrategy
from src.events import MarketEvent, SignalEvent

class TestStrategyIntegration:
    
    def test_buy_and_hold_signal_generation(self):
        """
        Verifies that BuyAndHoldStrategy generates ONE signal at the first bar.
        """
        # 1. Setup CSV with multiple bars
        csv_content = """Date,Close,Volume
2023-01-01,100.0,1000
2023-01-02,101.5,1500
2023-01-03,102.0,1200
"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=".csv") as tmp:
            tmp.write(csv_content)
            tmp_path = tmp.name
            
        try:
            # 2. Setup Components
            data_handler = DataHandler(tmp_path, "TEST_SYM")
            strategy = BuyAndHoldStrategy()
            engine = BacktestEngine(data_handler=data_handler, strategy=strategy)
            
            # 3. Run
            engine.run()
            
            # 4. Verify Output
            # We expect 3 MarketEvents and 1 SignalEvent (after the first MarketEvent)
            events = engine.processed_events
            
            # Count signals
            signal_events = [e for e in events if isinstance(e, SignalEvent)]
            market_events = [e for e in events if isinstance(e, MarketEvent)]
            
            assert len(market_events) == 3
            assert len(signal_events) == 1
            
            # Check signal details
            first_signal = signal_events[0]
            assert first_signal.signal_type == "LONG"
            assert first_signal.symbol == "TEST_SYM"
            
            # Verify order: Market, Signal, Market, Market
            # (Signal generated after handling first Market, so it should be processed next)
            assert isinstance(events[0], MarketEvent)
            assert isinstance(events[1], SignalEvent)
            assert isinstance(events[2], MarketEvent)
            assert isinstance(events[3], MarketEvent)
            
        finally:
            os.remove(tmp_path)

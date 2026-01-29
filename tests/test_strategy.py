import pytest
import tempfile
import os
from src.engine import BacktestEngine
from src.data_handler import DataHandler
from src.strategy import BuyAndHoldStrategy, MovingAverageCrossStrategy
from datetime import datetime
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

class TestMovingAverageStrategy:
    def test_warmup_period(self):
        """Verify no signals during warm-up period."""
        strategy = MovingAverageCrossStrategy(short_window=2, long_window=4)
        
        # Feed 3 events (one less than long_window)
        prices = [10.0, 11.0, 12.0]
        for p in prices:
            event = MarketEvent(datetime.now(), "TEST", p, 100)
            signal = strategy.calculate_signals(event)
            assert signal is None

    def test_golden_cross_long(self):
        """Verify LONG signal on Golden Cross."""
        strategy = MovingAverageCrossStrategy(short_window=2, long_window=4)
        
        # Prices:
        # 1. 10.0 -> History: [10]. Wait.
        # 2. 10.0 -> History: [10, 10]. Short: 10, Wait.
        # 3. 10.0 -> History: [10, 10, 10]. Short: 10, Wait.
        # 4. 10.0 -> History: [10, 10, 10, 10]. Short: 10, Long: 10. No Signal.
        # 5. 11.0 -> History: [10, 10, 10, 11]. 
        #    Short (last 2): (10+11)/2 = 10.5
        #    Long (last 4): (10+10+10+11)/4 = 10.25
        #    Short > Long -> LONG
        
        prices = [10.0, 10.0, 10.0, 10.0]
        for p in prices:
            event = MarketEvent(datetime.now(), "TEST", p, 100)
            strategy.calculate_signals(event)
            
        # Trigger crossover
        event = MarketEvent(datetime.now(), "TEST", 11.0, 100)
        signal = strategy.calculate_signals(event)
        
        assert signal is not None
        assert signal.signal_type == "LONG"
        assert strategy.bought is True

    def test_death_cross_exit(self):
        """Verify EXIT signal on Death Cross."""
        strategy = MovingAverageCrossStrategy(short_window=2, long_window=4)
        strategy.bought = True # Manually set state to bought to test exit
        
        # Prices set up such that Short is currently > Long (consistent with bought),
        # but about to cross down.
        # Let's just force history so next price triggers drop.
        
        # History: [12, 12, 12, 12]
        # Short (2): 12. Long (4): 12. 
        # (Technically we need Short > Long to have entered naturally, but we force bought=True for unit test isolation)
        
        strategy.prices = [12.0, 12.0, 12.0, 12.0] 
        
        # Trigger drop
        # New Price: 10.0
        # History: [..., 12, 12, 12, 10]
        # Short (2): (12+10)/2 = 11.0
        # Long (4): (12+12+12+10)/4 = 11.5
        # Short < Long -> EXIT
        
        event = MarketEvent(datetime.now(), "TEST", 10.0, 100)
        signal = strategy.calculate_signals(event)
        
        assert signal is not None
        assert signal.signal_type == "EXIT"
        assert strategy.bought is False
        
    def test_no_repeat_signal(self):
        """Verify no repeated signals if trend continues."""
        strategy = MovingAverageCrossStrategy(short_window=2, long_window=4)
        
        # Establish LONG position
        # [10, 10, 10, 11] -> 10.5 vs 10.25 -> LONG
        strategy.prices = [10.0, 10.0, 10.0]
        strategy.calculate_signals(MarketEvent(datetime.now(), "TEST", 11.0, 100))
        assert strategy.bought is True
        
        # Continue trend
        # Next: 12.0
        # History: [..., 10, 10, 11, 12]
        # Short (2): 11.5
        # Long (4): (10+10+11+12)/4 = 10.75
        # Short > Long. Still bought. Should be None.
        
        event = MarketEvent(datetime.now(), "TEST", 12.0, 100)
        signal = strategy.calculate_signals(event)
        
        assert signal is None
        assert strategy.bought is True

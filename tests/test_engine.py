import pytest
from datetime import datetime
from src.engine import BacktestEngine
from src.events import MarketEvent, SignalEvent

class TestBacktestEngine:
    
    def test_fifo_order(self):
        """
        Verifies that events are processed in First-In-First-Out order.
        """
        engine = BacktestEngine()
        
        # Create two distinct events
        event_1 = MarketEvent(
            time=datetime(2023, 1, 1, 10, 0), 
            symbol="AAPL", 
            price=150.0, 
            volume=100
        )
        
        event_2 = SignalEvent(
            time=datetime(2023, 1, 1, 10, 1), 
            symbol="AAPL", 
            signal_type="LONG"
        )
        
        # Put them in order 1, then 2
        engine.put(event_1)
        engine.put(event_2)
        
        # Run the engine
        engine.run()
        
        # Verify State
        assert len(engine.processed_events) == 2
        assert engine.processed_events[0] == event_1
        assert engine.processed_events[1] == event_2
        
    def test_queue_emptied(self):
        """
        Verifies that the queue is empty after run() completes.
        """
        engine = BacktestEngine()
        engine.put(MarketEvent(datetime.now(), "MSFT", 200.0, 50))
        
        assert len(engine.queue) == 1
        engine.run()
        assert len(engine.queue) == 0
        assert len(engine.processed_events) == 1

    def test_empty_queue_run(self):
        """
        Verifies that running on an empty queue works gracefully.
        """
        engine = BacktestEngine()
        engine.run() # Should not raise error
        assert len(engine.queue) == 0
        assert len(engine.processed_events) == 0

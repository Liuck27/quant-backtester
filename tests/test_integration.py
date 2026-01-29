import pytest
import tempfile
import os
import pandas as pd
from datetime import datetime
from src.engine import BacktestEngine
from src.data_handler import DataHandler
from src.strategy import MovingAverageCrossStrategy
from src.events import MarketEvent, SignalEvent, OrderEvent, FillEvent, Event

class TestDeterministicBacktest:
    
    def test_full_backtest_determinism(self):
        """
        Runs a full backtest with MovingAverageCrossStrategy and verifies that
        the sequence of events is exactly as expected and deterministic.
        """
        # 1. Setup deterministic CSV Data
        # Pattern: 
        # - 5 days flat (warmup)
        # - sharp rise (trigger BUY)
        # - sharp drop (trigger EXIT)
        
        # Long Window = 5. Short Window = 2.
        # Warmup needs 5 bars.
        
        csv_content = """Date,Close,Volume
2023-01-01,10.0,1000
2023-01-02,10.0,1000
2023-01-03,10.0,1000
2023-01-04,10.0,1000
2023-01-05,10.0,1000
2023-01-06,12.0,1000
2023-01-07,13.0,1000
2023-01-08,9.0,1000
2023-01-09,8.0,1000
"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=".csv") as tmp:
            tmp.write(csv_content)
            tmp_path = tmp.name
            
        try:
            # 2. Setup Components
            data_handler = DataHandler(tmp_path, "TEST_SYM")
            strategy = MovingAverageCrossStrategy(short_window=2, long_window=5)
            # No portfolio for this specific test if we just want to verify Signal generation sequence, 
            # BUT the prompt asked for "MarketEvent -> SignalEvent -> OrderEvent -> FillEvent".
            # So we DO need a portfolio to generate Orders and Fills.
            from src.portfolio import Portfolio
            portfolio = Portfolio(initial_capital=100000)
            
            engine = BacktestEngine(data_handler=data_handler, strategy=strategy, portfolio=portfolio)
            
            # 3. Run
            engine.run()
            
            # 4. Verify Event Trace
            events = engine.processed_events
            
            # Expected Timeline:
            # Day 1-5 (Jan 1-5): 10.0. Warmup (len=1..5). No Signals.
            # Day 6 (Jan 6): 12.0. 
            #   History: [10, 10, 10, 10, 10, 12].
            #   Long(5): [10, 10, 10, 10, 12] -> avg 10.4
            #   Short(2): [10, 12] -> avg 11.0
            #   Short > Long -> LONG Signal.
            #   Signal -> Order -> Fill (Day 6).
            
            # Day 7 (Jan 7): 13.0. Trend continues. No new signal.
            
            # Day 8 (Jan 8): 9.0.
            #   History: [..., 10, 10, 12, 13, 9]
            #   Long(5): [10, 10, 12, 13, 9] -> avg 10.8
            #   Short(2): [13, 9] -> avg 11.0
            #   Short (11.0) > Long (10.8). Still Long? Wait.
            
            # Day 9 (Jan 9): 8.0.
            #   History: [..., 10, 12, 13, 9, 8]
            #   Long(5): [10, 12, 13, 9, 8] -> avg 10.4
            #   Short(2): [9, 8] -> avg 8.5
            #   Short < Long -> EXIT Signal.
            
            # Filter for non-Market events to verify logic flow easier
            action_events = [e for e in events if not isinstance(e, MarketEvent)]
            
            # Event 0: Signal LONG (Jan 6)
            assert isinstance(action_events[0], SignalEvent)
            assert action_events[0].signal_type == "LONG"
            assert action_events[0].time.strftime("%Y-%m-%d") == "2023-01-06"
            
            # Event 1: Order BUY (Jan 6)
            assert isinstance(action_events[1], OrderEvent)
            assert action_events[1].direction == "BUY"
            
            # Event 2: Fill BUY (Jan 6)
            assert isinstance(action_events[2], FillEvent)
            assert action_events[2].direction == "BUY"
            
            # Event 3: Signal EXIT (Jan 9)
            assert isinstance(action_events[3], SignalEvent)
            assert action_events[3].signal_type == "EXIT"
            assert action_events[3].time.strftime("%Y-%m-%d") == "2023-01-09"
            
             # Event 4: Order SELL (Jan 9)
            assert isinstance(action_events[4], OrderEvent)
            assert action_events[4].direction == "SELL"
            
            # Event 5: Fill SELL (Jan 9)
            assert isinstance(action_events[5], FillEvent)
            assert action_events[5].direction == "SELL" # FillEvent uses 'SELL' for direction? Let's check Portfolio.
            # Portfolio create_order for EXIT -> direction='SELL'. 
            # Engine FillEvent direction=event.direction. So 'SELL'.
            
            assert len(action_events) == 6
            
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

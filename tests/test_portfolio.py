import pytest
import tempfile
import os
from datetime import datetime
from src.portfolio import Portfolio
from src.events import SignalEvent, FillEvent, MarketEvent
from src.engine import BacktestEngine
from src.data_handler import DataHandler
from src.strategy import BuyAndHoldStrategy

class TestPortfolioUnit:
    def test_initialization(self):
        """Verify initial state."""
        p = Portfolio(100000.0)
        assert p.current_cash == 100000.0
        assert p.holdings['AAPL'] == 0

    def test_update_fill_buy(self):
        """Verify cash and holdings update on BUY fill."""
        p = Portfolio(10000.0)
        fill = FillEvent(
            time=datetime.now(),
            symbol='AAPL',
            quantity=10,
            price=150.0,
            direction='BUY',
            commission=5.0
        )
        p.update_fill(fill)
        
        # Cost = 10 * 150 = 1500 + 5 comm = 1505
        expected_cash = 10000.0 - 1505.0
        assert p.current_cash == expected_cash
        assert p.holdings['AAPL'] == 10

    def test_create_order_long(self):
        """Verify Signal -> Order conversion."""
        p = Portfolio(10000.0)
        signal = SignalEvent(
            time=datetime.now(),
            symbol='AAPL',
            signal_type='LONG'
        )
        order = p.create_order(signal)
        
        assert order is not None
        assert order.symbol == 'AAPL'
        assert order.quantity == 10 # Fixed quantity from logic
        assert order.direction == 'BUY'

class TestPortfolioIntegration:
    def test_full_flow(self):
        """
        Verify: Market -> Strategy -> Signal -> Portfolio -> Order -> Engine -> Fill -> Portfolio Update
        """
        # 1. Setup CSV (Needs enough data to trigger things)
        csv_content = """Date,Close,Volume
2023-01-01,100.0,1000
2023-01-02,101.0,1000
"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=".csv") as tmp:
            tmp.write(csv_content)
            tmp_path = tmp.name

        try:
            # 2. Setup Components
            data_handler = DataHandler(tmp_path, "TEST_SYM")
            portfolio = Portfolio(10000.0)
            strategy = BuyAndHoldStrategy()
            engine = BacktestEngine(data_handler, strategy, portfolio)
            
            # 3. Run
            engine.run()
            
            # 4. Verify End State
            # We expect to have bought 10 shares at 100.0 (first bar)
            # Cash should be 10000 - (10 * 100) = 9000 (assuming 0 comm for simplicity elsewhere or default)
            
            assert portfolio.holdings["TEST_SYM"] == 10
            assert portfolio.current_cash == 9000.0
            
            # Verify Events Flow
            # processed_events should contain:
            # 1. MarketEvent (100.0)
            # 2. SignalEvent (LONG)
            # 3. OrderEvent (BUY 10)
            # 4. FillEvent (BUY 10 @ 100.0)
            # 5. MarketEvent (101.0)
            
            types = [type(e).__name__ for e in engine.processed_events]
            assert "SignalEvent" in types
            assert "OrderEvent" in types
            assert "FillEvent" in types
            
        finally:
            os.remove(tmp_path)

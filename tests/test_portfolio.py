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
        assert p.holdings["AAPL"] == 0

    def test_update_fill_buy(self):
        """Verify cash and holdings update on BUY fill."""
        p = Portfolio(10000.0)
        fill = FillEvent(
            time=datetime.now(),
            symbol="AAPL",
            quantity=10,
            price=150.0,
            direction="BUY",
            commission=5.0,
        )
        p.update_fill(fill)

        # Cost = 10 * 150 = 1500 + 5 comm = 1505
        expected_cash = 10000.0 - 1505.0
        assert p.current_cash == expected_cash
        assert p.holdings["AAPL"] == 10

    def test_create_order_long_risk_based(self):
        """Verify Signal -> Order conversion with risk-based sizing."""
        p = Portfolio(10000.0)
        p.latest_prices["AAPL"] = 100.0  # Setup price for sizing

        signal = SignalEvent(time=datetime.now(), symbol="AAPL", signal_type="LONG")
        # Default risk is 2% (0.02)
        # Equity = 10000. Risk amount = 200.
        # Quantity = 200 / 100 = 2.
        order = p.create_order(signal)

        assert order is not None
        assert order.symbol == "AAPL"
        assert order.quantity == 2
        assert order.direction == "BUY"


    def test_create_order_short(self):
        """SHORT signal should produce a SELL order sized by risk."""
        p = Portfolio(10000.0)
        p.latest_prices["AAPL"] = 100.0

        signal = SignalEvent(time=datetime.now(), symbol="AAPL", signal_type="SHORT")
        order = p.create_order(signal)

        assert order is not None
        assert order.direction == "SELL"
        assert order.quantity == 2  # 10000 * 0.02 / 100 = 2

    def test_exit_covers_short_position(self):
        """EXIT signal should buy-to-cover when holding is negative (short)."""
        p = Portfolio(10000.0)
        p.latest_prices["AAPL"] = 100.0
        # Simulate an open short: we sold 5 shares we didn't own
        p.holdings["AAPL"] = -5

        signal = SignalEvent(time=datetime.now(), symbol="AAPL", signal_type="EXIT")
        order = p.create_order(signal)

        assert order is not None
        assert order.direction == "BUY"
        assert order.quantity == 5

    def test_equity_warns_on_missing_price(self, caplog):
        """Equity calculation should warn when a held symbol has no latest price."""
        import logging

        p = Portfolio(10000.0)
        p.holdings["AAPL"] = 10  # holding with no price in latest_prices

        with caplog.at_level(logging.WARNING, logger="src.portfolio"):
            signal = SignalEvent(time=datetime.now(), symbol="AAPL", signal_type="LONG")
            p.latest_prices["AAPL"] = 100.0  # price for the LONG sizing itself
            # Introduce a second holding with no price to trigger the warning
            p.holdings["MSFT"] = 5
            p.create_order(signal)

        assert any("MSFT" in record.message for record in caplog.records)


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
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".csv") as tmp:
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
            assert (
                portfolio.holdings["TEST_SYM"] > 0
            )  # Risk-based sizing will yield > 0
            # Cash should be reduced by cost + commission
            assert portfolio.current_cash < 10000.0

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

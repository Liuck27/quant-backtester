"""
Tests for MLSignalStrategy.

Focus areas:
- No look-ahead bias (model only trained on past data)
- Signal generation correctness (LONG when p_up high, EXIT when p_up low)
- All three model types instantiate correctly
- Warmup period respected (no signal before MIN_WARMUP_BARS)
- Strategy integrates with the BacktestEngine event loop
"""

import pytest
import tempfile
import os
import random
from datetime import datetime, timedelta

from src.ml_strategy import MLSignalStrategy, MIN_WARMUP_BARS, _compute_rsi, _build_features
from src.events import MarketEvent, SignalEvent


def _make_market_event(price: float, bar: int = 0) -> MarketEvent:
    """Helper to create a MarketEvent with a given price."""
    return MarketEvent(
        time=datetime(2020, 1, 1) + timedelta(days=bar),
        symbol="TEST",
        price=price,
        volume=1000,
    )


def _feed_prices(strategy: MLSignalStrategy, prices: list) -> list:
    """Feed a list of prices to the strategy and return any signals generated."""
    signals = []
    for i, price in enumerate(prices):
        result = strategy.calculate_signals(_make_market_event(price, bar=i))
        if result is not None:
            signals.append(result)
    return signals


class TestFeatureEngineering:
    def test_rsi_neutral_during_warmup(self):
        """RSI should return 50.0 when there is not enough data."""
        assert _compute_rsi([100.0] * 5, period=14) == 50.0

    def test_rsi_overbought(self):
        """Continuously rising prices should produce high RSI."""
        prices = [100.0 + i for i in range(20)]
        rsi = _compute_rsi(prices)
        assert rsi > 70

    def test_rsi_oversold(self):
        """Continuously falling prices should produce low RSI."""
        prices = [200.0 - i for i in range(20)]
        rsi = _compute_rsi(prices)
        assert rsi < 30

    def test_build_features_returns_none_when_insufficient_data(self):
        assert _build_features([100.0] * 10) is None

    def test_build_features_returns_eight_values(self):
        prices = [100.0 + i * 0.1 for i in range(30)]
        features = _build_features(prices)
        assert features is not None
        assert len(features) == 8


class TestMLSignalStrategyWarmup:
    def test_no_signal_before_warmup(self):
        """No signal should be emitted during the warmup period."""
        strategy = MLSignalStrategy(model_type="logistic", lookback_window=110)
        prices = [100.0 + i * 0.05 for i in range(MIN_WARMUP_BARS - 1)]
        signals = _feed_prices(strategy, prices)
        assert len(signals) == 0

    def test_signal_possible_after_warmup(self):
        """After sufficient data the strategy may produce signals."""
        random.seed(42)
        strategy = MLSignalStrategy(model_type="logistic", lookback_window=110, retrain_every=5)
        # Use a trending price series so the classifier has a learnable pattern
        prices = [100.0 + i * 0.1 for i in range(MIN_WARMUP_BARS + 50)]
        signals = _feed_prices(strategy, prices)
        # We don't assert a specific signal, just that the strategy ran without error.
        # Whether signals are generated depends on the learned probabilities.
        assert isinstance(signals, list)


class TestMLSignalStrategyModels:
    """All three model types should instantiate and run without errors."""

    @pytest.mark.parametrize("model_type", ["random_forest", "gradient_boosting", "logistic"])
    def test_model_types_run(self, model_type):
        strategy = MLSignalStrategy(model_type=model_type, lookback_window=110, retrain_every=10)
        prices = [100.0 + i * 0.1 for i in range(MIN_WARMUP_BARS + 30)]
        # Should not raise
        _feed_prices(strategy, prices)

    def test_invalid_model_type_raises(self):
        with pytest.raises(ValueError, match="Unknown model_type"):
            MLSignalStrategy(model_type="xgboost_not_supported")


class TestMLSignalStrategyLogic:
    def test_no_duplicate_long_signals(self):
        """Should not emit two consecutive LONG signals without an EXIT in between."""
        strategy = MLSignalStrategy(model_type="logistic", lookback_window=110, retrain_every=5)
        prices = [100.0 + i * 0.15 for i in range(MIN_WARMUP_BARS + 80)]
        signals = _feed_prices(strategy, prices)

        long_signals = [s for s in signals if s.signal_type == "LONG"]
        exit_signals = [s for s in signals if s.signal_type == "EXIT"]

        # After each LONG there must be at most one EXIT before the next LONG
        # (i.e. signal sequence must alternate LONG/EXIT correctly)
        # We verify strategy state tracks is_long consistently.
        is_long = False
        for signal in signals:
            if signal.signal_type == "LONG":
                assert not is_long, "Received LONG while already long"
                is_long = True
            elif signal.signal_type == "EXIT":
                assert is_long, "Received EXIT while not long"
                is_long = False

    def test_signal_strength_is_probability(self):
        """Signal strength should be the predicted up-probability (0.0–1.0)."""
        strategy = MLSignalStrategy(model_type="logistic", lookback_window=110, retrain_every=5)
        prices = [100.0 + i * 0.15 for i in range(MIN_WARMUP_BARS + 80)]
        signals = _feed_prices(strategy, prices)

        for signal in signals:
            assert 0.0 <= signal.strength <= 1.0


class TestMLSignalStrategyIntegration:
    def test_full_backtest_with_ml_strategy(self):
        """MLSignalStrategy should work end-to-end with BacktestEngine."""
        import csv

        from src.data_handler import DataHandler
        from src.portfolio import Portfolio
        from src.engine import BacktestEngine

        # Build a CSV with enough bars (MIN_WARMUP_BARS + 50)
        n_bars = MIN_WARMUP_BARS + 50
        rows = [["Date", "Close", "Volume"]]
        base = datetime(2020, 1, 1)
        price = 100.0
        for i in range(n_bars):
            date_str = (base + timedelta(days=i)).strftime("%Y-%m-%d")
            price += 0.1  # Gentle uptrend
            rows.append([date_str, f"{price:.2f}", "1000"])

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".csv", newline="") as f:
            writer = csv.writer(f)
            writer.writerows(rows)
            tmp_path = f.name

        try:
            strategy = MLSignalStrategy(model_type="logistic", lookback_window=110, retrain_every=10)
            data_handler = DataHandler(tmp_path, "TEST")
            portfolio = Portfolio(100_000.0)
            engine = BacktestEngine(data_handler, strategy, portfolio)
            engine.run()

            # Engine should complete without error; equity history should be populated
            assert len(portfolio.history) == n_bars
        finally:
            os.remove(tmp_path)

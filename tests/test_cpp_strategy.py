import pytest
from datetime import datetime
from src.events import MarketEvent
from src.strategy import CppMovingAverageCrossStrategy, MovingAverageCrossStrategy

try:
    import quant_strategy_cpp

    CPP_AVAILABLE = True
except ImportError:
    CPP_AVAILABLE = False


@pytest.mark.skipif(not CPP_AVAILABLE, reason="C++ extension not built")
class TestCppMovingAverageStrategy:
    def test_equivalence_with_python(self):
        """
        Verify that C++ strategy produces identical results to Python strategy.
        """
        cpp_strategy = CppMovingAverageCrossStrategy(short_window=5, long_window=10)
        py_strategy = MovingAverageCrossStrategy(short_window=5, long_window=10)

        prices = [100.0 + i for i in range(20)]  # Uptrend
        prices += [120.0 - i * 2 for i in range(20)]  # Downtrend

        for i, p in enumerate(prices):
            event = MarketEvent(datetime.now(), "TEST", p, 100)

            cpp_signal = cpp_strategy.calculate_signals(event)
            py_signal = py_strategy.calculate_signals(event)

            # Check Signal type
            if py_signal is None:
                assert cpp_signal is None, f"Step {i}: Python None, C++ {cpp_signal}"
            else:
                assert (
                    cpp_signal is not None
                ), f"Step {i}: Python {py_signal.signal_type}, C++ None"
                assert cpp_signal.signal_type == py_signal.signal_type
                assert cpp_signal.symbol == py_signal.symbol

            # Check internal state
            assert cpp_strategy.bought == py_strategy.bought

    def test_golden_cross_long(self):
        """Verify LONG signal on Golden Cross."""
        strategy = CppMovingAverageCrossStrategy(short_window=2, long_window=4)

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

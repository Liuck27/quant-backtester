from abc import ABC, abstractmethod
from typing import Optional, List
from src.events import MarketEvent, SignalEvent


class Strategy(ABC):
    """
    Abstract Base Class for all trading strategies.
    Apps logic to MarketEvents to generate SignalEvents.
    """

    @abstractmethod
    def calculate_signals(self, event: MarketEvent) -> Optional[SignalEvent]:
        """
        Calculates signals based on market data.

        Args:
            event (MarketEvent): The latest market data event.

        Returns:
            Optional[SignalEvent]: A signal event if generated, else None.
        """
        pass


class BuyAndHoldStrategy(Strategy):
    """
    Naive strategy that generates a LONG signal on the first received bar
    and then does nothing.
    """

    def __init__(self):
        self.bought = False

    def calculate_signals(self, event: MarketEvent) -> Optional[SignalEvent]:
        if not isinstance(event, MarketEvent):
            return None

        if not self.bought:
            self.bought = True
            return SignalEvent(time=event.time, symbol=event.symbol, signal_type="LONG")
        return None


class MovingAverageCrossStrategy(Strategy):
    """
    Stateful strategy using Simple Moving Average (SMA) Crossover.

    Logic:
    - LONG (Golden Cross): Short SMA crosses above Long SMA.
    - EXIT (Death Cross): Short SMA crosses below Long SMA.

    Note:
    - Currently implements LONG/EXIT only (no shorting).
    - Can be extended to LONG/SHORT reversal system in the future.
    """

    def __init__(self, short_window: int = 10, long_window: int = 30):
        self.short_window = short_window
        self.long_window = long_window
        self.prices: List[float] = []  # History of closing prices
        self.bought = False

    def calculate_signals(self, event: MarketEvent) -> Optional[SignalEvent]:
        if not isinstance(event, MarketEvent):
            return None

        # Update history
        self.prices.append(event.price)

        # Warm-up period
        if len(self.prices) < self.long_window:
            return None

        # Calculate SMAs
        # We need the last 'window' prices
        short_prices = self.prices[-self.short_window :]
        long_prices = self.prices[-self.long_window :]

        short_sma = sum(short_prices) / self.short_window
        long_sma = sum(long_prices) / self.long_window

        # Generate Signals
        signal_type = None

        # Golden Cross: Short > Long (and we are flat)
        if short_sma > long_sma and not self.bought:
            self.bought = True
            signal_type = "LONG"

        # Death Cross: Short < Long (and we are Long)
        elif short_sma < long_sma and self.bought:
            self.bought = False
            signal_type = "EXIT"

        if signal_type:
            return SignalEvent(
                time=event.time,
                symbol=event.symbol,
                signal_type=signal_type,
                strength=1.0,  # Default strength
            )

        return None


try:
    import quant_strategy_cpp

    class CppMovingAverageCrossStrategy(Strategy):
        """
        Optimized version of MovingAverageCrossStrategy using C++ extension.
        """

        def __init__(self, short_window: int = 10, long_window: int = 30):
            self._cpp_strategy = quant_strategy_cpp.CppMovingAverageCrossStrategy(
                short_window, long_window
            )

        def calculate_signals(self, event: MarketEvent) -> Optional[SignalEvent]:
            if not isinstance(event, MarketEvent):
                return None

            # Convert Python Event to C++ MinimalMarketEvent
            # Note: time is passed as string
            cpp_event = quant_strategy_cpp.MinimalMarketEvent(
                str(event.time), event.symbol, event.price, event.volume
            )

            # Call C++ method
            result = self._cpp_strategy.calculate_signals(cpp_event)

            # Convert result back to Python SignalEvent
            if result:
                return SignalEvent(
                    time=event.time,  # Reuse original event time or parse result.time
                    symbol=result.symbol,
                    signal_type=result.signal_type,
                    strength=result.strength,
                )

            return None

        def calculate_signal_fast(self, price: float) -> int:
            """
            Direct fast path to C++ logic, bypassing Event objects.
            Returns: 1 (LONG), -1 (EXIT), 0 (NONE)
            """
            return self._cpp_strategy.calculate_signal_fast(price)

        # Expose testing helpers
        @property
        def bought(self):
            return self._cpp_strategy.is_bought()

        @property
        def prices(self):
            return self._cpp_strategy.get_prices()

except ImportError:
    print(
        "Warning: C++ extension 'quant_strategy_cpp' not found or could not be imported. CppMovingAverageCrossStrategy will not be available."
    )
    CppMovingAverageCrossStrategy = None
    pass

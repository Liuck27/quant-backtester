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


class RSIStrategy(Strategy):
    """
    RSI Mean-Reversion Strategy.

    Logic:
    - LONG when RSI drops below the oversold threshold (e.g. 30).
    - EXIT when RSI rises above the overbought threshold (e.g. 70).
    """

    def __init__(self, rsi_period: int = 14, oversold: float = 30.0, overbought: float = 70.0):
        self.rsi_period = rsi_period
        self.oversold = oversold
        self.overbought = overbought
        self.prices: List[float] = []
        self.bought = False

    def _calc_rsi(self) -> Optional[float]:
        if len(self.prices) < self.rsi_period + 1:
            return None
        deltas = [self.prices[i] - self.prices[i - 1] for i in range(-self.rsi_period, 0)]
        gains = sum(d for d in deltas if d > 0) / self.rsi_period
        losses = sum(-d for d in deltas if d < 0) / self.rsi_period
        if losses == 0:
            return 100.0
        rs = gains / losses
        return 100.0 - (100.0 / (1.0 + rs))

    def calculate_signals(self, event: MarketEvent) -> Optional[SignalEvent]:
        if not isinstance(event, MarketEvent):
            return None
        self.prices.append(event.price)
        rsi = self._calc_rsi()
        if rsi is None:
            return None
        signal_type = None
        if rsi < self.oversold and not self.bought:
            self.bought = True
            signal_type = "LONG"
        elif rsi > self.overbought and self.bought:
            self.bought = False
            signal_type = "EXIT"
        if signal_type:
            return SignalEvent(
                time=event.time,
                symbol=event.symbol,
                signal_type=signal_type,
                strength=1.0,
            )
        return None

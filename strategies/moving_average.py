import pandas as pd


class MovingAverageStrategy:
    """
    Simple Moving Average Crossover Strategy.

    When the short moving average crosses above the long one -> buy signal (+1).
    When it crosses below -> sell signal (-1).
    """

    def __init__(self, short_window: int, long_window: int):
        self.short_window = short_window
        self.long_window = long_window

    def generate_signals(self, prices: pd.Series) -> pd.Series:
        """
        Generate trading signals (+1 = buy, -1 = sell, 0 = hold).

        Args:
            prices: pandas Series of closing prices

        Returns:
            pandas Series of signals indexed by date.
        """
        # Computing Moving Average
        short_ma = prices.rolling(window=self.short_window, min_periods=1).mean()
        long_ma = prices.rolling(window=self.long_window, min_periods=1).mean()

        # True if short MA > long MA
        condition = short_ma > long_ma

        # Convert True/False in int (1/0)
        position = condition.astype(int)

        # +1 -> bullish cross, -1 -> bearish cross
        signals = position.diff().fillna(0)
        signals = signals.astype(int)

        return signals

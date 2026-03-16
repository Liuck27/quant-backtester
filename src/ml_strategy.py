"""
ML-based trading strategy using scikit-learn classifiers.

Trains a binary classifier to predict whether the next bar will close higher
or lower than the current bar. Generates LONG/EXIT signals based on the
predicted probability.

No look-ahead bias: the model is only ever trained on bars that occurred
strictly before the current bar.
"""

import logging
from typing import Optional, List

import numpy as np

from src.events import MarketEvent, SignalEvent
from src.strategy import Strategy

logger = logging.getLogger(__name__)

# Minimum bars required before the model can make its first prediction.
# Needs: 20-period features + 14-period RSI + enough history to train on.
MIN_WARMUP_BARS = 100


def _compute_rsi(prices: List[float], period: int = 14) -> float:
    """Compute RSI for the most recent bar given a price list."""
    if len(prices) < period + 1:
        return 50.0  # Neutral value during warmup

    deltas = [prices[i] - prices[i - 1] for i in range(-period, 0)]
    gains = [d for d in deltas if d > 0]
    losses = [-d for d in deltas if d < 0]

    avg_gain = sum(gains) / period if gains else 0.0
    avg_loss = sum(losses) / period if losses else 1e-10  # Avoid division by zero

    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def _build_features(prices: List[float]) -> Optional[List[float]]:
    """
    Build a feature vector from the tail of a price history list.

    Features (all computed from past data only):
      - 1, 5, 10, 20-bar returns
      - 5 and 10-bar rolling return standard deviation (volatility proxy)
      - 10/20-bar SMA ratio minus 1 (trend direction)
      - 14-bar RSI

    Returns None if there is not enough history.
    """
    if len(prices) < 21:
        return None

    p = prices  # Alias for brevity

    # Returns
    ret_1 = (p[-1] - p[-2]) / p[-2] if p[-2] != 0 else 0.0
    ret_5 = (p[-1] - p[-6]) / p[-6] if len(p) >= 6 and p[-6] != 0 else 0.0
    ret_10 = (p[-1] - p[-11]) / p[-11] if len(p) >= 11 and p[-11] != 0 else 0.0
    ret_20 = (p[-1] - p[-21]) / p[-21] if len(p) >= 21 and p[-21] != 0 else 0.0

    # Volatility (rolling std of daily returns)
    recent_rets_5 = [(p[i] - p[i - 1]) / p[i - 1] for i in range(-5, 0) if p[i - 1] != 0]
    recent_rets_10 = [(p[i] - p[i - 1]) / p[i - 1] for i in range(-10, 0) if p[i - 1] != 0]
    vol_5 = float(np.std(recent_rets_5)) if len(recent_rets_5) >= 2 else 0.0
    vol_10 = float(np.std(recent_rets_10)) if len(recent_rets_10) >= 2 else 0.0

    # Trend: short/long SMA ratio
    sma_10 = sum(p[-10:]) / 10
    sma_20 = sum(p[-20:]) / 20
    sma_ratio = (sma_10 / sma_20 - 1.0) if sma_20 != 0 else 0.0

    # RSI
    rsi = _compute_rsi(p)

    return [ret_1, ret_5, ret_10, ret_20, vol_5, vol_10, sma_ratio, rsi]


class MLSignalStrategy(Strategy):
    """
    Classifier-based strategy that predicts next-bar direction.

    Parameters
    ----------
    model_type : str
        One of "random_forest", "gradient_boosting", "logistic".
    lookback_window : int
        Number of past bars used as training data. Default 252 (~1 trading year).
    retrain_every : int
        Retrain the model every N bars. Default 20 (monthly on daily data).
    long_threshold : float
        Predicted probability above which a LONG signal is generated. Default 0.6.
    exit_threshold : float
        Predicted probability below which an EXIT signal is generated. Default 0.4.
    """

    def __init__(
        self,
        model_type: str = "random_forest",
        lookback_window: int = 252,
        retrain_every: int = 20,
        long_threshold: float = 0.6,
        exit_threshold: float = 0.4,
    ):
        self.model_type = model_type
        self.lookback_window = lookback_window
        self.retrain_every = retrain_every
        self.long_threshold = long_threshold
        self.exit_threshold = exit_threshold

        valid_models = {"random_forest", "gradient_boosting", "logistic"}
        if model_type not in valid_models:
            raise ValueError(
                f"Unknown model_type '{model_type}'. Choose from: {', '.join(sorted(valid_models))}."
            )

        self.prices: List[float] = []
        self.bars_since_retrain: int = 0
        self.model = None
        self.is_long: bool = False
        self._model_trained: bool = False

    def _build_model(self):
        """Instantiate the sklearn classifier."""
        from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
        from sklearn.linear_model import LogisticRegression

        if self.model_type == "random_forest":
            return RandomForestClassifier(n_estimators=100, max_depth=4, random_state=42, n_jobs=-1)
        elif self.model_type == "gradient_boosting":
            return GradientBoostingClassifier(n_estimators=100, max_depth=3, random_state=42)
        elif self.model_type == "logistic":
            return LogisticRegression(max_iter=500, random_state=42)
        else:
            raise ValueError(
                f"Unknown model_type '{self.model_type}'. "
                "Choose from: random_forest, gradient_boosting, logistic."
            )

    def _train(self) -> bool:
        """
        Train the classifier on recent price history.

        Uses a sliding window of `lookback_window` bars. Each training sample
        is a feature vector built from bar t, with a label of 1 if price[t+1]
        > price[t] (next bar up) and 0 otherwise.

        Returns True if training succeeded, False if there is not enough data.
        """
        prices = self.prices
        window = min(len(prices) - 1, self.lookback_window)

        if window < MIN_WARMUP_BARS:
            return False

        X, y = [], []
        start = len(prices) - window - 1  # Leave the last bar for prediction

        for i in range(start, len(prices) - 1):
            features = _build_features(prices[: i + 1])
            if features is None:
                continue
            label = 1 if prices[i + 1] > prices[i] else 0
            X.append(features)
            y.append(label)

        if len(X) < 20 or len(set(y)) < 2:
            # Too few samples or only one class — skip this training round
            return False

        X_arr = np.array(X, dtype=np.float64)
        y_arr = np.array(y, dtype=np.int32)

        if self.model is None:
            self.model = self._build_model()

        self.model.fit(X_arr, y_arr)
        logger.debug(
            f"[MLSignalStrategy] Retrained {self.model_type} on {len(X)} samples."
        )
        return True

    def calculate_signals(self, event: MarketEvent) -> Optional[SignalEvent]:
        if not isinstance(event, MarketEvent):
            return None

        self.prices.append(event.price)
        self.bars_since_retrain += 1

        # Not enough data to do anything yet
        if len(self.prices) < MIN_WARMUP_BARS + 1:
            return None

        # Retrain on schedule
        if not self._model_trained or self.bars_since_retrain >= self.retrain_every:
            success = self._train()
            if success:
                self._model_trained = True
                self.bars_since_retrain = 0
            elif not self._model_trained:
                return None  # Still warming up

        # Build features for the current bar
        features = _build_features(self.prices)
        if features is None or self.model is None:
            return None

        # Predict probability that next bar closes up
        proba = self.model.predict_proba([features])[0]
        # proba[1] = probability of class 1 (next bar up)
        p_up = proba[1]

        signal_type = None
        if p_up >= self.long_threshold and not self.is_long:
            self.is_long = True
            signal_type = "LONG"
        elif p_up <= self.exit_threshold and self.is_long:
            self.is_long = False
            signal_type = "EXIT"

        if signal_type:
            logger.info(
                f"[MLSignalStrategy] {signal_type} signal for {event.symbol} "
                f"| p_up={p_up:.3f} | model={self.model_type}"
            )
            return SignalEvent(
                time=event.time,
                symbol=event.symbol,
                signal_type=signal_type,
                strength=float(p_up),
            )

        return None

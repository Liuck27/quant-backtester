import pandas as pd


def run_backtest(
    prices: pd.DataFrame, signals: pd.Series, initial_cash: float = 10_000.0
) -> pd.DataFrame:
    """
    Run a simple vectorized backtest.

    Args:
        prices: DataFrame with 'close' column and datetime index.
        signals: Series of +1 (buy), -1 (sell) change signals.
        initial_cash: starting capital.

    Returns:
        DataFrame with:
            - 'returns': asset daily returns
            - 'position': current position (1 = long, 0 = flat)
            - 'strategy_returns': daily returns of the strategy
            - 'equity_curve': cumulative portfolio value
    """

    df = pd.concat([prices, signals], axis=1)
    df.columns = ["close", "signal"]

    df["signal"] = signals.reindex(df.index).fillna(0)

    # Compute daily asset returns
    df["returns"] = df["close"].pct_change().fillna(0)

    # Build the position series over time
    position = []
    current_pos = 0

    for sig in df["signal"]:
        if sig == 1:
            current_pos = 1  # enter long
        elif sig == -1:
            current_pos = 0  # exit (flat)
        position.append(current_pos)

    df["position"] = position

    # Strategy return = daily asset return * previous day's position
    df["strategy_returns"] = df["position"].shift(1) * df["returns"]

    df = df.iloc[1:]  # Remove first row (empty after shifting)

    # Cumulative portfolio value
    df["equity_curve"] = (1 + df["strategy_returns"]).cumprod() * initial_cash

    return df

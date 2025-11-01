import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


def total_return(equity_curve: pd.Series) -> float:
    """Compute total return from start to end."""
    # (final value / initial value) - 1
    return (equity_curve.iloc[-1] / equity_curve.iloc[0]) - 1


def max_drawdown(equity_curve: pd.Series) -> float:
    """Compute the maximum drawdown (as a negative fraction)."""
    # Compute the running maximum of the equity curve
    running_max = equity_curve.cummax()
    # Compute drawdown at each point
    drawdown = equity_curve / running_max - 1.0
    # Return the minimum drawdown (most negative)
    return drawdown.min()


def sharpe_ratio(returns: pd.Series, risk_free_rate: float = 0.0) -> float:
    """Compute the annualized Sharpe ratio."""
    # Excess returns above risk-free rate
    excess_returns = returns - risk_free_rate / 252  # assuming daily returns
    # Annualized Sharpe ratio = mean / std * sqrt(252)
    if excess_returns.std() == 0:
        return np.nan
    return np.sqrt(252) * excess_returns.mean() / excess_returns.std()


def compute_metrics(
    equity_curve: pd.Series, returns: pd.Series, risk_free_rate: float = 0.0
) -> dict:
    """
    Bundle metrics into a dictionary for easy reporting.

    Args:
        equity_curve: portfolio value over time
        returns: daily returns of the strategy
        risk_free_rate: annual risk-free rate (e.g. 0.03 for 3%)

    Returns:
        dict with total_return, max_drawdown, sharpe_ratio
    """
    return {
        "total_return": total_return(equity_curve),
        "max_drawdown": max_drawdown(equity_curve),
        "sharpe_ratio": sharpe_ratio(returns, risk_free_rate),
    }


def plot_backtest_with_signals(
    equity_curve: pd.Series, returns: pd.Series, signals: pd.Series, metrics: dict
):
    """
    Plot equity curve with buy/sell signals, daily returns, and show metrics.

    Args:
        equity_curve: pd.Series of portfolio value over time
        returns: pd.Series of strategy daily returns
        signals: pd.Series of signals (1=buy, -1=sell, 0=hold)
        metrics: dict from compute_metrics
    """
    fig, axs = plt.subplots(2, 1, figsize=(14, 8), sharex=True)

    # Equity curve
    axs[0].plot(
        equity_curve.index, equity_curve.values, label="Equity Curve", color="blue"
    )

    # Mark buy signals
    buy_signals = signals[signals == 1].index
    axs[0].scatter(
        buy_signals,
        equity_curve.loc[buy_signals],
        marker="^",
        color="green",
        label="Buy",
        s=100,
    )

    # Mark sell signals
    sell_signals = signals[signals == -1].index
    axs[0].scatter(
        sell_signals,
        equity_curve.loc[sell_signals],
        marker="v",
        color="red",
        label="Sell",
        s=100,
    )

    axs[0].set_ylabel("Portfolio Value")
    axs[0].set_title("Equity Curve with Buy/Sell Signals")
    axs[0].legend()
    axs[0].grid(True)

    # Daily returns
    axs[1].bar(returns.index, returns.values, color="grey")
    axs[1].set_ylabel("Daily Returns")
    axs[1].set_title("Strategy Daily Returns")
    axs[1].grid(True)

    plt.tight_layout()
    plt.show()

    # Print metrics
    print("=== Backtest Metrics ===")
    for k, v in metrics.items():
        if k == "sharpe_ratio":
            print(f"{k}: {v:.2f}")
        else:
            print(f"{k}: {v:.4f}")

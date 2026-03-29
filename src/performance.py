import pandas as pd
import numpy as np
from collections import deque
from typing import Dict, List, Optional


def create_equity_curve(portfolio_history: List[Dict]) -> pd.DataFrame:
    """
    Converts the portfolio history list into a pandas DataFrame.

    Args:
        portfolio_history (List[Dict]): The history list from Portfolio.

    Returns:
        pd.DataFrame: DataFrame indexed by datetime with equity, returns, etc.
    """
    if not portfolio_history:
        return pd.DataFrame()

    df = pd.DataFrame(portfolio_history)
    df.set_index("datetime", inplace=True)
    df.sort_index(inplace=True)

    # Calculate Returns
    df["returns"] = df["equity"].pct_change().fillna(0.0)
    df["cum_returns"] = (1 + df["returns"]).cumprod() - 1.0

    return df


def calculate_drawdown(equity_curve: pd.DataFrame) -> pd.Series:
    """
    Calculates the drawdown series.
    """
    if equity_curve.empty:
        return pd.Series()

    # High Water Mark
    hwm = equity_curve["equity"].cummax()
    drawdown = (equity_curve["equity"] - hwm) / hwm
    return drawdown


def calculate_sharpe_ratio(
    equity_curve: pd.DataFrame, risk_free_rate: float = 0.0, periods: int = 252
) -> float:
    """
    Calculates the annualized Sharpe Ratio.
    """
    if equity_curve.empty:
        return 0.0

    returns = equity_curve["returns"]
    if returns.std() == 0:
        return 0.0

    sharpe = (returns.mean() - risk_free_rate) / returns.std()
    return sharpe * np.sqrt(periods)


def calculate_win_rate(trades: List[Dict]) -> Optional[float]:
    """
    Calculates win rate by FIFO-matching BUY/SELL pairs.
    A win is a SELL that closes at a price above average cost basis.
    Returns None if there are no closed trades (no matched pairs).
    """
    buy_queue: deque = deque()  # (price, qty)
    wins = 0
    total_closed = 0

    for t in trades:
        if t["direction"] == "BUY":
            buy_queue.append((t["price"], t["quantity"]))
        elif t["direction"] == "SELL":
            remaining = t["quantity"]
            sell_price = t["price"]
            cost_basis = 0.0
            matched_qty = 0

            while remaining > 0 and buy_queue:
                buy_price, buy_qty = buy_queue[0]
                take = min(remaining, buy_qty)
                cost_basis += take * buy_price
                matched_qty += take
                remaining -= take
                if take == buy_qty:
                    buy_queue.popleft()
                else:
                    buy_queue[0] = (buy_price, buy_qty - take)

            if matched_qty > 0:
                avg_cost = cost_basis / matched_qty
                if sell_price > avg_cost:
                    wins += 1
                total_closed += 1

    if total_closed == 0:
        return None
    return (wins / total_closed) * 100


def calculate_total_return(equity_curve: pd.DataFrame) -> float:
    """
    Calculates the total percentage return.
    """
    if equity_curve.empty:
        return 0.0

    initial_equity = equity_curve["equity"].iloc[0]
    final_equity = equity_curve["equity"].iloc[-1]

    if initial_equity == 0:
        return 0.0

    return (final_equity - initial_equity) / initial_equity

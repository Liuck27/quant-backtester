import pandas as pd
import numpy as np
from typing import Dict, List

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
    df.set_index('datetime', inplace=True)
    df.sort_index(inplace=True)
    
    # Calculate Returns
    df['returns'] = df['equity'].pct_change().fillna(0.0)
    df['cum_returns'] = (1 + df['returns']).cumprod() - 1.0
    
    return df

def calculate_drawdown(equity_curve: pd.DataFrame) -> pd.Series:
    """
    Calculates the drawdown series.
    """
    if equity_curve.empty:
        return pd.Series()
        
    # High Water Mark
    hwm = equity_curve['equity'].cummax()
    drawdown = (equity_curve['equity'] - hwm) / hwm
    return drawdown

def calculate_sharpe_ratio(equity_curve: pd.DataFrame, risk_free_rate: float = 0.0, periods: int = 252) -> float:
    """
    Calculates the annualized Sharpe Ratio.
    """
    if equity_curve.empty:
        return 0.0
        
    returns = equity_curve['returns']
    if returns.std() == 0:
        return 0.0
        
    sharpe = (returns.mean() - risk_free_rate) / returns.std()
    return sharpe * np.sqrt(periods)

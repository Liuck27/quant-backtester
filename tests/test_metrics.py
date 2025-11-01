import pandas as pd
import numpy as np
from backtester.metrics import total_return, max_drawdown, sharpe_ratio

def test_total_return():
    equity = pd.Series([100, 110, 121])
    assert round(total_return(equity), 2) == 0.21  # 21% growth

def test_max_drawdown():
    equity = pd.Series([100, 120, 90, 130])
    dd = max_drawdown(equity)
    assert dd < 0  # drawdown is negative

def test_sharpe_ratio():
    returns = pd.Series(np.random.normal(0.001, 0.01, 252))
    sr = sharpe_ratio(returns)
    assert isinstance(sr, float)

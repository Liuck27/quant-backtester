import pytest
import pandas as pd
from datetime import datetime
from src.performance import (
    create_equity_curve,
    calculate_drawdown,
    calculate_sharpe_ratio,
    calculate_total_return,
)


class TestPerformance:
    def test_equity_curve_generation(self):
        """Verify dataframe creation from history."""
        history = [
            {
                "datetime": datetime(2023, 1, 1),
                "cash": 100,
                "equity": 100,
                "holdings_value": 0,
            },
            {
                "datetime": datetime(2023, 1, 2),
                "cash": 100,
                "equity": 110,
                "holdings_value": 10,
            },
        ]
        df = create_equity_curve(history)

        assert len(df) == 2
        assert "returns" in df.columns
        assert df.iloc[0]["returns"] == 0.0
        assert df.iloc[1]["returns"] == pytest.approx(0.10)  # 10% gain

    def test_sharpe_ratio(self):
        """Verify Sharpe calculation (naive check)."""
        history = [
            {"datetime": datetime(2023, 1, 1), "equity": 100},
            {"datetime": datetime(2023, 1, 2), "equity": 101},
            {"datetime": datetime(2023, 1, 3), "equity": 102},
            # Stable returns, positive sharpe
        ]
        df = create_equity_curve(history)
        sharpe = calculate_sharpe_ratio(df)
        assert sharpe > 0

    def test_drawdown(self):
        """Verify drawdown calculation."""
        history = [
            {"datetime": datetime(2023, 1, 1), "equity": 100},
            {"datetime": datetime(2023, 1, 2), "equity": 90},  # -10% DD
            {"datetime": datetime(2023, 1, 3), "equity": 100},
        ]
        df = create_equity_curve(history)
        dd = calculate_drawdown(df)

        assert dd.iloc[0] == 0.0
        assert dd.iloc[1] == -0.10
        assert dd.iloc[2] == 0.0

    def test_total_return(self):
        """Verify total return calculation."""
        history = [
            {"datetime": datetime(2023, 1, 1), "equity": 100},
            {"datetime": datetime(2023, 1, 2), "equity": 150},
        ]
        df = pd.DataFrame(history)
        ret = calculate_total_return(df)
        assert ret == 0.50

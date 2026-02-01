"""
Tests for Walk-Forward Analysis Module
"""

import pytest
import tempfile
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from src.walk_forward import WalkForwardAnalyzer
from src.strategy import MovingAverageCrossStrategy


class TestWalkForwardWindows:
    """Tests for window generation logic."""

    def create_temp_csv(self, length: int) -> str:
        """Helper to create a temporary CSV with synthetic data."""
        np.random.seed(42)
        dates = [datetime(2023, 1, 1) + timedelta(days=i) for i in range(length)]
        prices = 100 + np.cumsum(np.random.randn(length) * 0.5)

        df = pd.DataFrame({"Date": dates, "Close": prices, "Volume": 1000})

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".csv") as tmp:
            df.to_csv(tmp, index=False)
            return tmp.name

    def test_window_generation_count(self):
        """Verify correct number of windows are generated."""
        tmp_path = self.create_temp_csv(100)

        try:
            # 100 bars, in_sample=50, out_of_sample=20
            # Window size = 70, step = 20
            # Windows: [0:70], [20:90] = 2 windows (100 does not fit 3rd)
            # Actually: start=0 -> [0:50, 50:70], start=20 -> [20:70, 70:90], start=40 -> 40+70=110 > 100 -> stop
            # So 2 windows.

            analyzer = WalkForwardAnalyzer(
                data_path=tmp_path,
                symbol="TEST",
                strategy_cls=MovingAverageCrossStrategy,
                param_grid={"short_window": [5], "long_window": [10]},
                in_sample_periods=50,
                out_of_sample_periods=20,
            )

            windows = analyzer.generate_windows()
            assert len(windows) == 2

            # Verify window sizes
            is_1, oos_1 = windows[0]
            assert len(is_1) == 50
            assert len(oos_1) == 20

        finally:
            os.remove(tmp_path)

    def test_window_no_overlap_in_oos(self):
        """Verify OOS periods don't overlap."""
        tmp_path = self.create_temp_csv(120)

        try:
            analyzer = WalkForwardAnalyzer(
                data_path=tmp_path,
                symbol="TEST",
                strategy_cls=MovingAverageCrossStrategy,
                param_grid={"short_window": [5], "long_window": [10]},
                in_sample_periods=50,
                out_of_sample_periods=20,
            )

            windows = analyzer.generate_windows()

            # OOS windows should be non-overlapping
            oos_1_dates = set(windows[0][1]["Date"])
            oos_2_dates = set(windows[1][1]["Date"])

            # No common dates between OOS windows
            assert len(oos_1_dates & oos_2_dates) == 0

        finally:
            os.remove(tmp_path)


class TestWalkForwardExecution:
    """Integration tests for walk-forward analysis."""

    def create_temp_csv(self, length: int) -> str:
        """Helper to create a temporary CSV with synthetic data."""
        np.random.seed(42)
        dates = [datetime(2023, 1, 1) + timedelta(days=i) for i in range(length)]
        prices = 100 + np.cumsum(np.random.randn(length) * 0.5)

        df = pd.DataFrame({"Date": dates, "Close": prices, "Volume": 1000})

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".csv") as tmp:
            df.to_csv(tmp, index=False)
            return tmp.name

    def test_end_to_end_walk_forward(self):
        """Run a complete walk-forward analysis and verify output structure."""
        tmp_path = self.create_temp_csv(150)

        try:
            analyzer = WalkForwardAnalyzer(
                data_path=tmp_path,
                symbol="TEST",
                strategy_cls=MovingAverageCrossStrategy,
                param_grid={"short_window": [5, 10], "long_window": [20, 30]},
                in_sample_periods=60,
                out_of_sample_periods=30,
            )

            results_df = analyzer.run()

            # Verify output structure
            assert isinstance(results_df, pd.DataFrame)
            assert len(results_df) > 0

            # Check required columns
            expected_cols = [
                "Window",
                "OOS_Total_Return",
                "OOS_Sharpe_Ratio",
                "OOS_Max_Drawdown",
            ]
            for col in expected_cols:
                assert col in results_df.columns

            # Verify metrics are numeric
            assert pd.api.types.is_numeric_dtype(results_df["OOS_Total_Return"])

        finally:
            os.remove(tmp_path)

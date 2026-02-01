"""
Walk-Forward Analysis Module

Provides tools for validating trading strategies using a rolling
in-sample optimization and out-of-sample testing methodology.
This helps prevent overfitting by ensuring strategies perform well
on unseen data.
"""

import pandas as pd
import logging
from typing import Dict, List, Type, Any, Tuple
from src.engine import BacktestEngine
from src.data_handler import DataHandler
from src.data_loader import CSVDataLoader
from src.portfolio import Portfolio
from src.strategy import Strategy
from src.performance import (
    create_equity_curve,
    calculate_sharpe_ratio,
    calculate_drawdown,
)

logger = logging.getLogger(__name__)


class WalkForwardAnalyzer:
    """
    Performs Walk-Forward Analysis on a trading strategy.

    The data is split into rolling windows:
    1. In-Sample (IS): Used to optimize strategy parameters.
    2. Out-of-Sample (OOS): Used to validate the optimized parameters.

    This process is repeated, "walking forward" through the data.
    """

    def __init__(
        self,
        data_path: str,
        symbol: str,
        strategy_cls: Type[Strategy],
        param_grid: Dict[str, List[Any]],
        in_sample_periods: int,
        out_of_sample_periods: int,
    ):
        """
        Args:
            data_path: Path to CSV data file.
            symbol: Ticker symbol.
            strategy_cls: Strategy class to optimize.
            param_grid: Dictionary of parameter names to lists of values.
            in_sample_periods: Number of bars for in-sample optimization.
            out_of_sample_periods: Number of bars for out-of-sample testing.
        """
        self.data_path = data_path
        self.symbol = symbol
        self.strategy_cls = strategy_cls
        self.param_grid = param_grid
        self.in_sample_periods = in_sample_periods
        self.out_of_sample_periods = out_of_sample_periods

        # Load full dataset
        self.full_data = self._load_full_data()

    def _load_full_data(self) -> pd.DataFrame:
        """Loads the full dataset from CSV."""
        loader = CSVDataLoader(self.data_path)
        df = loader.load_data()
        df["Date"] = pd.to_datetime(df["Date"])
        df = df.sort_values("Date").reset_index(drop=True)
        return df

    def generate_windows(self) -> List[Tuple[pd.DataFrame, pd.DataFrame]]:
        """
        Generates rolling (in-sample, out-of-sample) window pairs.

        Returns:
            List of tuples: [(is_df_1, oos_df_1), (is_df_2, oos_df_2), ...]
        """
        windows = []
        window_size = self.in_sample_periods + self.out_of_sample_periods
        total_bars = len(self.full_data)

        start_idx = 0
        while start_idx + window_size <= total_bars:
            is_end = start_idx + self.in_sample_periods
            oos_end = is_end + self.out_of_sample_periods

            is_data = self.full_data.iloc[start_idx:is_end].copy()
            oos_data = self.full_data.iloc[is_end:oos_end].copy()

            windows.append((is_data, oos_data))

            # Walk forward by out_of_sample_periods
            start_idx += self.out_of_sample_periods

        logger.info(f"Generated {len(windows)} walk-forward windows.")
        return windows

    def _run_backtest_on_data(
        self, data: pd.DataFrame, params: Dict[str, Any]
    ) -> Dict[str, float]:
        """Runs a single backtest on a DataFrame slice with given parameters."""
        import tempfile
        import os

        # Save slice to temp file for DataHandler
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".csv") as tmp:
            data.to_csv(tmp, index=False)
            tmp_path = tmp.name

        try:
            data_handler = DataHandler(tmp_path, self.symbol)
            portfolio = Portfolio()
            strategy = self.strategy_cls(**params)
            engine = BacktestEngine(data_handler, strategy, portfolio)
            engine.run()

            equity_curve = create_equity_curve(portfolio.history)

            if equity_curve.empty:
                return {"Total Return": 0.0, "Sharpe Ratio": 0.0, "Max Drawdown": 0.0}

            initial = equity_curve["equity"].iloc[0]
            final = equity_curve["equity"].iloc[-1]
            total_return = (final - initial) / initial if initial else 0.0
            sharpe = calculate_sharpe_ratio(equity_curve)
            dd = calculate_drawdown(equity_curve)
            max_dd = dd.min() if not dd.empty else 0.0

            return {
                "Total Return": total_return,
                "Sharpe Ratio": sharpe,
                "Max Drawdown": max_dd,
            }
        finally:
            os.remove(tmp_path)

    def _optimize_on_in_sample(self, is_data: pd.DataFrame) -> Dict[str, Any]:
        """Finds the best parameters on the in-sample data."""
        import itertools

        keys = self.param_grid.keys()
        values = self.param_grid.values()
        combinations = [dict(zip(keys, v)) for v in itertools.product(*values)]

        best_params = None
        best_sharpe = -float("inf")

        for params in combinations:
            metrics = self._run_backtest_on_data(is_data, params)
            if metrics["Sharpe Ratio"] > best_sharpe:
                best_sharpe = metrics["Sharpe Ratio"]
                best_params = params

        return best_params if best_params else combinations[0]

    def run(self) -> pd.DataFrame:
        """
        Executes the walk-forward analysis.

        Returns:
            DataFrame with out-of-sample results for each window.
        """
        windows = self.generate_windows()
        results = []

        logger.info(f"Starting Walk-Forward Analysis with {len(windows)} windows...")

        for i, (is_data, oos_data) in enumerate(windows):
            # 1. Optimize on In-Sample
            best_params = self._optimize_on_in_sample(is_data)
            logger.info(f"Window {i+1}: Best IS params = {best_params}")

            # 2. Validate on Out-of-Sample
            oos_metrics = self._run_backtest_on_data(oos_data, best_params)

            # 3. Collect results
            result_row = best_params.copy()
            result_row["Window"] = i + 1
            result_row["OOS_Total_Return"] = oos_metrics["Total Return"]
            result_row["OOS_Sharpe_Ratio"] = oos_metrics["Sharpe Ratio"]
            result_row["OOS_Max_Drawdown"] = oos_metrics["Max Drawdown"]
            results.append(result_row)

        logger.info("Walk-Forward Analysis completed.")
        return pd.DataFrame(results)

    def get_recommended_params(self, results_df: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyzes WFA results and returns the most robust parameter combination.

        Uses a voting system: returns the parameters that appeared most frequently
        as the best in each window (mode). In case of tie, uses best average OOS Sharpe.

        Args:
            results_df: DataFrame returned by run()

        Returns:
            Dictionary of recommended parameters.
        """
        param_cols = [
            c
            for c in results_df.columns
            if c
            not in [
                "Window",
                "OOS_Total_Return",
                "OOS_Sharpe_Ratio",
                "OOS_Max_Drawdown",
            ]
        ]

        # Create a tuple key for each parameter combination
        results_df["param_key"] = results_df[param_cols].apply(tuple, axis=1)

        # Count frequency of each param combo
        param_counts = results_df["param_key"].value_counts()
        most_frequent = param_counts.index[0]

        # Build result dict
        recommended = dict(zip(param_cols, most_frequent))

        logger.info(f"Recommended params (most frequent across windows): {recommended}")
        return recommended

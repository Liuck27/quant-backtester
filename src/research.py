import pandas as pd
import itertools
from typing import Dict, List, Type, Any
from src.engine import BacktestEngine
from src.data_handler import DataHandler
from src.portfolio import Portfolio
from src.strategy import Strategy
from src.performance import create_equity_curve, calculate_sharpe_ratio, calculate_drawdown

class StrategyResearchRunner:
    """
    Orchestrates multiple backtests with varying parameters for research purposes.
    """
    def __init__(self, data_path: str, symbol: str, strategy_cls: Type[Strategy], param_grid: Dict[str, List[Any]]):
        """
        Args:
            data_path (str): Path to the CSV data file.
            symbol (str): Symbol ticker.
            strategy_cls (Type[Strategy]): The strategy class to instantiate.
            param_grid (Dict[str, List[Any]]): Dictionary mapping parameter names to lists of values.
        """
        self.data_path = data_path
        self.symbol = symbol
        self.strategy_cls = strategy_cls
        self.param_grid = param_grid

    def _generate_param_combinations(self) -> List[Dict[str, Any]]:
        """Generates all combinations of parameters from the grid."""
        keys = self.param_grid.keys()
        values = self.param_grid.values()
        combinations = [dict(zip(keys, v)) for v in itertools.product(*values)]
        return combinations

    def run(self) -> pd.DataFrame:
        """
        Runs the parameter sweep and returns a DataFrame of results.
        
        Returns:
            pd.DataFrame: A DataFrame where each row corresponds to a parameter combination
                          and includes performance metrics.
        """
        combinations = self._generate_param_combinations()
        results = []

        print(f"Starting research run: {len(combinations)} combinations to test.")

        for params in combinations:
            # 1. Setup Components for this run
            # Important: Create fresh instances for each run to avoid state leakage
            data_handler = DataHandler(self.data_path, self.symbol)
            portfolio = Portfolio() 
            strategy = self.strategy_cls(**params) # Instantiate strategy with specific params
            
            engine = BacktestEngine(
                data_handler=data_handler,
                strategy=strategy,
                portfolio=portfolio
            )

            # 2. Run Backtest
            engine.run()

            # 3. Calculate Performance
            equity_curve = create_equity_curve(portfolio.history)
            
            # Metrics
            total_return = 0.0
            sharpe_ratio = 0.0
            max_drawdown = 0.0

            if not equity_curve.empty:
                # Total Return
                initial_equity = equity_curve['equity'].iloc[0]
                final_equity = equity_curve['equity'].iloc[-1]
                total_return = (final_equity - initial_equity) / initial_equity

                # Sharpe Ratio
                sharpe_ratio = calculate_sharpe_ratio(equity_curve)

                # Max Drawdown
                drawdown_series = calculate_drawdown(equity_curve)
                max_drawdown = drawdown_series.min() # Drawdown is usually negative or 0

            # 4. Collect Result
            # Combine params and metrics into a single dictionary
            result_row = params.copy()
            result_row['Total Return'] = total_return
            result_row['Sharpe Ratio'] = sharpe_ratio
            result_row['Max Drawdown'] = max_drawdown
            
            results.append(result_row)

        print("Research run completed.")
        return pd.DataFrame(results)

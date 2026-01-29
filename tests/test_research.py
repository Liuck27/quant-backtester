import pytest
import tempfile
import os
import pandas as pd
from src.research import StrategyResearchRunner
from src.strategy import MovingAverageCrossStrategy, Strategy
from src.events import MarketEvent, SignalEvent
from typing import Optional

class TestStrategyResearch:
    
    def test_grid_generation(self):
        """Verify that parameter grid combinations are generated correctly."""
        param_grid = {
            "short_window": [5, 10],
            "long_window": [20, 30]
        }
        # Dummy inputs for init
        runner = StrategyResearchRunner("dummy.csv", "TEST", MovingAverageCrossStrategy, param_grid)
        
        combos = runner._generate_param_combinations()
        
        assert len(combos) == 4
        expected = [
            {"short_window": 5, "long_window": 20},
            {"short_window": 5, "long_window": 30},
            {"short_window": 10, "long_window": 20},
            {"short_window": 10, "long_window": 30},
        ]
        # Sort by short_window then long_window to compare safely, though order depends on itertools
        # itertools.product is deterministic order.
        assert combos == expected

    def test_end_to_end_sweep(self):
        """
        Runs a sweep on synthetic data and verifies the output DataFrame.
        """
        # 1. Setup Data
        csv_content = """Date,Close,Volume
2023-01-01,100.0,1000
2023-01-02,101.0,1000
2023-01-03,102.0,1000
2023-01-04,103.0,1000
2023-01-05,104.0,1000
2023-01-06,105.0,1000
2023-01-07,90.0,1000
2023-01-08,80.0,1000
"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=".csv") as tmp:
            tmp.write(csv_content)
            tmp_path = tmp.name
            
        try:
            # 2. Setup Runner
            param_grid = {
                "short_window": [2],
                "long_window": [3, 5] 
            }
            # Combinations: (2, 3), (2, 5)
            
            runner = StrategyResearchRunner(
                data_path=tmp_path,
                symbol="TEST_SYM",
                strategy_cls=MovingAverageCrossStrategy,
                param_grid=param_grid
            )
            
            # 3. Run
            df_results = runner.run()
            
            # 4. Verify Output Structure
            assert isinstance(df_results, pd.DataFrame)
            assert len(df_results) == 2
            
            expected_cols = ['short_window', 'long_window', 'Total Return', 'Sharpe Ratio', 'Max Drawdown']
            for col in expected_cols:
                assert col in df_results.columns
                
            # 5. Verify Content (Basic check)
            # Ensure different params are in rows
            assert df_results.iloc[0]['long_window'] == 3
            assert df_results.iloc[1]['long_window'] == 5
            
            # With short synthetic data, metrics might be 0 or small, but should be numeric type
            assert isinstance(df_results.iloc[0]['Total Return'], float)
            
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

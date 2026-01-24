import pytest
import tempfile
import os
import pandas as pd
from src.engine import BacktestEngine
from src.data_handler import DataHandler
from src.events import MarketEvent

class TestDataFeedIntegration:
    
    def test_end_to_end_feed(self):
        """
        Verifies that N rows in CSV result in N processed MarketEvents.
        """
        # 1. Setup minimal CSV
        csv_content = """Date,Close,Volume
2023-01-01,100.0,1000
2023-01-02,101.5,1500
2023-01-03,102.0,1200
"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=".csv") as tmp:
            tmp.write(csv_content)
            tmp_path = tmp.name
            
        try:
            # 2. Setup Components
            data_handler = DataHandler(tmp_path, "TEST_SYM")
            engine = BacktestEngine(data_handler=data_handler)
            
            # 3. Run
            engine.run()
            
            # 4. Verify Output (State Verification)
            assert len(engine.processed_events) == 3
            
            # Check content of events
            events = engine.processed_events
            assert isinstance(events[0], MarketEvent)
            assert events[0].symbol == "TEST_SYM"
            assert events[0].price == 100.0
            assert events[1].price == 101.5
            assert events[2].price == 102.0
            
        finally:
            os.remove(tmp_path)

    def test_missing_columns_error(self):
        """Test failure when CSV has missing columns."""
        csv_content = """Date,Open
2023-01-01,100.0
"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=".csv") as tmp:
            tmp.write(csv_content)
            tmp_path = tmp.name
            
        try:
            with pytest.raises(ValueError, match="CSV missing required columns"):
                DataHandler(tmp_path, "TEST_SYM")
        finally:
            os.remove(tmp_path)

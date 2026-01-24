import pandas as pd
from collections import deque
from datetime import datetime
from typing import Optional, List
from src.events import MarketEvent
from src.data_loader import CSVDataLoader

class DataHandler:
    """
    DataHandler manages the supply of historical data to the event loop.
    It reads from CSVDataLoader and provides a drip-feed mechanism.
    """
    def __init__(self, csv_path: str, symbol: str):
        """
        Args:
            csv_path (str): Path to the CSV file.
            symbol (str): The symbol ticker (e.g., "AAPL").
        """
        self.symbol = symbol
        self.loader = CSVDataLoader(csv_path)
        self.data_df = self._load_and_sort()
        self.data_iterator = self.data_df.iterrows()
        self.continue_backtest = True

    def _load_and_sort(self) -> pd.DataFrame:
        """Loads data, validates validation and ensures it is sorted by date."""
        df = self.loader.load_data()
        
        # Strict validation
        required_columns = ['Date', 'Close']
        if not all(col in df.columns for col in required_columns):
            raise ValueError(f"CSV missing required columns. Required: {required_columns}")

        df['Date'] = pd.to_datetime(df['Date'])
        df = df.sort_values('Date').reset_index(drop=True)
        return df

    def update_bars(self) -> Optional[MarketEvent]:
        """
        Returns the next bar as a MarketEvent.
        Sets continue_backtest to False if end of data is reached.
        """
        try:
            index, row = next(self.data_iterator)
            
            # Strict data extraction
            timestamp = row['Date']
            price = float(row['Close'])
            volume = int(row['Volume']) if 'Volume' in row else 0

            return MarketEvent(
                time=timestamp,
                symbol=self.symbol,
                price=price,
                volume=volume
            )
            
        except StopIteration:
            self.continue_backtest = False
            return None

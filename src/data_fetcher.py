import os
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from src.config import DATA_DIR
import logging

logger = logging.getLogger(__name__)


class DataFetcher:
    """
    Handles fetching data from Yahoo Finance and caching it locally in CSV format.
    """

    def __init__(self, cache_dir: str = DATA_DIR):
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)

    def get_data(
        self, symbol: str, start_date: str, end_date: str, force_download: bool = False
    ) -> str:
        """
        Retrieves data for a symbol. Checks cache first unless force_download is True.

        Args:
            symbol (str): Ticker symbol.
            start_date (str): Start date string (YYYY-MM-DD).
            end_date (str): End date string (YYYY-MM-DD).
            force_download (bool): If True, bypasses cache.

        Returns:
            str: Absolute path to the CSV file.
        """
        file_name = f"{symbol}_{start_date}_{end_date}.csv"
        file_path = os.path.join(self.cache_dir, file_name)

        if not force_download and os.path.exists(file_path):
            logger.info(f"Loading cached data for {symbol} from {file_path}")
            return file_path

        logger.info(f"Downloading data for {symbol} from {start_date} to {end_date}...")
        try:
            df = yf.download(symbol, start=start_date, end=end_date)

            if df.empty:
                raise ValueError(f"No data found for {symbol} in the given date range.")

            # Flatten MultiIndex columns if present (yfinance sometimes returns them)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            # Ensure 'Date' is a column if it's the index
            if df.index.name == "Date" or "Date" not in df.columns:
                df = df.reset_index()

            df.to_csv(file_path, index=False)
            logger.info(f"Saved data to {file_path}")
            return file_path

        except Exception as e:
            logger.error(f"Error downloading data: {e}")
            raise

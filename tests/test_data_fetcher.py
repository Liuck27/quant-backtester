import pytest
import os
from src.data_fetcher import DataFetcher
from src.config import DATA_DIR


def test_data_fetcher_initialization():
    fetcher = DataFetcher()
    assert os.path.exists(fetcher.cache_dir)


def test_data_fetcher_caching(tmp_path):
    # Use a temporary directory for testing
    fetcher = DataFetcher(cache_dir=str(tmp_path))
    symbol = "TEST_TICKER"
    start_date = "2023-01-01"
    end_date = "2023-01-02"

    file_name = f"{symbol}_{start_date}_{end_date}.csv"
    file_path = tmp_path / file_name

    # Manually create a cache file
    with open(file_path, "w") as f:
        f.write("Date,Close,Volume\n2023-01-01,100,1000")

    # Should load from cache
    path = fetcher.get_data(symbol, start_date, end_date)
    assert path == str(file_path)

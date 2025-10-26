import pandas as pd

def load_csv(path: str) -> pd.DataFrame:
    """Load an OHLCV CSV file into a pandas DataFrame with a DatetimeIndex.

    Args:
        path: Path to CSV file. Expected columns: ['Date', 'Open', 'High', 'Low', 'Close', 'Volume'].

    Returns:
        DataFrame: index = DatetimeIndex (converted from 'Date'), columns names lowercased.

    Raises:
        FileNotFoundError: if the file does not exist.
        ValueError: if expected columns are missing.
    """

    df = pd.read_csv(path)
    df["Date"] = pd.to_datetime(df["Date"])
    df.set_index("Date", inplace=True)

    df.columns = [col.lower() for col in df.columns]

    return df


print(load_csv("data/AAPL.csv"))
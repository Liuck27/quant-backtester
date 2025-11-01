import pandas as pd
import os


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

    base_path = os.path.dirname(__file__)
    file_path = os.path.join(base_path, "..", path)
    file_path = os.path.abspath(file_path)

    df = pd.read_csv(file_path)
    df["Date"] = pd.to_datetime(df["Date"])
    df.set_index("Date", inplace=True)
    df = df.sort_index(ascending=True)

    df.columns = [col.lower() for col in df.columns]
    df.columns = [col.strip() for col in df.columns]

    price_cols = ["close/last", "open", "high", "low"]
    for col in price_cols:
        df[col] = df[col].replace("[\$,]", "", regex=True).astype(float)
    df["volume"] = df["volume"].astype(int)

    df = df.rename(columns={"close/last": "close"})

    return df

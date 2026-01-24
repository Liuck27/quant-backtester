import pandas as pd
from pathlib import Path
from typing import Optional

class CSVDataLoader:
    """
    Handles loading of historical market data from CSV files.
    
    Attributes:
        file_path (Path): Path to the CSV file.
    """

    def __init__(self, file_path: str):
        """
        Initializes the loader with a file path.

        Args:
            file_path (str): Absolute or relative path to the CSV file.
        """
        self.file_path = Path(file_path)

    def load_data(self) -> pd.DataFrame:
        """
        Loads data from the CSV file into a pandas DataFrame.

        Returns:
            pd.DataFrame: Loaded data.

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: If the file is empty.
        """
        if not self.file_path.exists():
            raise FileNotFoundError(f"File not found: {self.file_path}")

        if not self.file_path.is_file():
             raise IsADirectoryError(f"Path is a directory, not a file: {self.file_path}")

        try:
            # Check for empty file before loading
            if self.file_path.stat().st_size == 0:
                raise ValueError(f"File is empty: {self.file_path}")

            df = pd.read_csv(self.file_path)
            
            if df.empty:
                 raise ValueError(f"File contains no data (empty DataFrame): {self.file_path}")

            return df
        
        except pd.errors.EmptyDataError:
             raise ValueError(f"File contains no data or header only: {self.file_path}")


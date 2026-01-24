import pytest
import pandas as pd
from pathlib import Path
from src.data_loader import CSVDataLoader
import tempfile
import os


def test_load_data_success():
    """Test successful loading of a valid CSV."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=".csv") as tmp:
        tmp.write("col1,col2\n1,2\n3,4")
        tmp_path = tmp.name
    
    try:
        loader = CSVDataLoader(tmp_path)
        df = loader.load_data()
        assert not df.empty
        assert list(df.columns) == ["col1", "col2"]
        assert len(df) == 2
    finally:
        os.remove(tmp_path)

def test_file_not_found():
    """Test that FileNotFoundError is raised for non-existent file."""
    loader = CSVDataLoader("non_existent_file.csv")
    with pytest.raises(FileNotFoundError):
        loader.load_data()

def test_empty_file():
    """Test that ValueError is raised for empty file."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=".csv") as tmp:
        pass # Create empty file
        tmp_path = tmp.name

    try:
        loader = CSVDataLoader(tmp_path)
        with pytest.raises(ValueError, match="File is empty"):
            loader.load_data()
    finally:
        os.remove(tmp_path)

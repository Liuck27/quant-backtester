import logging
import os

# Base Directories
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
LOG_DIR = os.path.join(BASE_DIR, "logs")

# Ensure directories exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

# Default Backtest Parameters
INITIAL_CAPITAL = 100000.0
COMMISSION_RATE = 0.001  # 0.1% per trade
DEFAULT_RISK_PER_TRADE = 0.02  # 2% of capital

# Logging Configuration
LOG_FILE = os.path.join(LOG_DIR, "backtest.log")
LOG_LEVEL = logging.INFO
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


def setup_logging():
    """Configures the global logging settings."""
    logging.basicConfig(
        level=LOG_LEVEL,
        format=LOG_FORMAT,
        handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()],
    )

# Quantitative Backtesting Engine

An event-driven backtesting engine designed for incremental development and clear separation of concerns.
Built as a demonstration of Quantitative Developer skills (Python).

## 🏗 Architecture

The system follows a strict **Event-Driven Architecture**, preferred in institutional trading systems for its realism (handling latencies, complex order types, and avoiding look-ahead bias).

### Core Components
1.  **Event Loop (`BacktestEngine`)**: The central nervous system. A FIFO queue consuming events sequentially.
2.  **Data Feed (`DataHandler`)**: Drip-feeds historical data (`MarketEvent`) to simulate a live market.
3.  **Strategy**: Receives `MarketEvent` and decides whether to generate a `SignalEvent`.
4.  **Portfolio**: Manages Cash & Holdings. Receives `SignalEvent` -> Generates `OrderEvent`. Updates state on `FillEvent`.
5.  **Performance**: Calculates Equity Curve, Sharpe Ratio, and Drawdowns (Mark-to-Market).

### Event Flow
```mermaid
graph LR
    Data(DataHandler) -->|MarketEvent| Engine
    Engine -->|MarketEvent| Strategy
    Strategy -->|SignalEvent| Engine
    Engine -->|SignalEvent| Portfolio
    Portfolio -->|OrderEvent| Engine
    Engine -->|OrderEvent| Execution((Exec Sim))
    Execution -->|FillEvent| Engine
    Engine -->|FillEvent| Portfolio
```

## 🚀 Getting Started

### Prerequisites
- Python 3.9+
- `pip`

### Installation
Clone the repository and install in editable mode:
```bash
pip install -e .
```

### Running the Demo
A comprehensive demo notebook is available to visualize the backtest results.
1.  Activate your environment.
2.  Open `notebook_demo.ipynb` in VS Code or Jupyter Lab.
3.  Select the **"Python (quant-backtester)"** kernel.
4.  Run All Cells.

### Running Tests
Unit tests use `pytest`:
```bash
pytest tests/
```

## 📊 Project Status
**Phase 1 (Python)**: ✅ Completed
- [x] Event Loop Skeleton
- [x] Data Ingestion (CSV)
- [x] Naive Strategy Implementation (Buy & Hold)
- [x] Portfolio Management (Cash/Holdings)
- [x] Performance Metrics (Sharpe, Drawdown)

**Phase 2 (C++)**: 🚧 Planned
- [ ] Migrate `Strategy` calculation to C++
- [ ] Bind using `pybind11` for high-performance backtesting.

## 🤝 Contribution
Designed for clean code readability and extensibility. 
Strict typing and `pytest` coverage required for new modules.

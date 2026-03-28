# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Setup & Build
```bash
# Install package in editable mode + dependencies
pip install -e .
```

### Running the Full Stack
```bash
# Docker (recommended — starts Frontend + API + PostgreSQL + Adminer)
docker-compose up -d --build

# Services:
#   Frontend:  http://localhost:5173
#   API:       http://localhost:8000
#   API Docs:  http://localhost:8000/docs
#   Adminer:   http://localhost:8080
```

### Running Locally (without Docker)
```bash
# Backend (requires a running PostgreSQL instance)
uvicorn src.api.main:app --reload

# Frontend (in a separate terminal)
cd frontend
npm install
npm run dev
```

### Tests
```bash
# Run all unit/integration tests
pytest tests/

# Run a single test file
pytest tests/test_engine.py

# End-to-end test (requires Docker stack running)
python tests/test_end_to_end.py
```

### Database Migrations
```bash
# Apply pending migrations
alembic upgrade head

# Create a new migration after model changes
alembic revision --autogenerate -m "description"
```

## Architecture

This is an **event-driven backtesting framework** where components communicate exclusively through a FIFO event queue inside `BacktestEngine`. The data flow is strictly one-directional:

```
DataHandler → MarketEvent → Strategy → SignalEvent → Portfolio → OrderEvent → Engine (execution sim) → FillEvent → Portfolio
```

### Core event loop ([src/engine.py](src/engine.py))
`BacktestEngine.run()` drives everything. On each iteration it either pulls the next `MarketEvent` from the `DataHandler` (when the queue is empty) or dispatches the front event to the appropriate handler. Slippage is applied inline during `OrderEvent` processing — there is no separate `ExecutionHandler` class.

### Event types ([src/events.py](src/events.py))
Four event types form the contract between components: `MarketEvent`, `SignalEvent`, `OrderEvent`, `FillEvent`. All components only pass these objects; they never call each other directly.

### Strategy layer ([src/strategy.py](src/strategy.py))
- `Strategy` ABC with a single `calculate_signals(event) -> Optional[SignalEvent]` method.
- `BuyAndHoldStrategy` and `MovingAverageCrossStrategy` are the built-in implementations.
- `MLSignalStrategy` in `src/ml_strategy.py` trains a scikit-learn classifier on OHLCV features.

### Portfolio ([src/portfolio.py](src/portfolio.py))
Manages cash and holdings. Converts `SignalEvent` → `OrderEvent` using risk-based position sizing (2% of equity per trade by default). Updates state on `FillEvent`. Records an equity snapshot on every `MarketEvent` into `portfolio.history` for downstream performance analysis.

### Performance & Walk-Forward ([src/performance.py](src/performance.py), [src/walk_forward.py](src/walk_forward.py))
`create_equity_curve`, `calculate_sharpe_ratio`, `calculate_drawdown`, and `calculate_total_return` operate on `portfolio.history`. `WalkForwardAnalyzer` in `src/walk_forward.py` splits data into rolling in-sample / out-of-sample windows, grid-searches parameters on the in-sample slice (optimising Sharpe ratio), then evaluates on the out-of-sample slice — not yet exposed as an API endpoint.

### REST API ([src/api/](src/api/))
FastAPI application at `src/api/main.py`. Backtests run asynchronously via `ThreadPoolExecutor` managed by `JobManager` in `src/api/jobs.py`. Job lifecycle: `PENDING → RUNNING → COMPLETED/FAILED`. Results are persisted to PostgreSQL immediately after completion inside `routes.py:save_results_to_db`. CORS origins are configurable via `CORS_ORIGINS` environment variable (defaults to `*` for local dev).

### Database ([src/db/](src/db/))
SQLAlchemy models: `BacktestRun`, `Trade`, `PerformanceResult` (one-to-many and one-to-one relationships). Connection string is read from the `DATABASE_URL` environment variable, defaulting to `postgresql://postgres:postgres@localhost:5432/quant_backtester`. Migrations are managed with Alembic (`alembic/`).

### Frontend ([frontend/](frontend/))
React 18 + Vite + Tailwind CSS single-page application with the "QuantVault" design system. Uses React Router for navigation between three pages:
- **Backtest Page** (`/`): Configuration form + live equity chart with SSE streaming + real-time logs.
- **History Page** (`/history`): Job listing with status filters, auto-refresh, and navigation to results.
- **Results Page** (`/results/:jobId`): Detailed metrics, equity growth curve, and trade log table.

Key frontend files:
- `frontend/src/api/client.js` — API client; base URL configurable via `VITE_API_URL` env var.
- `frontend/src/App.jsx` — Router + shared layout (Sidebar, TopBar).
- `frontend/src/pages/` — Page components for each route.
- `frontend/src/components/EquityChart.jsx` — Recharts-based equity chart with trade markers.

### Configuration ([src/config.py](src/config.py))
Central place for default constants: `INITIAL_CAPITAL`, `COMMISSION_RATE`, `SLIPPAGE_RATE`, `DEFAULT_RISK_PER_TRADE`. Import from here rather than hardcoding values in component files.

### Data flow for real data ([src/data_fetcher.py](src/data_fetcher.py), [src/data_handler.py](src/data_handler.py))
`DataFetcher` pulls OHLCV data from Yahoo Finance and caches it as CSV in `data/`. `DataHandler` reads the CSV bar-by-bar and emits `MarketEvent`s. `CSVDataLoader` in `src/data_loader.py` is the lower-level helper used by `WalkForwardAnalyzer`.

## Environment Variables

| Variable | Used By | Default | Description |
|---|---|---|---|
| `DATABASE_URL` | Backend | `postgresql://postgres:postgres@localhost:5432/quant_backtester` | PostgreSQL connection string |
| `CORS_ORIGINS` | Backend | `*` | Comma-separated allowed origins for CORS |
| `VITE_API_URL` | Frontend | `http://localhost:8000` | Backend API base URL |

## Deployment
- **Frontend**: Designed for Vercel deployment (static SPA build via `npm run build`).
- **Database**: Planned migration to Supabase (PostgreSQL-compatible).
- **Backend**: Containerized via Docker, deployable to Railway/Fly.io/Render.
- **Docker Compose**: Local dev convenience only — runs all 4 services (frontend, api, db, adminer).

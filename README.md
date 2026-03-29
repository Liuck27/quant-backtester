# Event-Driven Quantitative Backtesting Framework

A professional-grade algorithmic trading simulation engine built with Python. This framework demonstrates institutional-style architectures for backtesting, featuring realistic execution modeling, walk-forward validation, a scalable REST API, SSE-streamed live updates, and a modern React frontend.

---

## Architecture

The system follows a strict **Event-Driven Architecture**, ensuring high fidelity by simulating market latencies, handling complex order flows, and eliminating look-ahead bias.

```mermaid
graph LR
    Data(DataHandler) -->|MarketEvent| Engine
    Engine -->|MarketEvent| Strategy
    Strategy -->|SignalEvent| Engine
    Engine -->|SignalEvent| Portfolio
    Portfolio -->|OrderEvent| Engine
    Engine -->|OrderEvent| Execution((Exec Sim + Slippage))
    Execution -->|FillEvent| Engine
    Engine -->|FillEvent| Portfolio
```

### Core Components

- **`BacktestEngine`** (`src/engine.py`): Central event loop managing a FIFO queue of market, signal, order, and fill events. Slippage is applied inline during order processing — no separate execution handler.
- **`Strategy`** (`src/strategy.py`, `src/ml_strategy.py`): Pluggable strategy interface. Four implementations built-in (see below).
- **`Portfolio`** (`src/portfolio.py`): Real-time position tracking with risk-based sizing (2% equity per trade by default) and equity snapshot history.
- **`DataHandler`** (`src/data_handler.py`): Yahoo Finance integration via `yfinance` with local CSV caching for rapid iteration.
- **`Performance`** (`src/performance.py`): Sharpe ratio, max drawdown, total return, and equity curve construction from portfolio history.
- **`WalkForwardAnalyzer`** (`src/walk_forward.py`): Rolls in-sample/out-of-sample windows, grid-searches parameters on in-sample data (optimising Sharpe), then evaluates on out-of-sample.

### Strategies

| Strategy | Key Parameters | Notes |
|---|---|---|
| `buy_and_hold` | — | Baseline: buy once, hold forever |
| `moving_average_cross` | `short_window`, `long_window` | Golden/death cross signals |
| `rsi` | `rsi_period`, `oversold`, `overbought` | Mean-reversion on RSI extremes |
| `ml_signal` | `model_type`, `lookback_window`, `retrain_every`, `long_threshold` | Trains a scikit-learn classifier on OHLCV features; supports `random_forest`, `gradient_boosting`, `logistic` |

### REST API (`src/api/`)

FastAPI application. Backtests run asynchronously via `ThreadPoolExecutor` managed by `JobManager`. Job lifecycle: `PENDING → RUNNING → COMPLETED/FAILED`.

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/backtest/run` | Submit a backtest job |
| `GET` | `/backtest/{job_id}` | Poll job status |
| `GET` | `/results/{job_id}` | Retrieve completed results |
| `GET` | `/stream/{job_id}` | SSE live equity stream during execution |
| `POST` | `/research/run` | Submit a parameter sweep job |
| `GET` | `/research/{job_id}` | Get sweep results |
| `GET` | `/research/stream/{job_id}` | SSE live progress for sweep |
| `GET` | `/jobs` | List all jobs (session-scoped) |
| `GET` | `/strategies` | List available strategies and parameters |
| `GET` | `/health` | Health check with DB connectivity |

### Frontend (`frontend/`)

React 18 + Vite + Tailwind CSS SPA with the "QuantVault" design system.

| Page | Route | Description |
|---|---|---|
| Backtest | `/` | Configuration form + live equity chart via SSE |
| History | `/history` | Job listing with status filters and auto-refresh |
| Results | `/results/:jobId` | Metrics, equity curve, and full trade log |
| Research | `/research` | Parameter sweep configuration and heatmap results |
| About | `/about` | Framework overview and usage guide |

### Database (`src/db/`)

SQLAlchemy models: `BacktestRun`, `Trade`, `PerformanceResult`. Results are persisted to PostgreSQL immediately after job completion. Migrations managed with Alembic.

---

## Project Evolution

Built incrementally from a minimal event loop to a production-deployed system.

- **Phase 1 — Foundation**: Core event loop, FIFO queue, and market data ingestion.
- **Phase 2 — Strategy & Portfolio**: Stateful strategy support and equity curve tracking.
- **Phase 3 — Realism**: Slippage, commissions, risk-adjusted position sizing, walk-forward validation, and real data fetching via Yahoo Finance.
- **Phase 4 — Professional API**: FastAPI service with async job management, SSE streaming, and status tracking.
- **Phase 5 — Persistence**: PostgreSQL integration with SQLAlchemy and Alembic.
- **Phase 6 — Docker**: Containerized full-stack environment.
- **Phase 7 — Frontend**: React SPA with live backtest streaming, job history, and detailed results analysis.
- **Phase 8 — ML Strategies**: `MLSignalStrategy` with scikit-learn classifiers, rolling training windows, and anti-look-ahead guards.
- **Phase 9 — Research Tools**: Parameter sweep engine with SSE streaming and results heatmap.
- **Phase 10 — Deployment**: Live on Vercel (frontend) + Render (API) + Supabase (database).

---

## Getting Started

### Prerequisites
- Docker & Docker Compose
- Python 3.9+ (if running locally)
- Node.js 20+ (if running frontend locally)

### Docker (Recommended)

Starts all four services: Frontend, API, PostgreSQL, and Adminer.

```bash
docker-compose up -d --build
```

| Service | URL |
|---|---|
| Frontend | http://localhost:5173 |
| API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| Adminer | http://localhost:8080 |

### Local Development

```bash
# Backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e .
uvicorn src.api.main:app --reload

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

### Database Migrations

```bash
alembic upgrade head
```

---

## Testing

```bash
# Unit and integration tests
pytest tests/

# End-to-end test (requires Docker stack running)
python tests/test_end_to_end.py
```

---

## Environment Variables

| Variable | Service | Default | Description |
|---|---|---|---|
| `DATABASE_URL` | Backend | `postgresql://postgres:postgres@localhost:5432/quant_backtester` | PostgreSQL connection string |
| `CORS_ORIGINS` | Backend | `*` | Comma-separated allowed origins — set to your frontend URL in production |
| `VITE_API_URL` | Frontend | `http://localhost:8000` | Backend API base URL |

---

## Deployment

Live deployment at zero cost:

| Layer | Service | Notes |
|---|---|---|
| Frontend | [Vercel](https://vercel.com) Hobby tier | Auto-deploys from `main`; root directory set to `frontend/` |
| Backend | [Render](https://render.com) Free tier | Dockerized; auto-deploys from `main` |
| Database | [Supabase](https://supabase.com) Free tier | PostgreSQL; connect via Transaction Pooler (port 6543) to avoid IPv6 issues on Render |

---

## Technical Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11, FastAPI, uvicorn |
| Data | pandas, numpy, yfinance |
| ML | scikit-learn |
| Database | PostgreSQL 15, SQLAlchemy, Alembic, psycopg2 |
| Frontend | React 18, Vite, Tailwind CSS, Recharts, React Router |
| Streaming | Server-Sent Events (SSE) |
| Containerisation | Docker, Docker Compose |

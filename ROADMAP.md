# Project Roadmap

Goal: turn the backtesting engine into a portfolio piece that is technically impressive (ML strategies, observability) and visually compelling to a recruiter (live frontend), deployable at $0 cost.

---

## Phase 1 — ML/AI Strategies
*Resume signal: machine learning, feature engineering, scikit-learn/PyTorch*

### ✅ 1a. `MLSignalStrategy` (scikit-learn)
Trains a binary classifier on historical price features to predict next-bar direction. Generates LONG/EXIT signals based on predicted up-probability.

- **Features:** 1/5/10/20-day returns, 5/10-day rolling volatility, SMA(10)/SMA(20) ratio, RSI(14)
- **Model types:** `random_forest` (default), `gradient_boosting`, `logistic`
- **Anti-overfitting:** rolling training window, retrains every N bars, no look-ahead
- **Files:** [`src/ml_strategy.py`](src/ml_strategy.py), [`tests/test_ml_strategy.py`](tests/test_ml_strategy.py)
- **API:** `strategy: "ml_signal"` with params `model_type`, `lookback_window`, `retrain_every`, `long_threshold`, `exit_threshold`

### ⬜ 1b. `LSTMStrategy` (PyTorch)
Sequence model (LSTM) that takes the last N closing prices and predicts next-bar direction.

- **Files to create:** `src/lstm_strategy.py`
- **Dependency:** `torch` (CPU-only build)
- **Key detail:** save model weights to disk so each backtest doesn't retrain from scratch
- **API:** add `strategy: "lstm"` with params `lookback_window`, `hidden_size`, `epochs`

---

## Phase 2 — Monitoring
*Resume signal: observability, Prometheus, production engineering*

### ⬜ 2a. Prometheus metrics endpoint
- Add `prometheus-fastapi-instrumentator` to `src/api/main.py`
- Exposes `/metrics`: request latency, job queue depth, backtest duration histogram

### ⬜ 2b. Grafana dashboard via docker-compose
- Add `grafana` + `prometheus` services to `docker-compose.yml`
- Pre-provision dashboard: active jobs, backtest durations, API latency, strategy comparison
- Files to create: `monitoring/prometheus.yml`, `monitoring/grafana/dashboard.json`

### ⬜ 2c. Structured JSON logging
- Replace plain `logger.info(f"...")` with `python-json-logger`
- Each entry includes: `job_id`, `strategy`, `symbol`, `duration_ms`
- File to modify: all files that use `logger`

---

## Phase 3 — Live Frontend
*Resume signal: React, SSE/real-time, data visualization, full-stack*

### ⬜ 3a. Backend: Server-Sent Events (SSE) stream
- Add optional progress callback to `BacktestEngine` so it publishes each `FillEvent` and equity snapshot
- Add `/stream/{job_id}` SSE endpoint in `src/api/routes.py`
- SSE chosen over WebSockets: simpler, one-directional, no protocol upgrade needed

### ⬜ 3b. React frontend
- **Stack:** React + Recharts + TailwindCSS
- **Location:** `frontend/` in repo root
- **Views:**
  - Run form: symbol, date range, strategy selector, parameter sliders
  - Live view: equity curve updating bar-by-bar, trade markers (▲/▼) on chart, real-time metrics panel
  - Results view: final metrics, full trade table, equity curve

### ⬜ 3c. Docker integration
- Add `frontend` service to `docker-compose.yml` (nginx) or serve built static files from FastAPI `StaticFiles`

---

## Deployment (when ready)
- **Database:** swap to [Supabase](https://supabase.com) free tier — single `DATABASE_URL` env var change
- **API:** Render.com free tier (Docker, auto-deploy on push to `main`)
- **Frontend:** Render.com static site or Netlify (both free)
- **Total cost: $0**

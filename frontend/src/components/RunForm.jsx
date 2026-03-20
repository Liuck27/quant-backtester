import { useState } from 'react'
import { runBacktest } from '../api/client'

const MA_DEFAULTS = { short_window: 10, long_window: 50 }
const ML_DEFAULTS = {
  model_type: 'random_forest',
  lookback_window: 252,
  retrain_every: 20,
  long_threshold: 0.6,
  exit_threshold: 0.4,
}

function Field({ label, hint, children }) {
  return (
    <div>
      <label className="block text-dim font-mono text-[10px] uppercase tracking-widest mb-1">
        {label}
      </label>
      {children}
      {hint && <p className="text-dim text-[10px] mt-1">{hint}</p>}
    </div>
  )
}

const inputCls =
  'w-full bg-surface border border-border rounded px-3 py-2 font-mono text-sm text-bright ' +
  'placeholder:text-dim focus:outline-none focus:border-accent transition-colors'

const selectCls =
  'w-full bg-surface border border-border rounded px-3 py-2 font-mono text-sm text-bright ' +
  'focus:outline-none focus:border-accent transition-colors'

export default function RunForm({ onJobStarted }) {
  const [symbol, setSymbol] = useState('AAPL')
  const [startDate, setStartDate] = useState('2022-01-01')
  const [endDate, setEndDate] = useState('2024-01-01')
  const [strategy, setStrategy] = useState('ma_crossover')
  const [capital, setCapital] = useState(100000)
  const [maParams, setMaParams] = useState(MA_DEFAULTS)
  const [mlParams, setMlParams] = useState(ML_DEFAULTS)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      const params = strategy === 'ma_crossover'
        ? { short_window: Number(maParams.short_window), long_window: Number(maParams.long_window) }
        : {
            model_type: mlParams.model_type,
            lookback_window: Number(mlParams.lookback_window),
            retrain_every: Number(mlParams.retrain_every),
            long_threshold: Number(mlParams.long_threshold),
            exit_threshold: Number(mlParams.exit_threshold),
          }

      const res = await runBacktest({
        symbol: symbol.toUpperCase().trim(),
        start_date: startDate,
        end_date: endDate,
        strategy,
        parameters: params,
        initial_capital: Number(capital),
      })
      onJobStarted(res.job_id, { symbol: symbol.toUpperCase().trim(), strategy, initial_capital: Number(capital) })
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-xl mx-auto fade-in">
      {/* Header */}
      <div className="mb-8">
        <div className="font-mono text-[10px] text-dim uppercase tracking-widest mb-2">
          QUANT BACKTESTER / NEW RUN
        </div>
        <h1 className="text-bright text-2xl font-sans font-semibold">Configure Backtest</h1>
      </div>

      <form onSubmit={handleSubmit} className="space-y-5">
        {/* Symbol + Capital */}
        <div className="grid grid-cols-2 gap-4">
          <Field label="Symbol">
            <input
              className={inputCls}
              value={symbol}
              onChange={(e) => setSymbol(e.target.value)}
              placeholder="AAPL"
              required
            />
          </Field>
          <Field label="Initial Capital ($)">
            <input
              type="number"
              className={inputCls}
              value={capital}
              onChange={(e) => setCapital(e.target.value)}
              min={1000}
              step={1000}
              required
            />
          </Field>
        </div>

        {/* Date range */}
        <div className="grid grid-cols-2 gap-4">
          <Field label="Start Date">
            <input
              type="date"
              className={inputCls}
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              required
            />
          </Field>
          <Field label="End Date">
            <input
              type="date"
              className={inputCls}
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              required
            />
          </Field>
        </div>

        {/* Strategy */}
        <Field label="Strategy">
          <select
            className={selectCls}
            value={strategy}
            onChange={(e) => setStrategy(e.target.value)}
          >
            <option value="ma_crossover">Moving Average Crossover</option>
            <option value="ml_signal">ML Signal (scikit-learn)</option>
          </select>
        </Field>

        {/* Strategy params */}
        {strategy === 'ma_crossover' && (
          <div className="border border-border rounded p-4 space-y-4 bg-surface/50">
            <div className="text-dim font-mono text-[10px] uppercase tracking-widest">MA Parameters</div>
            <div className="grid grid-cols-2 gap-4">
              <Field label="Short Window" hint="Fast MA period">
                <input
                  type="number"
                  className={inputCls}
                  value={maParams.short_window}
                  onChange={(e) => setMaParams((p) => ({ ...p, short_window: e.target.value }))}
                  min={2} max={200}
                />
              </Field>
              <Field label="Long Window" hint="Slow MA period">
                <input
                  type="number"
                  className={inputCls}
                  value={maParams.long_window}
                  onChange={(e) => setMaParams((p) => ({ ...p, long_window: e.target.value }))}
                  min={5} max={500}
                />
              </Field>
            </div>
          </div>
        )}

        {strategy === 'ml_signal' && (
          <div className="border border-border rounded p-4 space-y-4 bg-surface/50">
            <div className="text-dim font-mono text-[10px] uppercase tracking-widest">ML Parameters</div>
            <Field label="Model Type">
              <select
                className={selectCls}
                value={mlParams.model_type}
                onChange={(e) => setMlParams((p) => ({ ...p, model_type: e.target.value }))}
              >
                <option value="random_forest">Random Forest</option>
                <option value="gradient_boosting">Gradient Boosting</option>
                <option value="logistic">Logistic Regression</option>
              </select>
            </Field>
            <div className="grid grid-cols-2 gap-4">
              <Field label="Lookback Window" hint="Training bars">
                <input
                  type="number"
                  className={inputCls}
                  value={mlParams.lookback_window}
                  onChange={(e) => setMlParams((p) => ({ ...p, lookback_window: e.target.value }))}
                  min={50} max={1000}
                />
              </Field>
              <Field label="Retrain Every N bars">
                <input
                  type="number"
                  className={inputCls}
                  value={mlParams.retrain_every}
                  onChange={(e) => setMlParams((p) => ({ ...p, retrain_every: e.target.value }))}
                  min={1} max={200}
                />
              </Field>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <Field label="Long Threshold" hint="Min P(up) to enter">
                <input
                  type="number"
                  className={inputCls}
                  value={mlParams.long_threshold}
                  onChange={(e) => setMlParams((p) => ({ ...p, long_threshold: e.target.value }))}
                  min={0.5} max={1} step={0.05}
                />
              </Field>
              <Field label="Exit Threshold" hint="P(up) to exit">
                <input
                  type="number"
                  className={inputCls}
                  value={mlParams.exit_threshold}
                  onChange={(e) => setMlParams((p) => ({ ...p, exit_threshold: e.target.value }))}
                  min={0} max={0.5} step={0.05}
                />
              </Field>
            </div>
          </div>
        )}

        {error && (
          <div className="border border-red/30 bg-red/5 rounded px-4 py-3 font-mono text-xs text-red">
            {error}
          </div>
        )}

        <button
          type="submit"
          disabled={loading}
          className="w-full bg-accent/10 border border-accent/40 hover:bg-accent/20 hover:border-accent
                     text-accent font-mono text-sm py-3 rounded transition-all disabled:opacity-40
                     disabled:cursor-not-allowed tracking-wider"
        >
          {loading ? 'SUBMITTING…' : 'RUN BACKTEST →'}
        </button>
      </form>
    </div>
  )
}

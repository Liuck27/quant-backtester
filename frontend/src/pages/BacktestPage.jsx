import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { runBacktest, openStream, getResults } from '../api/client'
import EquityChart from '../components/EquityChart'

const MA_DEFAULTS = { short_window: 10, long_window: 50 }
const ML_DEFAULTS = {
  model_type: 'random_forest',
  lookback_window: 252,
  retrain_every: 20,
  long_threshold: 0.6,
  exit_threshold: 0.4,
}

const inputCls =
  'w-full bg-surface-container-lowest border-none focus:ring-1 focus:ring-primary rounded-md py-2.5 px-4 text-sm font-medium text-on-surface'

export default function BacktestPage() {
  const navigate = useNavigate()

  // Form state
  const [symbol, setSymbol] = useState('AAPL')
  const [startDate, setStartDate] = useState('2022-01-01')
  const [endDate, setEndDate] = useState('2024-01-01')
  const [strategy, setStrategy] = useState('ma_crossover')
  const [capital, setCapital] = useState(100000)
  const [maParams, setMaParams] = useState(MA_DEFAULTS)
  const [mlParams, setMlParams] = useState(ML_DEFAULTS)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  // Live state
  const [jobId, setJobId] = useState(null)
  const [status, setStatus] = useState(null) // null | RUNNING | DONE | ERROR
  const [equityData, setEquityData] = useState([])
  const [fills, setFills] = useState([])
  const [liveEquity, setLiveEquity] = useState(null)
  const [barCount, setBarCount] = useState(0)
  const [logs, setLogs] = useState([])
  const equityRef = useRef([])
  const fillsRef = useRef([])

  // Metrics (shown in top cards once available)
  const [metrics, setMetrics] = useState(null)

  const addLog = (msg, color = 'text-white') => {
    const time = new Date().toLocaleTimeString('en-US', { hour12: false })
    setLogs((prev) => [...prev.slice(-50), { time, msg, color }])
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError(null)
    setLoading(true)
    setStatus(null)
    setEquityData([])
    setFills([])
    setLogs([])
    setMetrics(null)
    setBarCount(0)
    equityRef.current = []
    fillsRef.current = []

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

      addLog('Initializing backtest engine...', 'text-white')
      addLog(`Strategy "${strategy}" loaded with params ${JSON.stringify(params)}.`, 'text-white')

      const res = await runBacktest({
        symbol: symbol.toUpperCase().trim(),
        start_date: startDate,
        end_date: endDate,
        strategy,
        parameters: params,
        initial_capital: Number(capital),
      })

      setJobId(res.job_id)
      setLiveEquity(Number(capital))
      addLog(`Job ${res.job_id} created. Connecting to stream...`, 'text-white')
      startStream(res.job_id)
    } catch (err) {
      setError(err.message)
      addLog(`Error: ${err.message}`, 'text-tertiary')
    } finally {
      setLoading(false)
    }
  }

  const startStream = (id) => {
    const es = openStream(id)
    setStatus('RUNNING')
    addLog('Backtest started. Processing intervals.', 'text-secondary')

    es.onmessage = (e) => {
      let evt
      try { evt = JSON.parse(e.data) } catch { return }

      if (evt.type === 'equity') {
        const pt = { time: evt.time, equity: evt.equity, cash: evt.cash }
        equityRef.current = [...equityRef.current, pt]
        setEquityData(equityRef.current)
        setLiveEquity(evt.equity)
        setBarCount((n) => n + 1)
      } else if (evt.type === 'fill') {
        const f = { time: evt.time, direction: evt.direction }
        fillsRef.current = [...fillsRef.current, f]
        setFills(fillsRef.current)
        addLog(`Signal: ${evt.direction} generated`, evt.direction === 'BUY' ? 'text-secondary' : 'text-tertiary')
      } else if (evt.type === 'done') {
        setStatus('DONE')
        es.close()
        addLog('Backtest complete. Fetching results...', 'text-secondary')
        const snap = { equityData: equityRef.current, fills: fillsRef.current }
        getResults(id)
          .then((results) => {
            setMetrics(results.metrics)
            // Navigate to results page with state
            navigate(`/results/${id}`, { state: { results, snap } })
          })
          .catch(() => {
            setTimeout(() => {
              getResults(id)
                .then((results) => {
                  setMetrics(results.metrics)
                  navigate(`/results/${id}`, { state: { results, snap } })
                })
                .catch(console.error)
            }, 1000)
          })
      } else if (evt.type === 'error') {
        setError(evt.message)
        setStatus('ERROR')
        es.close()
        addLog(`Error: ${evt.message}`, 'text-tertiary')
      }
    }

    es.onerror = () => {
      setStatus('ERROR')
      setError('Connection lost')
      es.close()
      addLog('Connection lost', 'text-tertiary')
    }
  }

  const ret = liveEquity && capital
    ? (((liveEquity - Number(capital)) / Number(capital)) * 100).toFixed(2)
    : null

  const fmtMoney = (v) => v != null ? `$${Number(v).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : '—'
  const fmtPct = (v) => v != null ? `${v >= 0 ? '+' : ''}${Number(v).toFixed(2)}%` : '—'

  return (
    <div className="space-y-8 fade-in">
      {/* Metrics Row */}
      <section className="grid grid-cols-4 gap-6">
        <MetricCard
          label="Total Return"
          value={metrics ? fmtPct(metrics.total_return) : ret ? `${parseFloat(ret) >= 0 ? '+' : ''}${ret}%` : '—'}
          color={metrics ? (metrics.total_return >= 0 ? 'text-secondary' : 'text-tertiary') : ret ? (parseFloat(ret) >= 0 ? 'text-secondary' : 'text-tertiary') : 'text-white'}
          icon="trending_up"
        />
        <MetricCard
          label="Sharpe Ratio"
          value={metrics?.sharpe_ratio != null ? Number(metrics.sharpe_ratio).toFixed(2) : '—'}
          color="text-white"
          icon="equalizer"
        />
        <MetricCard
          label="Max Drawdown"
          value={metrics?.max_drawdown != null ? fmtPct(metrics.max_drawdown) : '—'}
          color={metrics?.max_drawdown != null ? 'text-tertiary' : 'text-white'}
          icon="south_east"
        />
        <MetricCard
          label="Live Equity"
          value={liveEquity ? fmtMoney(liveEquity) : fmtMoney(capital)}
          color="text-primary"
          icon="account_balance_wallet"
        />
      </section>

      {/* Main grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* LEFT: Configure */}
        <section className="lg:col-span-4 space-y-6">
          <div className="bg-surface-container-low p-6 rounded-xl">
            <h2 className="text-lg font-headline font-semibold text-white mb-6">Configure Backtest</h2>
            <form onSubmit={handleSubmit} className="space-y-5">
              <div className="space-y-1.5">
                <label className="text-[11px] font-bold text-outline uppercase tracking-wider">Symbol</label>
                <input className={inputCls} type="text" value={symbol} onChange={(e) => setSymbol(e.target.value)} required />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <label className="text-[11px] font-bold text-outline uppercase tracking-wider">Start Date</label>
                  <input className={inputCls + ' py-2 px-3 text-xs'} type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} required />
                </div>
                <div className="space-y-1.5">
                  <label className="text-[11px] font-bold text-outline uppercase tracking-wider">End Date</label>
                  <input className={inputCls + ' py-2 px-3 text-xs'} type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} required />
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="text-[11px] font-bold text-outline uppercase tracking-wider">Strategy</label>
                <select className={inputCls + ' appearance-none'} value={strategy} onChange={(e) => setStrategy(e.target.value)}>
                  <option value="ma_crossover">Moving Average Crossover</option>
                  <option value="ml_signal">ML Signal (scikit-learn)</option>
                </select>
              </div>

              {/* Parameters */}
              <div className="pt-4 border-t border-outline-variant/10">
                <h3 className="text-xs font-bold text-white mb-4">Parameters</h3>
                {strategy === 'ma_crossover' ? (
                  <div className="space-y-4">
                    <ParamRow label="Fast Period" value={maParams.short_window} onChange={(v) => setMaParams((p) => ({ ...p, short_window: v }))} />
                    <ParamRow label="Slow Period" value={maParams.long_window} onChange={(v) => setMaParams((p) => ({ ...p, long_window: v }))} />
                  </div>
                ) : (
                  <div className="space-y-4">
                    <div className="space-y-1.5">
                      <label className="text-xs text-outline">Model Type</label>
                      <select className={inputCls + ' appearance-none text-xs'} value={mlParams.model_type} onChange={(e) => setMlParams((p) => ({ ...p, model_type: e.target.value }))}>
                        <option value="random_forest">Random Forest</option>
                        <option value="gradient_boosting">Gradient Boosting</option>
                        <option value="logistic">Logistic Regression</option>
                      </select>
                    </div>
                    <ParamRow label="Lookback Window" value={mlParams.lookback_window} onChange={(v) => setMlParams((p) => ({ ...p, lookback_window: v }))} />
                    <ParamRow label="Retrain Every" value={mlParams.retrain_every} onChange={(v) => setMlParams((p) => ({ ...p, retrain_every: v }))} />
                    <ParamRow label="Long Threshold" value={mlParams.long_threshold} onChange={(v) => setMlParams((p) => ({ ...p, long_threshold: v }))} step={0.05} />
                    <ParamRow label="Exit Threshold" value={mlParams.exit_threshold} onChange={(v) => setMlParams((p) => ({ ...p, exit_threshold: v }))} step={0.05} />
                  </div>
                )}
                <ParamRow label="Initial Capital" value={capital} onChange={setCapital} className="mt-4" inputClassName="w-24" />
              </div>

              {error && (
                <div className="bg-error-container/20 text-error rounded-md px-4 py-3 text-xs">
                  {error}
                </div>
              )}

              <button
                type="submit"
                disabled={loading || status === 'RUNNING'}
                className="w-full bg-gradient-to-br from-primary to-primary-container text-on-primary-container font-bold py-3.5 rounded-md text-sm mt-4 shadow-lg shadow-primary/10 hover:shadow-primary/20 transition-all active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? 'Submitting...' : status === 'RUNNING' ? 'Running...' : 'Run Backtest'}
              </button>
            </form>
          </div>
        </section>

        {/* RIGHT: Live Performance */}
        <section className="lg:col-span-8 space-y-6">
          <div className="bg-surface-container-low rounded-xl overflow-hidden flex flex-col">
            <div className="p-6 border-b border-outline-variant/10 flex justify-between items-center">
              <h2 className="text-lg font-headline font-semibold text-white">Live Performance</h2>
              <div className="flex items-center gap-4">
                {status === 'RUNNING' && (
                  <div className="flex items-center gap-1.5">
                    <span className="w-2 h-2 rounded-full bg-secondary live-dot" />
                    <span className="text-[10px] text-outline uppercase font-bold tracking-widest">Live</span>
                  </div>
                )}
                <div className="flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-secondary" />
                  <span className="text-[10px] text-outline uppercase font-bold tracking-widest">Buy</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-tertiary" />
                  <span className="text-[10px] text-outline uppercase font-bold tracking-widest">Sell</span>
                </div>
              </div>
            </div>

            {/* Chart Area */}
            <div className="p-8 h-[400px] relative bg-background/50">
              <EquityChart equityData={equityData} fills={fills} live />
            </div>

            {/* Real-time Logs */}
            <div className="flex-1 bg-surface-container-lowest p-6 min-h-[200px] border-t border-outline-variant/10">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-[10px] font-bold text-outline uppercase tracking-widest">Real-time Logs</h3>
                <span className="text-[10px] tabular-nums text-primary/60">
                  {barCount > 0 ? `${barCount} bars processed` : 'IDLE'}
                </span>
              </div>
              <div className="space-y-2 font-body text-[11px] h-32 overflow-y-auto">
                {logs.length === 0 && (
                  <p className="text-outline">Configure and run a backtest to see logs here.</p>
                )}
                {logs.map((log, i) => (
                  <p key={i} className="text-outline flex gap-4">
                    <span className="text-primary/40">[{log.time}]</span>
                    <span className={log.color}>{log.msg}</span>
                  </p>
                ))}
              </div>
            </div>
          </div>
        </section>
      </div>
    </div>
  )
}

function MetricCard({ label, value, color = 'text-white', icon }) {
  return (
    <div className="bg-surface-container-low p-6 rounded-lg relative overflow-hidden group hover:bg-surface-container transition-colors">
      <div className="flex flex-col gap-1">
        <span className="text-[10px] font-bold text-outline uppercase tracking-widest">{label}</span>
        <span className={`text-3xl font-headline font-bold tabular-nums ${color}`}>{value}</span>
      </div>
      <div className="absolute -right-2 -bottom-2 opacity-5 group-hover:opacity-10 transition-opacity">
        <span className="material-symbols-outlined text-6xl">{icon}</span>
      </div>
    </div>
  )
}

function ParamRow({ label, value, onChange, step, className = '', inputClassName = 'w-16' }) {
  return (
    <div className={`flex items-center justify-between ${className}`}>
      <span className="text-xs text-outline">{label}</span>
      <input
        className={`bg-surface-container-lowest border-none ${inputClassName} py-1 px-2 rounded text-xs text-right tabular-nums text-on-surface`}
        type="number"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        step={step}
      />
    </div>
  )
}

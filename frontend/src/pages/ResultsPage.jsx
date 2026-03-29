import { useEffect, useState, useRef } from 'react'
import { useParams, useLocation, useNavigate } from 'react-router-dom'
import { getResults, openStream } from '../api/client'
import EquityChart from '../components/EquityChart'

const fmtDate = (s) => {
  if (!s) return '—'
  return new Date(s).toLocaleString('en-US', { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

const fmtPct = (v) => v != null ? `${v >= 0 ? '+' : ''}${Number(v).toFixed(1)}%` : '—'
const fmtMoney = (v) => v != null ? `$${Number(v).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : '—'

export default function ResultsPage() {
  const { jobId } = useParams()
  const location = useLocation()
  const navigate = useNavigate()

  const isLiveMode = location.state?.live === true

  // Static results (from API, used in historical mode or after live stream finishes)
  const [results, setResults] = useState(location.state?.results ?? null)
  const [loading, setLoading] = useState(!results && !isLiveMode)

  // Live mode state
  const [isStreaming, setIsStreaming] = useState(isLiveMode)
  const [chartMode, setChartMode] = useState('equity') // 'equity' | 'price'
  const [showMA, setShowMA] = useState(false)
  const [liveEquityData, setLiveEquityData] = useState([])
  const [liveFills, setLiveFills] = useState([])
  const [liveEquity, setLiveEquity] = useState(location.state?.initialCapital ?? null)
  const [barCount, setBarCount] = useState(0)
  const equityRef = useRef([])
  const fillsRef = useRef([])

  // Fetch results from API (historical mode)
  useEffect(() => {
    if (!results && !isLiveMode) {
      getResults(jobId)
        .then((r) => setResults(r))
        .catch(console.error)
        .finally(() => setLoading(false))
    }
  }, [jobId, results, isLiveMode])

  // Open SSE stream in live mode
  useEffect(() => {
    if (!isLiveMode) return

    const es = openStream(jobId)

    es.onmessage = (e) => {
      let evt
      try { evt = JSON.parse(e.data) } catch { return }

      if (evt.type === 'snapshot') {
        // Replay of accumulated history on (re)connect — replace state wholesale
        const pts = evt.equity_curve.map((e) => ({ time: e.time, equity: e.equity, cash: e.cash, price: e.price }))
        const fs  = evt.fills.map((f) => ({ time: f.time, direction: f.direction }))
        equityRef.current = pts
        fillsRef.current  = fs
        setLiveEquityData(pts)
        setLiveFills(fs)
        if (pts.length > 0) {
          setLiveEquity(pts[pts.length - 1].equity)
          setBarCount(pts.length)
        }
      } else if (evt.type === 'equity') {
        const pt = { time: evt.time, equity: evt.equity, cash: evt.cash, price: evt.price }
        equityRef.current = [...equityRef.current, pt]
        setLiveEquityData([...equityRef.current])
        setLiveEquity(evt.equity)
        setBarCount((n) => n + 1)
      } else if (evt.type === 'fill') {
        const f = { time: evt.time, direction: evt.direction }
        fillsRef.current = [...fillsRef.current, f]
        setLiveFills([...fillsRef.current])
      } else if (evt.type === 'done') {
        es.close()
        getResults(jobId)
          .then((r) => {
            setResults(r)
            setIsStreaming(false)
          })
          .catch(() => {
            setTimeout(() => {
              getResults(jobId)
                .then((r) => { setResults(r); setIsStreaming(false) })
                .catch(console.error)
            }, 1000)
          })
      } else if (evt.type === 'error') {
        es.close()
        setIsStreaming(false)
      }
    }

    es.onerror = () => {
      es.close()
      setIsStreaming(false)
    }

    return () => es.close()
  }, [jobId, isLiveMode])

  if (loading) {
    return <div className="text-center text-outline py-20 fade-in">Loading results...</div>
  }
  if (!results && !isLiveMode) {
    return <div className="text-center text-outline py-20 fade-in">Results not found</div>
  }

  // Resolve display values — live state takes precedence while streaming
  const symbol = results?.symbol ?? location.state?.symbol ?? '—'
  const strategy = results?.strategy ?? location.state?.strategy ?? '—'
  const created_at = results?.created_at
  const completed_at = results?.completed_at
  const metrics = results?.metrics
  const trades = results?.trades

  const equityData = isStreaming ? liveEquityData : (results?.equity_curve ?? [])
  const fills = isStreaming ? liveFills : (results?.fills ?? [])

  const isMACrossover = strategy === 'ma_crossover'
  const maParams = isMACrossover ? {
    shortWindow: results?.parameters?.short_window ?? 10,
    longWindow:  results?.parameters?.long_window  ?? 50,
  } : null

  const totalReturn = metrics?.total_return
  const sharpeRatio = metrics?.sharpe_ratio
  const maxDrawdown = metrics?.max_drawdown
  const totalTrades = metrics?.total_trades ?? trades?.length ?? 0
  const winRate = metrics?.win_rate ?? null

  // Live return estimate while streaming
  const liveReturn = isStreaming && liveEquity && location.state?.initialCapital
    ? ((liveEquity - location.state.initialCapital) / location.state.initialCapital) * 100
    : null

  return (
    <div className="fade-in space-y-8">
      {/* Header */}
      <section className="flex justify-between items-end">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <h2 className="text-3xl font-extrabold font-headline tracking-tight text-white">
              Backtest Results: <span className="text-primary">{symbol}</span> - <span className="opacity-80">{strategy?.replace('_', ' ')}</span>
            </h2>
            {isStreaming && (
              <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-secondary/10 border border-secondary/20">
                <span className="w-1.5 h-1.5 rounded-full bg-secondary live-dot" />
                <span className="text-[10px] font-bold text-secondary tracking-widest uppercase">Live</span>
              </div>
            )}
          </div>
          <div className="flex gap-6 text-sm font-medium text-outline">
            {created_at && (
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-xs">calendar_today</span>
                Created: {fmtDate(created_at)}
              </div>
            )}
            {completed_at && (
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-xs">check_circle</span>
                Completed: {fmtDate(completed_at)}
              </div>
            )}
            {isStreaming && (
              <div className="flex items-center gap-2 text-primary/60">
                <span className="material-symbols-outlined text-xs">bar_chart</span>
                {barCount} bars processed
              </div>
            )}
          </div>
        </div>
        <div className="flex gap-3">
          <button
            onClick={() => navigate('/history')}
            className="px-4 py-2 rounded-lg bg-surface-container-high text-on-surface font-semibold text-sm hover:bg-surface-variant transition-colors"
          >
            Back to History
          </button>
          <button
            onClick={() => navigate('/')}
            className="px-4 py-2 rounded-lg bg-surface-container-high text-on-surface font-semibold text-sm hover:bg-surface-variant transition-colors"
          >
            New Backtest
          </button>
        </div>
      </section>

      {/* Config strip — shown once results are available */}
      {results?.parameters && (
        <section className="flex flex-wrap gap-2">
          {Object.entries(results.parameters).map(([key, val]) => (
            <span
              key={key}
              className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-surface-container-high border border-outline-variant/15 text-xs"
            >
              <span className="text-outline font-medium">{key.replace(/_/g, ' ')}</span>
              <span className="text-white font-bold">{String(val)}</span>
            </span>
          ))}
          {results.initial_capital != null && (
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-surface-container-high border border-outline-variant/15 text-xs">
              <span className="text-outline font-medium">capital</span>
              <span className="text-white font-bold">{fmtMoney(results.initial_capital)}</span>
            </span>
          )}
        </section>
      )}

      {/* Metrics Row */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <SparkMetric
          label="Total Return"
          value={isStreaming ? fmtPct(liveReturn) : fmtPct(totalReturn)}
          color={
            isStreaming
              ? (liveReturn != null ? (liveReturn >= 0 ? 'text-secondary' : 'text-tertiary-container') : 'text-outline')
              : (totalReturn >= 0 ? 'text-secondary' : 'text-tertiary-container')
          }
          computing={isStreaming && liveReturn == null}
        />
        <SparkMetric
          label="Sharpe Ratio"
          value={sharpeRatio != null ? Number(sharpeRatio).toFixed(2) : '—'}
          color="text-primary"
          computing={isStreaming}
        />
        <div className="bg-surface-container-low p-6 rounded-xl flex flex-col">
          <p className="text-xs font-semibold text-outline uppercase tracking-wider mb-2">Win Rate</p>
          <span className={`text-3xl font-bold font-headline tabular-nums ${isStreaming ? 'text-outline' : 'text-white'}`}>
            {winRate != null ? `${winRate.toFixed(1)}%` : '—'}
          </span>
          {winRate != null && (
            <p className="text-[10px] text-outline mt-3">{totalTrades} trades total</p>
          )}
        </div>
        <SparkMetric
          label="Max Drawdown"
          value={fmtPct(maxDrawdown)}
          color={maxDrawdown != null ? 'text-tertiary-container' : 'text-outline'}
          computing={isStreaming}
        />
      </div>

      {/* Chart */}
      <section className="bg-surface-container-low rounded-xl p-8">
        <div className="flex justify-between items-start mb-6">
          <div>
            {/* Tab switcher */}
            <div className="flex gap-1 bg-surface-container-lowest rounded-lg p-1 mb-3 w-fit">
              {[
                { key: 'equity', label: 'Equity Curve' },
                { key: 'price',  label: 'Stock Price'  },
              ].map(({ key, label }) => (
                <button
                  key={key}
                  onClick={() => setChartMode(key)}
                  className={`px-4 py-1.5 rounded-md text-xs font-semibold transition-colors ${
                    chartMode === key
                      ? 'bg-surface-container-high text-white'
                      : 'text-outline hover:text-on-surface'
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
            <p className="text-sm text-outline">
              {isStreaming
                ? 'Computing in real-time...'
                : chartMode === 'equity'
                  ? 'Net portfolio value in USD over the simulation period.'
                  : `${symbol} closing price with strategy entry/exit markers.`}
            </p>
          </div>
          <div className="flex gap-4 items-center">
            {isMACrossover && chartMode === 'price' && (
              <button
                onClick={() => setShowMA((v) => !v)}
                className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider border transition-colors ${
                  showMA
                    ? 'bg-primary/10 text-primary border-primary/30'
                    : 'bg-surface-container-highest text-outline border-outline-variant/20 hover:text-on-surface'
                }`}
              >
                <span className="material-symbols-outlined text-xs">show_chart</span>
                MA Lines
              </button>
            )}
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-secondary" />
              <span className="text-[10px] font-semibold text-outline uppercase">Buy</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-tertiary-container" />
              <span className="text-[10px] font-semibold text-outline uppercase">Sell</span>
            </div>
            {showMA && maParams && chartMode === 'price' && (
              <>
                <div className="flex items-center gap-1.5">
                  <div className="w-5 h-[2px] rounded bg-[#ffd966]" />
                  <span className="text-[10px] font-semibold text-outline uppercase">MA {maParams.shortWindow}</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <div className="w-5 h-[2px] rounded bg-[#ff8c42]" />
                  <span className="text-[10px] font-semibold text-outline uppercase">MA {maParams.longWindow}</span>
                </div>
              </>
            )}
            <div className="flex items-center gap-2">
              <div className={`w-3 h-3 rounded-full ${chartMode === 'equity' ? 'bg-primary' : 'bg-[#c9a7ff]'}`} />
              <span className="text-xs font-semibold text-on-surface">{chartMode === 'equity' ? 'Equity' : 'Price'}</span>
            </div>
          </div>
        </div>
        <div className="h-[400px] w-full">
          {equityData.length > 0 ? (
            <EquityChart equityData={equityData} fills={fills} live={isStreaming} mode={chartMode} showMA={showMA} maParams={maParams} />
          ) : (
            <div className="flex items-center justify-center h-full text-outline text-sm">
              {isStreaming ? 'Waiting for first data point...' : 'Equity curve data not available'}
            </div>
          )}
        </div>
      </section>

      {/* Trade Log */}
      <section className="bg-surface-container-low rounded-xl overflow-hidden">
        <div className="p-6 border-b border-outline-variant/10 flex justify-between items-center">
          <h3 className="text-lg font-bold font-headline text-white">Detailed Trade Log</h3>
          <span className="text-xs text-outline font-medium">
            {isStreaming ? 'Computing...' : `${totalTrades} trades`}
          </span>
        </div>
        <table className="w-full text-left">
          <thead>
            <tr className="bg-surface-container-lowest/50 text-[10px] uppercase tracking-[0.15em] text-outline font-bold">
              <th className="px-6 py-4">Timestamp</th>
              <th className="px-6 py-4">Direction</th>
              <th className="px-6 py-4">Symbol</th>
              <th className="px-6 py-4 text-right">Quantity</th>
              <th className="px-6 py-4 text-right">Price (USD)</th>
              <th className="px-6 py-4 text-right">Commission</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-outline-variant/5">
            {isStreaming ? (
              <tr>
                <td colSpan={6} className="px-6 py-8 text-center text-outline text-sm">
                  <span className="material-symbols-outlined text-2xl mb-2 block opacity-30 animate-pulse">hourglass_top</span>
                  Trades will appear here when the backtest completes
                </td>
              </tr>
            ) : (!trades || trades.length === 0) ? (
              <tr>
                <td colSpan={6} className="px-6 py-8 text-center text-outline text-sm">No trades recorded</td>
              </tr>
            ) : (
              trades.map((t, i) => {
                const isBuy = t.direction === 'BUY'
                return (
                  <tr key={i} className="group hover:bg-surface-container-high transition-colors">
                    <td className="px-6 py-4 text-sm font-medium tabular-nums text-on-surface">{fmtDate(t.timestamp)}</td>
                    <td className="px-6 py-4">
                      <span className={`${isBuy ? 'bg-secondary/10 text-secondary border-secondary/20' : 'bg-tertiary-container/10 text-tertiary-container border-tertiary-container/20'} text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wide border`}>
                        {t.direction}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-sm font-semibold text-white">{t.symbol}</td>
                    <td className="px-6 py-4 text-sm text-right tabular-nums text-on-surface-variant">{t.quantity}</td>
                    <td className="px-6 py-4 text-sm text-right tabular-nums text-on-surface-variant">{fmtMoney(t.price)}</td>
                    <td className="px-6 py-4 text-sm text-right tabular-nums text-outline">{fmtMoney(t.commission ?? 0)}</td>
                  </tr>
                )
              })
            )}
          </tbody>
        </table>
      </section>
    </div>
  )
}

function SparkMetric({ label, value, color, computing = false }) {
  return (
    <div className="bg-surface-container-low p-6 rounded-xl flex flex-col">
      <p className="text-xs font-semibold text-outline uppercase tracking-wider mb-2">{label}</p>
      <span className={`text-3xl font-bold font-headline tabular-nums ${computing ? 'text-outline animate-pulse' : color}`}>
        {value}
      </span>
    </div>
  )
}

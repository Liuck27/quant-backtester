import EquityChart from './EquityChart'
import MetricsPanel from './MetricsPanel'
import TradeTable from './TradeTable'

const fmtDate = (s) => {
  if (!s) return '—'
  const d = new Date(s)
  return d.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' })
}

export default function ResultsView({ results, equityData, fills, onNewRun }) {
  const { metrics, trades, symbol, strategy, parameters, created_at, completed_at } = results

  const duration = created_at && completed_at
    ? `${((new Date(completed_at) - new Date(created_at)) / 1000).toFixed(1)}s`
    : null

  const paramStr = parameters
    ? Object.entries(parameters).map(([k, v]) => `${k}=${v}`).join(', ')
    : ''

  return (
    <div className="fade-in space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <div className="font-mono text-[10px] text-dim uppercase tracking-widest mb-1">
            BACKTEST COMPLETE
          </div>
          <h2 className="text-bright text-xl font-sans font-semibold">
            {symbol} · <span className="text-accent">{strategy?.replace('_', ' ')}</span>
          </h2>
          {paramStr && (
            <div className="font-mono text-xs text-dim mt-1">{paramStr}</div>
          )}
          {duration && (
            <div className="font-mono text-[10px] text-dim/60 mt-1">ran in {duration}</div>
          )}
        </div>
        <button
          onClick={onNewRun}
          className="border border-border text-dim hover:border-accent hover:text-accent
                     font-mono text-xs px-4 py-2 rounded transition-colors"
        >
          ← NEW RUN
        </button>
      </div>

      {/* Metrics */}
      <MetricsPanel
        metrics={metrics}
        initialCapital={results.initial_capital}
        finalEquity={metrics?.final_equity}
      />

      {/* Chart */}
      <div className="border border-border rounded bg-surface">
        <div className="px-4 pt-3 pb-1 font-mono text-[10px] text-dim uppercase tracking-widest border-b border-border">
          Equity Curve
          <span className="ml-2 text-accent/50">▲ BUY</span>
          <span className="ml-2 text-red/50">▼ SELL</span>
        </div>
        <div style={{ height: 280 }}>
          <EquityChart equityData={equityData} fills={fills} />
        </div>
      </div>

      {/* Trades */}
      <div className="border border-border rounded bg-surface">
        <div className="px-4 py-3 border-b border-border flex items-center justify-between">
          <span className="font-mono text-[10px] text-dim uppercase tracking-widest">
            Trade History
          </span>
          <span className="font-mono text-xs text-dim">
            {trades?.length ?? 0} trades
          </span>
        </div>
        <TradeTable trades={trades ?? []} />
      </div>
    </div>
  )
}

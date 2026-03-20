const fmt$ = (v) =>
  v >= 1_000_000
    ? `$${(v / 1_000_000).toFixed(3)}M`
    : `$${Number(v).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`

const fmtPct = (v, decimals = 2) =>
  v == null ? '—' : `${v >= 0 ? '+' : ''}${Number(v).toFixed(decimals)}%`

const fmtNum = (v, decimals = 2) =>
  v == null ? '—' : Number(v).toFixed(decimals)

function Metric({ label, value, color }) {
  return (
    <div className="border border-border rounded p-3 bg-surface">
      <div className="text-dim font-mono text-[10px] uppercase tracking-widest mb-1">{label}</div>
      <div className={`font-mono text-lg font-semibold ${color ?? 'text-bright'}`}>{value}</div>
    </div>
  )
}

export default function MetricsPanel({ metrics, initialCapital, finalEquity, live = false }) {
  if (!metrics && !finalEquity) {
    return (
      <div className="text-dim font-mono text-xs text-center py-4">
        {live ? 'Waiting for metrics…' : 'No metrics'}
      </div>
    )
  }

  const equity = finalEquity ?? metrics?.final_equity ?? initialCapital
  const ret = metrics?.total_return
  const sharpe = metrics?.sharpe_ratio
  const drawdown = metrics?.max_drawdown
  const trades = metrics?.total_trades

  const retColor = ret == null ? 'text-bright' : ret >= 0 ? 'text-accent' : 'text-red'
  const ddColor = drawdown == null ? 'text-bright' : drawdown <= -10 ? 'text-red' : 'text-amber'

  return (
    <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-2 xl:grid-cols-3">
      <Metric label="Equity" value={fmt$(equity)} />
      {ret != null && <Metric label="Total Return" value={fmtPct(ret)} color={retColor} />}
      {sharpe != null && (
        <Metric
          label="Sharpe Ratio"
          value={fmtNum(sharpe)}
          color={sharpe >= 1 ? 'text-accent' : sharpe >= 0 ? 'text-text' : 'text-red'}
        />
      )}
      {drawdown != null && <Metric label="Max Drawdown" value={fmtPct(drawdown)} color={ddColor} />}
      {trades != null && <Metric label="Total Trades" value={trades} />}
    </div>
  )
}

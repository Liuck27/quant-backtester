import { useEffect, useState } from 'react'
import { useParams, useLocation, useNavigate } from 'react-router-dom'
import { getResults } from '../api/client'
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

  const [results, setResults] = useState(location.state?.results ?? null)
  const [snap, setSnap] = useState(location.state?.snap ?? null)
  const [loading, setLoading] = useState(!results)

  useEffect(() => {
    if (!results) {
      getResults(jobId)
        .then((r) => setResults(r))
        .catch(console.error)
        .finally(() => setLoading(false))
    }
  }, [jobId, results])

  if (loading) {
    return <div className="text-center text-outline py-20 fade-in">Loading results...</div>
  }
  if (!results) {
    return <div className="text-center text-outline py-20 fade-in">Results not found</div>
  }

  const { metrics, trades, symbol, strategy, created_at, completed_at } = results
  const equityData = snap?.equityData ?? []
  const fills = snap?.fills ?? []

  const totalReturn = metrics?.total_return
  const sharpeRatio = metrics?.sharpe_ratio
  const maxDrawdown = metrics?.max_drawdown
  const totalTrades = metrics?.total_trades ?? trades?.length ?? 0
  const winCount = trades?.filter((t) => t.direction === 'SELL' && t.pnl > 0).length
  const lossCount = trades?.filter((t) => t.direction === 'SELL' && t.pnl <= 0).length
  const winRate = winCount != null && totalTrades > 0 ? ((winCount / Math.max(winCount + lossCount, 1)) * 100) : null

  return (
    <div className="fade-in space-y-8">
      {/* Header */}
      <section className="flex justify-between items-end">
        <div>
          <h2 className="text-3xl font-extrabold font-headline tracking-tight text-white mb-2">
            Backtest Results: <span className="text-primary">{symbol}</span> - <span className="opacity-80">{strategy?.replace('_', ' ')}</span>
          </h2>
          <div className="flex gap-6 text-sm font-medium text-outline">
            <div className="flex items-center gap-2">
              <span className="material-symbols-outlined text-xs">calendar_today</span>
              Created: {fmtDate(created_at)}
            </div>
            <div className="flex items-center gap-2">
              <span className="material-symbols-outlined text-xs">check_circle</span>
              Completed: {fmtDate(completed_at)}
            </div>
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

      {/* Metrics Row */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <SparkMetric label="Total Return" value={fmtPct(totalReturn)} color={totalReturn >= 0 ? 'text-secondary' : 'text-tertiary'} sparkColor={totalReturn >= 0 ? 'stroke-secondary' : 'stroke-tertiary'} />
        <SparkMetric label="Sharpe Ratio" value={sharpeRatio != null ? Number(sharpeRatio).toFixed(2) : '—'} color="text-primary" sparkColor="stroke-primary" />
        <div className="bg-surface-container-low p-6 rounded-xl flex flex-col">
          <p className="text-xs font-semibold text-outline uppercase tracking-wider mb-2">Win Rate</p>
          <span className="text-3xl font-bold font-headline tabular-nums text-white">
            {winRate != null ? `${winRate.toFixed(1)}%` : '—'}
          </span>
          {winCount != null && (
            <p className="text-[10px] text-outline mt-3">{winCount} Wins / {lossCount} Losses</p>
          )}
        </div>
        <SparkMetric label="Max Drawdown" value={fmtPct(maxDrawdown)} color="text-tertiary" sparkColor="stroke-tertiary" />
      </div>

      {/* Equity Chart */}
      <section className="bg-surface-container-low rounded-xl p-8">
        <div className="flex justify-between items-start mb-6">
          <div>
            <h3 className="text-xl font-bold font-headline text-white mb-1">Equity Growth Curve</h3>
            <p className="text-sm text-outline">Net portfolio value in USD over the simulation period.</p>
          </div>
          <div className="flex gap-4">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-primary" />
              <span className="text-xs font-semibold text-on-surface">Equity</span>
            </div>
          </div>
        </div>
        <div className="h-[400px] w-full">
          {equityData.length > 0 ? (
            <EquityChart equityData={equityData} fills={fills} />
          ) : (
            <div className="flex items-center justify-center h-full text-outline text-sm">
              Equity curve data not available (streamed data was not preserved)
            </div>
          )}
        </div>
      </section>

      {/* Trade Log */}
      <section className="bg-surface-container-low rounded-xl overflow-hidden">
        <div className="p-6 border-b border-outline-variant/10 flex justify-between items-center">
          <h3 className="text-lg font-bold font-headline text-white">Detailed Trade Log</h3>
          <span className="text-xs text-outline font-medium">{totalTrades} trades</span>
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
            {(!trades || trades.length === 0) ? (
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
                      <span className={`${isBuy ? 'bg-secondary/10 text-secondary border-secondary/20' : 'bg-tertiary/10 text-tertiary border-tertiary/20'} text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wide border`}>
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

function SparkMetric({ label, value, color, sparkColor }) {
  return (
    <div className="bg-surface-container-low p-6 rounded-xl flex flex-col">
      <p className="text-xs font-semibold text-outline uppercase tracking-wider mb-2">{label}</p>
      <span className={`text-3xl font-bold font-headline tabular-nums ${color}`}>{value}</span>
    </div>
  )
}

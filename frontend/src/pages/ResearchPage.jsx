import { useState, useRef, useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { runResearch, openResearchStream, getResearchJob, runBacktest } from '../api/client'
import EquityChart from '../components/EquityChart'

const inputCls =
  'w-full bg-surface-container-lowest border-none focus:ring-1 focus:ring-primary rounded-md py-2.5 px-4 text-sm font-medium text-on-surface'

// Map a normalized [0,1] value to a dark-theme hue: red→yellow→green
function sharpeColor(sharpe, min, max) {
  if (max === min) return 'hsl(60,55%,22%)'
  const t = Math.max(0, Math.min(1, (sharpe - min) / (max - min)))
  const hue = Math.round(t * 120)
  const lightness = Math.round(18 + t * 12)
  return `hsl(${hue},65%,${lightness}%)`
}

function parseWindows(str) {
  return str
    .split(',')
    .map((s) => parseInt(s.trim(), 10))
    .filter((n) => !isNaN(n) && n > 0)
}

export default function ResearchPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()

  // ---- Form state ----
  const [symbol, setSymbol]           = useState('AAPL')
  const [startDate, setStartDate]     = useState('2020-01-01')
  const [endDate, setEndDate]         = useState('2024-01-01')
  const [shortInput, setShortInput]   = useState('5, 10, 20, 30')
  const [longInput, setLongInput]     = useState('40, 50, 60, 80, 100, 120')
  const [capital, setCapital]         = useState(100000)
  const [advancedOpen, setAdvancedOpen] = useState(false)
  const [commissionRate, setCommissionRate] = useState(0.1)
  const [slippageRate, setSlippageRate]     = useState(0.05)
  const [riskPerTrade, setRiskPerTrade]     = useState(2.0)

  // ---- Run state ----
  const [phase, setPhase]           = useState('idle') // 'idle' | 'running' | 'done' | 'error'
  const [progress, setProgress]     = useState({ done: 0, total: 0 })
  const [results, setResults]       = useState([])   // [{short_window, long_window, sharpe_ratio, total_return, max_drawdown, trade_count}]
  const [bestEquity, setBestEquity] = useState([])
  const [bestFills, setBestFills]   = useState([])
  const [errorMsg, setErrorMsg]     = useState(null)
  const [runningBest, setRunningBest] = useState(false)
  const resultsRef = useRef([])

  // Load a completed job from DB when navigated here with ?job=<id>
  useEffect(() => {
    const jobId = searchParams.get('job')
    if (!jobId) return
    getResearchJob(jobId)
      .then((data) => {
        if (data.status === 'completed') {
          setResults(data.results ?? [])
          resultsRef.current = data.results ?? []
          setBestEquity(data.best_equity_curve ?? [])
          setBestFills(data.best_fills ?? [])
          setPhase('done')
          const n = (data.results ?? []).length
          setProgress({ done: n, total: n })
        }
      })
      .catch((err) => console.error('Failed to load research job:', err))
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // ---- Sorted table & selected row ----
  const [sortKey, setSortKey]       = useState('sharpe_ratio')
  const [sortDir, setSortDir]       = useState('desc')
  const [selectedRow, setSelectedRow] = useState(null)

  const shortWindows = parseWindows(shortInput)
  const longWindows  = parseWindows(longInput)
  const validCombos  = shortWindows.filter((sw) => longWindows.some((lw) => lw > sw)).length *
                       longWindows.filter((lw) => shortWindows.some((sw) => sw < lw)).length
  // More accurate count
  const comboCount = shortWindows.reduce((acc, sw) => acc + longWindows.filter((lw) => lw > sw).length, 0)

  // ---- Heatmap lookup ----
  const heatmapLookup = results.reduce((acc, r) => {
    acc[`${r.short_window}_${r.long_window}`] = r
    return acc
  }, {})

  const allSharpes = results.map((r) => r.sharpe_ratio)
  const minSharpe  = allSharpes.length ? Math.min(...allSharpes) : 0
  const maxSharpe  = allSharpes.length ? Math.max(...allSharpes) : 1

  const best = results.length
    ? results.reduce((a, b) => (a.sharpe_ratio > b.sharpe_ratio ? a : b))
    : null

  const sortedResults = [...results].sort((a, b) => {
    const dir = sortDir === 'desc' ? -1 : 1
    return (a[sortKey] - b[sortKey]) * dir
  })

  const handleSort = (key) => {
    if (sortKey === key) setSortDir((d) => (d === 'desc' ? 'asc' : 'desc'))
    else { setSortKey(key); setSortDir('desc') }
  }

  const handleRunBestBacktest = async () => {
    if (!best || runningBest) return
    setRunningBest(true)
    try {
      const res = await runBacktest({
        symbol: symbol.toUpperCase().trim(),
        start_date: startDate,
        end_date: endDate,
        strategy: 'ma_crossover',
        parameters: { short_window: best.short_window, long_window: best.long_window },
        initial_capital: Number(capital),
        commission_rate: Number(commissionRate) / 100,
        slippage_rate: Number(slippageRate) / 100,
        risk_per_trade: Number(riskPerTrade) / 100,
      })
      window.scrollTo({ top: 0, behavior: 'instant' })
      navigate(`/results/${res.job_id}`, {
        state: {
          live: true,
          symbol: symbol.toUpperCase().trim(),
          strategy: 'ma_crossover',
          initialCapital: Number(capital),
        },
      })
    } catch (err) {
      setErrorMsg(err.message)
      setRunningBest(false)
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setErrorMsg(null)
    setResults([])
    setBestEquity([])
    setBestFills([])
    setProgress({ done: 0, total: 0 })
    setSelectedRow(null)
    resultsRef.current = []
    setPhase('running')

    try {
      const { job_id } = await runResearch({
        symbol: symbol.toUpperCase().trim(),
        start_date: startDate,
        end_date: endDate,
        short_windows: shortWindows,
        long_windows: longWindows,
        initial_capital: Number(capital),
        commission_rate: Number(commissionRate) / 100,
        slippage_rate: Number(slippageRate) / 100,
        risk_per_trade: Number(riskPerTrade) / 100,
      })

      const es = openResearchStream(job_id)

      es.onmessage = (e) => {
        let evt
        try { evt = JSON.parse(e.data) } catch { return }

        if (evt.type === 'start') {
          setProgress({ done: 0, total: evt.total })
        } else if (evt.type === 'snapshot') {
          resultsRef.current = evt.results
          setResults([...evt.results])
          setProgress({ done: evt.done, total: evt.total })
        } else if (evt.type === 'progress') {
          resultsRef.current = [...resultsRef.current, evt.result]
          setResults([...resultsRef.current])
          setProgress({ done: evt.done, total: evt.total })
        } else if (evt.type === 'done') {
          setBestEquity(evt.best_equity_curve ?? [])
          setBestFills(evt.best_fills ?? [])
          setPhase('done')
          es.close()
        } else if (evt.type === 'error') {
          setErrorMsg(evt.message)
          setPhase('error')
          es.close()
        }
      }

      es.onerror = () => {
        setErrorMsg('Connection lost. The sweep may still be running — refresh to check.')
        setPhase('error')
        es.close()
      }
    } catch (err) {
      setErrorMsg(err.message)
      setPhase('error')
    }
  }

  const pct = progress.total > 0 ? (progress.done / progress.total) * 100 : 0

  const handleNewSweep = () => {
    setPhase('idle')
    setResults([])
    setBestEquity([])
    setBestFills([])
    setProgress({ done: 0, total: 0 })
    setSelectedRow(null)
    setErrorMsg(null)
    resultsRef.current = []
  }

  return (
    <div className="fade-in space-y-8">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-2xl font-extrabold font-headline tracking-tight text-white mb-1">
            Parameter Research
          </h2>
          <p className="text-sm text-outline">
            Sweep MA crossover parameters and visualize performance across the entire parameter space.
          </p>
        </div>
        {phase !== 'idle' && (
          <button
            onClick={handleNewSweep}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-surface-container-high text-on-surface text-sm font-semibold hover:bg-surface-variant transition-colors"
          >
            <span className="material-symbols-outlined text-sm">tune</span>
            New Sweep
          </button>
        )}
      </div>

      {/* Active run summary chip */}
      {phase !== 'idle' && (
        <div className="flex items-center gap-3 text-xs text-outline">
          <span className="font-bold text-white">{symbol.toUpperCase()}</span>
          <span>·</span>
          <span>{startDate} → {endDate}</span>
          <span>·</span>
          <span>Fast: [{shortInput}]</span>
          <span>·</span>
          <span>Slow: [{longInput}]</span>
        </div>
      )}

      <div className={phase === 'idle' ? 'grid grid-cols-1 lg:grid-cols-[380px_1fr] gap-8 items-start' : ''}>
        {/* ---- Config form (idle only) ---- */}
        {phase === 'idle' && <div className="bg-surface-container-low p-6 rounded-xl">
          <h3 className="text-xs font-bold text-outline uppercase tracking-wider mb-5">Configuration</h3>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-1.5">
              <label className="text-[11px] font-bold text-outline uppercase tracking-wider">Symbol</label>
              <input className={inputCls} type="text" value={symbol} onChange={(e) => setSymbol(e.target.value)} required />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <label className="text-[11px] font-bold text-outline uppercase tracking-wider">Start</label>
                <input className={inputCls + ' py-2 px-3 text-xs'} type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} required />
              </div>
              <div className="space-y-1.5">
                <label className="text-[11px] font-bold text-outline uppercase tracking-wider">End</label>
                <input className={inputCls + ' py-2 px-3 text-xs'} type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} required />
              </div>
            </div>

            <div className="pt-3 border-t border-outline-variant/10 space-y-4">
              <h4 className="text-xs font-bold text-white">Parameter Grid</h4>

              <div className="space-y-1.5">
                <label className="text-[11px] font-bold text-outline uppercase tracking-wider">
                  Fast Periods <span className="normal-case font-normal">(comma-separated)</span>
                </label>
                <input
                  className={inputCls}
                  type="text"
                  value={shortInput}
                  onChange={(e) => setShortInput(e.target.value)}
                  placeholder="5, 10, 20, 30"
                  required
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-[11px] font-bold text-outline uppercase tracking-wider">
                  Slow Periods <span className="normal-case font-normal">(comma-separated)</span>
                </label>
                <input
                  className={inputCls}
                  type="text"
                  value={longInput}
                  onChange={(e) => setLongInput(e.target.value)}
                  placeholder="40, 50, 60, 80, 100, 120"
                  required
                />
              </div>

              <div className="flex items-center justify-between text-xs text-outline">
                <span>Valid combinations</span>
                <span className="font-bold text-primary tabular-nums">{comboCount}</span>
              </div>
            </div>

            <div className="space-y-1.5">
              <div className="flex items-center justify-between text-xs text-outline mb-1">
                <span className="font-bold">Initial Capital</span>
                <input
                  className="bg-surface-container-lowest border-none w-28 py-1 px-2 rounded text-xs text-right tabular-nums text-on-surface"
                  type="number"
                  value={capital}
                  onChange={(e) => setCapital(e.target.value)}
                />
              </div>
            </div>

            {/* Advanced */}
            <div className="pt-3 border-t border-outline-variant/10">
              <button
                type="button"
                onClick={() => setAdvancedOpen((v) => !v)}
                className="flex items-center justify-between w-full text-xs font-bold text-outline hover:text-on-surface transition-colors"
              >
                <span className="uppercase tracking-wider">Advanced</span>
                <span className="material-symbols-outlined text-base">{advancedOpen ? 'expand_less' : 'expand_more'}</span>
              </button>
              {advancedOpen && (
                <div className="mt-4 space-y-3">
                  {[
                    { label: 'Commission %', val: commissionRate, set: setCommissionRate, step: 0.01 },
                    { label: 'Slippage %',   val: slippageRate,   set: setSlippageRate,   step: 0.01 },
                    { label: 'Risk/Trade %', val: riskPerTrade,   set: setRiskPerTrade,   step: 0.5  },
                  ].map(({ label, val, set, step }) => (
                    <div key={label} className="flex items-center justify-between">
                      <span className="text-xs text-outline">{label}</span>
                      <input
                        className="bg-surface-container-lowest border-none w-20 py-1 px-2 rounded text-xs text-right tabular-nums text-on-surface"
                        type="number" value={val} onChange={(e) => set(e.target.value)} step={step}
                      />
                    </div>
                  ))}
                </div>
              )}
            </div>

            {(phase === 'idle' || phase === 'error') && errorMsg && (
              <div className="bg-error-container/20 text-error rounded-md px-4 py-3 text-xs">{errorMsg}</div>
            )}

            <button
              type="submit"
              disabled={phase === 'running' || comboCount === 0}
              className="w-full bg-gradient-to-br from-primary to-primary-container text-on-primary-container font-bold py-3.5 rounded-md text-sm mt-2 shadow-lg shadow-primary/10 hover:shadow-primary/20 transition-all active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {phase === 'running' ? `Running… (${progress.done}/${progress.total})` : 'Run Parameter Sweep'}
            </button>
          </form>
        </div>}

        {/* ---- Right panel ---- */}
        <div className="space-y-6 min-w-0">
          {/* Progress bar */}
          {(phase === 'running' || phase === 'done') && (
            <div className="bg-surface-container-low rounded-xl p-5">
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs font-bold text-outline uppercase tracking-wider">Sweep Progress</span>
                <span className="text-xs font-bold tabular-nums text-primary">
                  {progress.done} / {progress.total}
                </span>
              </div>
              <div className="h-2 bg-surface-container-lowest rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-primary to-secondary rounded-full transition-all duration-300"
                  style={{ width: `${pct}%` }}
                />
              </div>
              {phase === 'done' && (
                <p className="text-xs text-secondary mt-2 font-semibold">
                  Sweep complete — {results.length} combinations evaluated
                </p>
              )}
            </div>
          )}

          {/* Heatmap */}
          {results.length > 0 && (
            <div className="bg-surface-container-low rounded-xl p-6 overflow-x-auto">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-xs font-bold text-outline uppercase tracking-wider">Sharpe Ratio Heatmap</h3>
                <div className="flex items-center gap-3 text-[10px] text-outline">
                  <span className="flex items-center gap-1.5">
                    <span className="w-3 h-3 rounded-sm inline-block" style={{ background: 'hsl(0,65%,22%)' }} />
                    Low
                  </span>
                  <span className="flex items-center gap-1.5">
                    <span className="w-3 h-3 rounded-sm inline-block" style={{ background: 'hsl(60,65%,28%)' }} />
                    Mid
                  </span>
                  <span className="flex items-center gap-1.5">
                    <span className="w-3 h-3 rounded-sm inline-block" style={{ background: 'hsl(120,65%,30%)' }} />
                    High
                  </span>
                </div>
              </div>

              <HeatmapGrid
                shortWindows={shortWindows}
                longWindows={longWindows}
                lookup={heatmapLookup}
                minSharpe={minSharpe}
                maxSharpe={maxSharpe}
                best={best}
              />
            </div>
          )}

          {/* Results table */}
          {results.length > 0 && (
            <div className="bg-surface-container-low rounded-xl overflow-hidden">
              <div className="px-6 py-4 border-b border-outline-variant/10 flex items-center justify-between">
                <h3 className="text-xs font-bold text-outline uppercase tracking-wider">All Results</h3>
                <span className="text-xs text-outline">{results.length} combinations</span>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-left">
                  <thead>
                    <tr className="bg-surface-container-lowest/50 text-[10px] uppercase tracking-[0.12em] text-outline font-bold">
                      {[
                        { key: 'short_window', label: 'Fast' },
                        { key: 'long_window',  label: 'Slow' },
                        { key: 'sharpe_ratio', label: 'Sharpe' },
                        { key: 'total_return', label: 'Return' },
                        { key: 'max_drawdown', label: 'Max DD' },
                        { key: 'trade_count',  label: 'Trades' },
                      ].map(({ key, label }) => (
                        <th
                          key={key}
                          className="px-4 py-3 text-right first:text-left cursor-pointer hover:text-on-surface select-none"
                          onClick={() => handleSort(key)}
                        >
                          {label} {sortKey === key ? (sortDir === 'desc' ? '↓' : '↑') : ''}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-outline-variant/5">
                    {sortedResults.slice(0, 10).map((r, i) => {
                      const isBest = best && r.short_window === best.short_window && r.long_window === best.long_window
                      return (
                        <tr
                          key={i}
                          onClick={() => setSelectedRow(r)}
                          className={`transition-colors cursor-pointer ${isBest ? 'bg-primary/5' : 'hover:bg-surface-container-high'}`}
                        >
                          <td className="px-4 py-3 text-sm font-semibold text-on-surface">{r.short_window}</td>
                          <td className="px-4 py-3 text-sm text-right tabular-nums text-on-surface-variant">{r.long_window}</td>
                          <td className={`px-4 py-3 text-sm text-right tabular-nums font-bold ${r.sharpe_ratio >= 0 ? 'text-secondary' : 'text-tertiary-container'}`}>
                            {r.sharpe_ratio.toFixed(3)}
                            {isBest && <span className="ml-1.5 text-[9px] font-bold text-primary uppercase tracking-wider">best</span>}
                          </td>
                          <td className={`px-4 py-3 text-sm text-right tabular-nums ${r.total_return >= 0 ? 'text-secondary' : 'text-tertiary-container'}`}>
                            {r.total_return >= 0 ? '+' : ''}{r.total_return.toFixed(1)}%
                          </td>
                          <td className="px-4 py-3 text-sm text-right tabular-nums text-tertiary-container">
                            {r.max_drawdown.toFixed(1)}%
                          </td>
                          <td className="px-4 py-3 text-sm text-right tabular-nums text-outline">{r.trade_count}</td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
                {sortedResults.length > 10 && (
                  <p className="text-center text-xs text-outline py-3">
                    Showing top 10 of {sortedResults.length} results
                  </p>
                )}
              </div>
            </div>
          )}

          {/* Best strategy equity curve */}
          {phase === 'done' && bestEquity.length > 0 && (
            <div className="bg-surface-container-low rounded-xl p-6">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h3 className="text-xs font-bold text-outline uppercase tracking-wider mb-1">Best Strategy Equity Curve</h3>
                  {best && (
                    <p className="text-sm text-on-surface-variant">
                      Fast={best.short_window} / Slow={best.long_window} — Sharpe{' '}
                      <span className="text-secondary font-bold">{best.sharpe_ratio.toFixed(3)}</span>
                    </p>
                  )}
                </div>
                {best && (
                  <button
                    onClick={handleRunBestBacktest}
                    disabled={runningBest}
                    className="px-3 py-1.5 rounded-lg bg-primary/10 border border-primary/20 text-primary text-xs font-bold hover:bg-primary/20 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {runningBest ? 'Starting…' : 'Run as Backtest →'}
                  </button>
                )}
              </div>
              <div className="h-[300px] w-full">
                <EquityChart equityData={bestEquity} fills={bestFills} live={false} mode="equity" />
              </div>
            </div>
          )}

          {/* Empty state */}
          {phase === 'idle' && (
            <div className="bg-surface-container-low rounded-xl p-12 flex flex-col items-center justify-center text-center">
              <span className="material-symbols-outlined text-5xl text-outline/30 mb-4">grid_view</span>
              <p className="text-outline text-sm font-medium">Configure your parameter grid and run the sweep</p>
              <p className="text-outline/60 text-xs mt-1">Results and heatmap will appear here</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}


// ---- Heatmap grid component ----

function HeatmapGrid({ shortWindows, longWindows, lookup, minSharpe, maxSharpe, best }) {
  const sortedShort = [...shortWindows].sort((a, b) => a - b)
  const sortedLong  = [...longWindows].sort((a, b) => a - b)

  return (
    <div className="overflow-x-auto">
      <table className="border-separate border-spacing-1 mx-auto">
        <thead>
          <tr>
            {/* top-left corner: axis labels */}
            <td className="text-[10px] text-outline text-right pr-2 pb-1 align-bottom">
              <span className="block">slow →</span>
              <span className="block">fast ↓</span>
            </td>
            {sortedLong.map((lw) => (
              <td key={lw} className="text-[10px] font-bold text-outline text-center px-1 pb-1 w-14">
                {lw}
              </td>
            ))}
          </tr>
        </thead>
        <tbody>
          {sortedShort.map((sw) => (
            <tr key={sw}>
              <td className="text-[10px] font-bold text-outline text-right pr-2">{sw}</td>
              {sortedLong.map((lw) => {
                const r = lookup[`${sw}_${lw}`]
                const invalid = sw >= lw
                const isBest  = best && r && sw === best.short_window && lw === best.long_window

                if (invalid) {
                  return (
                    <td key={lw} className="w-14 h-10 rounded text-center text-[10px] text-outline/20 bg-surface-container-lowest/30">
                      —
                    </td>
                  )
                }

                if (!r) {
                  return (
                    <td key={lw} className="w-14 h-10 rounded text-center animate-pulse bg-surface-container-lowest/50" />
                  )
                }

                const bg = sharpeColor(r.sharpe_ratio, minSharpe, maxSharpe)
                return (
                  <td
                    key={lw}
                    title={`Short=${sw} Long=${lw}\nSharpe: ${r.sharpe_ratio.toFixed(3)}\nReturn: ${r.total_return.toFixed(1)}%`}
                    className={`w-14 h-10 rounded text-center text-[10px] font-bold tabular-nums cursor-default transition-transform hover:scale-105 ${
                      isBest ? 'ring-2 ring-primary ring-offset-1 ring-offset-surface-container-low' : ''
                    }`}
                    style={{ background: bg, color: 'rgba(255,255,255,0.85)' }}
                  >
                    {r.sharpe_ratio.toFixed(2)}
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

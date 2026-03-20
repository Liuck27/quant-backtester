import { useEffect, useRef, useState } from 'react'
import { openStream, getResults } from '../api/client'
import EquityChart from './EquityChart'
import MetricsPanel from './MetricsPanel'

export default function LiveView({ jobId, jobConfig, onComplete }) {
  const [equityData, setEquityData] = useState([])
  const [fills, setFills] = useState([])
  const [liveEquity, setLiveEquity] = useState(jobConfig?.initial_capital)
  const [status, setStatus] = useState('CONNECTING')
  const [error, setError] = useState(null)
  const [barCount, setBarCount] = useState(0)
  const esRef = useRef(null)
  // Refs to capture latest state inside the SSE closure
  const equityRef = useRef([])
  const fillsRef = useRef([])

  useEffect(() => {
    const es = openStream(jobId)
    esRef.current = es

    es.onopen = () => setStatus('RUNNING')

    es.onmessage = (e) => {
      let evt
      try { evt = JSON.parse(e.data) }
      catch { return }

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
      } else if (evt.type === 'done') {
        setStatus('DONE')
        es.close()
        const snap = { equityData: equityRef.current, fills: fillsRef.current }
        getResults(jobId)
          .then((results) => onComplete(results, snap))
          .catch(() => {
            setTimeout(() => getResults(jobId).then((r) => onComplete(r, snap)).catch(console.error), 1000)
          })
      } else if (evt.type === 'error') {
        setError(evt.message)
        setStatus('ERROR')
        es.close()
      }
    }

    es.onerror = () => {
      if (status !== 'DONE') {
        setStatus('ERROR')
        setError('Connection lost')
      }
      es.close()
    }

    return () => es.close()
  }, [jobId]) // eslint-disable-line react-hooks/exhaustive-deps

  const ret = liveEquity && jobConfig?.initial_capital
    ? (((liveEquity - jobConfig.initial_capital) / jobConfig.initial_capital) * 100).toFixed(2)
    : null

  return (
    <div className="fade-in space-y-4">
      {/* Status bar */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            {status === 'RUNNING' && (
              <span className="live-dot w-2 h-2 rounded-full bg-accent inline-block" />
            )}
            {status === 'DONE' && (
              <span className="w-2 h-2 rounded-full bg-accent inline-block" />
            )}
            {status === 'ERROR' && (
              <span className="w-2 h-2 rounded-full bg-red inline-block" />
            )}
            {status === 'CONNECTING' && (
              <span className="w-2 h-2 rounded-full bg-amber inline-block" />
            )}
            <span className="font-mono text-[10px] text-dim uppercase tracking-widest">{status}</span>
          </div>
          <span className="text-border">|</span>
          <span className="font-mono text-xs text-dim">
            {jobConfig?.symbol} · {jobConfig?.strategy?.replace('_', ' ')}
          </span>
        </div>
        <div className="font-mono text-xs text-dim">{barCount} bars</div>
      </div>

      {/* Live equity headline */}
      <div className="border border-border rounded p-4 bg-surface">
        <div className="font-mono text-[10px] text-dim uppercase tracking-widest mb-1">Live Equity</div>
        <div className="flex items-baseline gap-3">
          <span className="font-mono text-3xl font-semibold text-bright">
            ${liveEquity?.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </span>
          {ret !== null && (
            <span className={`font-mono text-sm ${parseFloat(ret) >= 0 ? 'text-accent' : 'text-red'}`}>
              {parseFloat(ret) >= 0 ? '+' : ''}{ret}%
            </span>
          )}
          <span className="font-mono text-xs text-dim ml-auto">{fills.length} trades</span>
        </div>
      </div>

      {/* Chart */}
      <div className="border border-border rounded bg-surface" style={{ height: 320 }}>
        <div className="px-4 pt-3 pb-1 font-mono text-[10px] text-dim uppercase tracking-widest border-b border-border">
          Equity Curve
          <span className="ml-2 text-accent/50">▲ BUY</span>
          <span className="ml-2 text-red/50">▼ SELL</span>
        </div>
        <div style={{ height: 272 }}>
          <EquityChart equityData={equityData} fills={fills} live />
        </div>
      </div>

      {error && (
        <div className="border border-red/30 bg-red/5 rounded px-4 py-3 font-mono text-xs text-red">
          {error}
        </div>
      )}

      {status === 'DONE' && (
        <div className="text-center text-dim font-mono text-xs animate-pulse">
          Loading results…
        </div>
      )}
    </div>
  )
}

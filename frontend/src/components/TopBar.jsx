import { useState, useEffect } from 'react'

const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const POLL_INTERVAL_MS = 10000  // re-check every 10s regardless of state

export default function TopBar() {
  const [status, setStatus] = useState('checking') // 'checking' | 'waking' | 'online'

  useEffect(() => {
    let timer = null
    let destroyed = false

    const check = () => {
      const controller = new AbortController()
      const abortTimer = setTimeout(() => controller.abort(), 5000)

      fetch(`${BASE}/health`, { signal: controller.signal })
        .then((res) => {
          clearTimeout(abortTimer)
          if (!destroyed) setStatus(res.ok ? 'online' : 'waking')
        })
        .catch(() => {
          clearTimeout(abortTimer)
          // Covers both: connection refused (instant) and timeout (after 5s)
          if (!destroyed) setStatus('waking')
        })
        .finally(() => {
          if (!destroyed) timer = setTimeout(check, POLL_INTERVAL_MS)
        })
    }

    check()
    return () => {
      destroyed = true
      clearTimeout(timer)
    }
  }, [])

  const badge = status === 'online'
    ? { bg: 'bg-secondary/10', border: 'border-secondary/20', dot: 'bg-secondary', text: 'text-secondary', label: 'SYSTEM ONLINE' }
    : status === 'waking'
    ? { bg: 'bg-yellow-500/10', border: 'border-yellow-500/20', dot: 'bg-yellow-400 animate-pulse', text: 'text-yellow-400', label: 'SERVER STARTING UP\u2026' }
    : { bg: 'bg-outline/10', border: 'border-outline/20', dot: 'bg-outline animate-pulse', text: 'text-outline', label: 'CONNECTING\u2026' }

  return (
    <header className="bg-background/80 backdrop-blur-xl sticky top-0 z-40 w-full flex justify-between items-center px-8 h-16">
      <div className="flex items-center gap-4">
        <div className={`flex items-center gap-2 ${badge.bg} px-2 py-0.5 rounded border ${badge.border}`}>
          <span className={`w-1.5 h-1.5 rounded-full ${badge.dot}`} />
          <span className={`text-[10px] font-bold ${badge.text} tracking-tight`}>{badge.label}</span>
        </div>
      </div>
      <div />
    </header>
  )
}

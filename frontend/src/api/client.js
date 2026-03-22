const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

async function req(path, opts = {}) {
  const res = await fetch(`${BASE}${path}`, opts)
  if (!res.ok) {
    const text = await res.text()
    let msg
    try { msg = JSON.parse(text).detail ?? text }
    catch { msg = text }
    throw new Error(msg)
  }
  return res.json()
}

export const runBacktest = (body) =>
  req('/backtest/run', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })

export const getJobStatus = (jobId) => req(`/backtest/${jobId}`)
export const getResults   = (jobId) => req(`/results/${jobId}`)
export const getStrategies = ()     => req('/strategies')
export const getJobs      = ()      => req('/jobs')

export const openStream = (jobId) =>
  new EventSource(`${BASE}/stream/${jobId}`)

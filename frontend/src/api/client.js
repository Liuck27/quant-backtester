const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

function getSessionId() {
  const KEY = 'qb_session_id'
  let id = localStorage.getItem(KEY)
  if (!id) {
    id = crypto.randomUUID()
    localStorage.setItem(KEY, id)
  }
  return id
}

async function req(path, opts = {}, timeoutMs = 10000) {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeoutMs)
  const headers = { 'X-Session-ID': getSessionId(), ...(opts.headers ?? {}) }
  let res
  try {
    res = await fetch(`${BASE}${path}`, { ...opts, headers, signal: controller.signal })
  } catch (err) {
    if (err.name === 'AbortError') throw new Error('Request timed out')
    throw err
  } finally {
    clearTimeout(timer)
  }
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

export const runResearch = (body) =>
  req('/research/run', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  }, 15000)

export const getResearchJob  = (jobId) => req(`/research/${jobId}`)
export const openResearchStream = (jobId) =>
  new EventSource(`${BASE}/research/stream/${jobId}`)

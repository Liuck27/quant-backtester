const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

async function req(path, opts = {}, timeoutMs = 10000) {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeoutMs)
  let res
  try {
    res = await fetch(`${BASE}${path}`, { ...opts, signal: controller.signal })
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

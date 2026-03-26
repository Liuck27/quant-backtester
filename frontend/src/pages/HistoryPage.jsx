import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { getJobs, getResults } from '../api/client'

const statusColors = {
  COMPLETED: { bg: 'bg-secondary-container/20', text: 'text-secondary', dot: 'bg-secondary' },
  RUNNING:   { bg: 'bg-primary-container/20', text: 'text-primary', dot: 'bg-primary animate-pulse' },
  PENDING:   { bg: 'bg-surface-container-highest', text: 'text-gray-400', dot: 'bg-gray-500' },
  FAILED:    { bg: 'bg-error-container/20', text: 'text-error', dot: 'bg-error' },
}

const fmtDate = (s) => {
  if (!s) return '—'
  const d = new Date(s)
  return d.toLocaleString('en-US', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

export default function HistoryPage() {
  const navigate = useNavigate()
  const [jobs, setJobs] = useState([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('all')

  useEffect(() => {
    loadJobs()
    const interval = setInterval(loadJobs, 5000)
    return () => clearInterval(interval)
  }, [])

  const loadJobs = async () => {
    try {
      const data = await getJobs()
      setJobs(data.jobs ?? data ?? [])
    } catch (err) {
      console.error('Failed to load jobs:', err)
    } finally {
      setLoading(false)
    }
  }

  const filtered = filter === 'all'
    ? jobs
    : jobs.filter((j) => j.status?.toUpperCase() === filter.toUpperCase())

  const handleViewResults = async (job) => {
    const status = job.status?.toUpperCase()

    if (job.job_type === 'research') {
      if (status === 'COMPLETED') navigate(`/research?job=${job.job_id}`)
      return
    }

    if (status === 'RUNNING') {
      navigate(`/results/${job.job_id}`, {
        state: { live: true, symbol: job.symbol, strategy: job.strategy },
      })
      return
    }
    if (status !== 'COMPLETED') return
    try {
      const results = await getResults(job.job_id)
      navigate(`/results/${job.job_id}`, { state: { results } })
    } catch (err) {
      console.error('Failed to load results:', err)
    }
  }

  return (
    <div className="fade-in">
      {/* Header */}
      <div className="flex justify-between items-end mb-10">
        <div>
          <h2 className="text-4xl font-extrabold font-headline tracking-tight text-white mb-2">All Backtest Jobs</h2>
          <p className="text-on-surface-variant text-sm max-w-xl">Historical execution log and performance auditing for quantitative strategies.</p>
        </div>
        <button
          onClick={() => navigate('/')}
          className="flex items-center gap-2 px-6 py-2.5 bg-surface-container-highest text-primary rounded-md font-semibold text-sm hover:bg-surface-container-high transition-colors"
        >
          <span className="material-symbols-outlined text-sm">add</span>
          Run New
        </button>
      </div>

      {/* Filter Bar */}
      <div className="bg-surface-container-low p-4 rounded-xl flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          {['all', 'COMPLETED', 'RUNNING', 'FAILED'].map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-4 py-1.5 rounded-full text-xs font-semibold transition-colors ${
                filter === f
                  ? 'bg-surface-container-highest text-primary'
                  : 'hover:bg-surface-container-high text-gray-500 cursor-pointer'
              }`}
            >
              {f === 'all' ? 'All Jobs' : f.charAt(0) + f.slice(1).toLowerCase()}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-2 text-gray-500 text-xs font-medium">
          <span>{filtered.length} jobs</span>
        </div>
      </div>

      {/* Jobs List */}
      {loading ? (
        <div className="text-center text-outline py-20">Loading jobs...</div>
      ) : filtered.length === 0 ? (
        <div className="text-center text-outline py-20">
          <span className="material-symbols-outlined text-4xl mb-4 block opacity-30">inbox</span>
          <p>No backtest jobs found. Run your first backtest!</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4">
          {filtered.map((job) => {
            const st = statusColors[job.status?.toUpperCase()] ?? statusColors.PENDING
            const totalReturn = job.total_return

            return (
              <div
                key={job.job_id}
                className="group bg-surface-container-low hover:bg-surface-container-high transition-all duration-300 rounded-xl overflow-hidden flex items-center p-6 gap-8"
              >
                <div className="flex-1 grid grid-cols-5 items-center gap-6">
                  <div className="col-span-1">
                    <p className="text-gray-500 mb-1 uppercase tracking-widest text-[10px]">Job ID</p>
                    <p className="font-mono text-sm text-on-surface font-medium">#{job.job_id?.slice(0, 8)}</p>
                  </div>
                  <div>
                    <p className="text-gray-500 mb-1 uppercase tracking-widest text-[10px]">Symbol</p>
                    <p className="text-md font-bold text-white tabular-nums">{job.symbol ?? '—'}</p>
                  </div>
                  <div>
                    <p className="text-gray-500 mb-1 uppercase tracking-widest text-[10px]">Strategy</p>
                    <p className="text-sm font-medium text-on-surface">{job.strategy?.replace('_', ' ') ?? '—'}</p>
                  </div>
                  <div>
                    <p className="text-gray-500 mb-1 uppercase tracking-widest text-[10px]">Date</p>
                    <p className="text-sm text-gray-400 tabular-nums">{fmtDate(job.created_at)}</p>
                  </div>
                  <div className="flex items-center justify-end">
                    <span className={`px-3 py-1 rounded-full ${st.bg} ${st.text} text-[11px] font-bold uppercase tracking-wider flex items-center gap-1.5`}>
                      <span className={`w-1.5 h-1.5 rounded-full ${st.dot}`} />
                      {job.status}
                    </span>
                  </div>
                </div>

                <div className="w-px h-12 bg-outline-variant/20" />

                <div className="flex items-center gap-6 w-72">
                  {totalReturn != null ? (
                    <div className="text-right flex-1">
                      <p className="text-[10px] text-gray-500 uppercase tracking-widest mb-0.5">
                        {job.job_type === 'research' ? 'Best Sharpe' : 'Total Return'}
                      </p>
                      <p className={`text-xl font-bold tabular-nums ${totalReturn >= 0 ? 'text-secondary' : 'text-tertiary-container'}`}>
                        {job.job_type === 'research'
                          ? Number(totalReturn).toFixed(2)
                          : `${totalReturn >= 0 ? '+' : ''}${Number(totalReturn).toFixed(1)}%`}
                      </p>
                    </div>
                  ) : job.status?.toUpperCase() === 'RUNNING' ? (
                    <div className="flex flex-col gap-2 flex-1">
                      <div className="flex justify-between items-center text-[10px] text-gray-500 uppercase tracking-widest">
                        <span>Running</span>
                      </div>
                      <div className="w-full h-1 bg-surface-container-highest rounded-full overflow-hidden">
                        <div className="h-full bg-primary animate-pulse" style={{ width: '100%' }} />
                      </div>
                    </div>
                  ) : job.status?.toUpperCase() === 'FAILED' ? (
                    <div className="flex items-center gap-3 flex-1 text-error text-xs">
                      <span className="material-symbols-outlined text-lg">error</span>
                      <span className="font-medium">Execution failed</span>
                    </div>
                  ) : (
                    <div className="flex items-center gap-3 flex-1 text-gray-500 text-xs">
                      <span className="material-symbols-outlined text-lg">schedule</span>
                      <span className="font-medium">Pending</span>
                    </div>
                  )}
                </div>

                <button
                  onClick={() => handleViewResults(job)}
                  className={`p-3 rounded-lg bg-surface-container-highest text-on-surface hover:text-primary transition-colors ${
                    ['PENDING', 'FAILED'].includes(job.status?.toUpperCase()) ? 'opacity-50 cursor-not-allowed' : ''
                  }`}
                  disabled={['PENDING', 'FAILED'].includes(job.status?.toUpperCase())}
                >
                  <span className="material-symbols-outlined">chevron_right</span>
                </button>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

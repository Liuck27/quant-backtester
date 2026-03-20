import { useState } from 'react'
import RunForm from './components/RunForm'
import LiveView from './components/LiveView'
import ResultsView from './components/ResultsView'

// view: 'form' | 'live' | 'results'
export default function App() {
  const [view, setView] = useState('form')
  const [jobId, setJobId] = useState(null)
  const [jobConfig, setJobConfig] = useState(null)
  // Store equity/fill data collected during live stream for the results chart
  const [streamData, setStreamData] = useState({ equityData: [], fills: [] })
  const [results, setResults] = useState(null)

  const handleJobStarted = (id, config) => {
    setJobId(id)
    setJobConfig(config)
    setStreamData({ equityData: [], fills: [] })
    setResults(null)
    setView('live')
  }

  // Called by LiveView once the backtest completes and results are fetched
  const handleComplete = (fullResults, snap) => {
    setResults(fullResults)
    if (snap) setStreamData(snap)
    setView('results')
  }

  return (
    <div className="min-h-screen bg-bg">
      {/* Top bar */}
      <header className="border-b border-border bg-surface/80 backdrop-blur sticky top-0 z-10">
        <div className="max-w-5xl mx-auto px-6 h-12 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="font-mono text-accent font-semibold text-sm tracking-wider">QBTS</span>
            <span className="text-border text-xs">|</span>
            <span className="font-mono text-dim text-xs uppercase tracking-widest">
              {view === 'form' && 'Configure'}
              {view === 'live' && 'Live · ' + (jobConfig?.symbol ?? '')}
              {view === 'results' && 'Results · ' + (results?.symbol ?? '')}
            </span>
          </div>
          <div className="flex items-center gap-2">
            {view !== 'form' && (
              <button
                onClick={() => setView('form')}
                className="font-mono text-[10px] text-dim hover:text-accent transition-colors uppercase tracking-widest"
              >
                ← New Run
              </button>
            )}
          </div>
        </div>
      </header>

      {/* Main */}
      <main className="max-w-5xl mx-auto px-6 py-10">
        {view === 'form' && (
          <RunForm onJobStarted={handleJobStarted} />
        )}

        {view === 'live' && (
          <LiveView
            key={jobId}
            jobId={jobId}
            jobConfig={jobConfig}
            onComplete={handleComplete}
          />
        )}

        {view === 'results' && results && (
          <ResultsView
            results={results}
            equityData={streamData.equityData}
            fills={streamData.fills}
            onNewRun={() => setView('form')}
          />
        )}
      </main>
    </div>
  )
}

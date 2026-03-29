import { Routes, Route } from 'react-router-dom'
import Sidebar from './components/Sidebar'
import TopBar from './components/TopBar'
import BacktestPage from './pages/BacktestPage'
import HistoryPage from './pages/HistoryPage'
import ResultsPage from './pages/ResultsPage'
import ResearchPage from './pages/ResearchPage'
import AboutPage from './pages/AboutPage'

export default function App() {
  return (
    <div className="min-h-screen bg-background text-on-surface font-body">
      <Sidebar />
      <div className="ml-64 min-h-screen flex flex-col">
        <TopBar />
        <main className="p-8 flex-1">
          <Routes>
            <Route path="/" element={<BacktestPage />} />
            <Route path="/history" element={<HistoryPage />} />
            <Route path="/results/:jobId" element={<ResultsPage />} />
            <Route path="/research" element={<ResearchPage />} />
            <Route path="/about" element={<AboutPage />} />
          </Routes>
        </main>
      </div>
      {/* Background decoration */}
      <div className="fixed inset-0 -z-10 pointer-events-none overflow-hidden">
        <div className="absolute top-[-10%] right-[-5%] w-[40%] h-[40%] bg-primary/5 blur-[120px] rounded-full" />
        <div className="absolute bottom-[-5%] left-[20%] w-[30%] h-[30%] bg-secondary/5 blur-[100px] rounded-full" />
      </div>
    </div>
  )
}

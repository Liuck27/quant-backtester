import { NavLink, useNavigate } from 'react-router-dom'

const navItems = [
  { to: '/', icon: 'history_toggle_off', label: 'Backtest' },
  { to: '/research', icon: 'grid_view', label: 'Research' },
  { to: '/history', icon: 'manage_history', label: 'History' },
]

export default function Sidebar() {
  const navigate = useNavigate()

  return (
    <aside className="bg-surface-container-low h-screen w-64 fixed left-0 top-0 overflow-y-auto flex flex-col py-8 px-4 z-50">
      <div className="mb-10 px-2">
        <h1 className="text-xl font-bold tracking-tight text-white font-headline">QuantBacktester</h1>
        <p className="text-[10px] uppercase tracking-widest text-primary/60 font-semibold">Institutional Grade</p>
      </div>

      <nav className="flex-1 space-y-1">
        {navItems.map(({ to, icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-md transition-colors duration-200 group ${
                isActive
                  ? 'text-[#3B82F6] font-semibold border-r-2 border-[#3B82F6] bg-blue-500/5'
                  : 'text-gray-500 hover:text-gray-300 hover:bg-surface-container-highest'
              }`
            }
          >
            <span className="material-symbols-outlined text-[20px]">{icon}</span>
            <span className="text-sm font-medium">{label}</span>
          </NavLink>
        ))}
      </nav>

      <button
        onClick={() => navigate('/')}
        className="mt-8 bg-gradient-to-br from-primary to-primary-container text-on-primary-container font-bold py-3 px-4 rounded-md text-sm transition-transform active:scale-95"
      >
        New Backtest
      </button>
    </aside>
  )
}

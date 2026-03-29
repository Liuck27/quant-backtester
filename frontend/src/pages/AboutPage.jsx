const STRATEGIES = [
  {
    icon: 'show_chart',
    name: 'Moving Average Crossover',
    badge: 'Active',
    badgeCls: 'text-primary bg-primary/10',
    description:
      'A trend-following strategy. It generates a BUY signal when a short-term moving average crosses above a long-term one (Golden Cross), and an EXIT signal when it crosses back below (Death Cross). Works best in trending markets, struggles in sideways/choppy conditions.',
    params: ['Fast Period', 'Slow Period'],
    dimmed: false,
  },
  {
    icon: 'sync',
    name: 'RSI Mean-Reversion',
    badge: 'Active',
    badgeCls: 'text-primary bg-primary/10',
    description:
      'A momentum oscillator strategy. RSI (Relative Strength Index) measures the speed and magnitude of recent price changes. The strategy buys when RSI drops below the oversold threshold (asset is cheap relative to recent history) and exits when it rises above the overbought threshold. Works best in range-bound markets.',
    params: ['RSI Period', 'Oversold Level', 'Overbought Level'],
    dimmed: false,
  },
  {
    icon: 'psychology',
    name: 'ML Signal',
    badge: 'Coming Soon',
    badgeCls: 'text-outline bg-surface-container-high',
    description:
      'A machine learning strategy that trains a scikit-learn classifier on historical price features to predict next-bar direction. Currently in development — will be available in a future release.',
    params: [],
    dimmed: true,
  },
]

const TECH = [
  { label: 'Backend', items: ['Python', 'FastAPI', 'SQLAlchemy', 'scikit-learn', 'PostgreSQL'] },
  { label: 'Frontend', items: ['React 18', 'Recharts', 'Tailwind CSS', 'Vite'] },
  { label: 'Infrastructure', items: ['Docker', 'Server-Sent Events (real-time streaming)'] },
]

export default function AboutPage() {
  return (
    <div className="fade-in space-y-8">
      {/* Header */}
      <div>
        <p className="text-[11px] font-bold text-outline uppercase tracking-wider mb-2">Documentation</p>
        <h1 className="text-2xl font-extrabold font-headline tracking-tight text-white">
          About QuantBacktester
        </h1>
        <p className="text-sm text-outline mt-1">
          An event-driven backtesting engine with live visualization
        </p>
      </div>

      {/* What is a Backtest? */}
      <div className="bg-surface-container-low rounded-xl p-6">
        <p className="text-xs font-bold text-outline uppercase tracking-wider mb-3">
          What is a Backtest?
        </p>
        <p className="text-sm text-outline leading-relaxed">
          A backtest simulates a trading strategy on historical price data to estimate how it would
          have performed in the past. It does not guarantee future results, but it helps understand
          the mechanics and risk profile of a strategy before committing real capital. By measuring
          metrics like Sharpe ratio, maximum drawdown, and total return across different market
          regimes, you can develop more informed intuition about a strategy's strengths and failure
          modes.
        </p>
      </div>

      {/* Strategies */}
      <div>
        <p className="text-xs font-bold text-outline uppercase tracking-wider mb-4">Strategies</p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {STRATEGIES.map((s) => (
            <div
              key={s.name}
              className={`bg-surface-container-low rounded-xl p-6 flex flex-col gap-4 border border-white/5 ${
                s.dimmed ? 'opacity-60' : ''
              }`}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0">
                    <span className="material-symbols-outlined text-primary text-[20px]">
                      {s.icon}
                    </span>
                  </div>
                  <span className="text-sm font-bold text-white leading-tight">{s.name}</span>
                </div>
                <span
                  className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full flex-shrink-0 ${s.badgeCls}`}
                >
                  {s.badge}
                </span>
              </div>

              <p className="text-sm text-outline leading-relaxed">{s.description}</p>

              {s.params.length > 0 && (
                <div>
                  <p className="text-[10px] font-bold text-outline uppercase tracking-wider mb-2">
                    Parameters
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {s.params.map((p) => (
                      <span
                        key={p}
                        className="text-[11px] bg-surface-container-high text-on-surface-variant px-2.5 py-1 rounded-full font-medium"
                      >
                        {p}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Parameter Research */}
      <div className="bg-surface-container-low rounded-xl p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-9 h-9 rounded-lg bg-secondary/10 flex items-center justify-center flex-shrink-0">
            <span className="material-symbols-outlined text-secondary text-[20px]">grid_view</span>
          </div>
          <p className="text-xs font-bold text-outline uppercase tracking-wider">
            Parameter Research
          </p>
        </div>
        <p className="text-sm text-outline leading-relaxed mb-4">
          The Research page automates the process of finding optimal strategy parameters so you
          don't have to run backtests by hand for every combination.
        </p>
        <ul className="space-y-2">
          {[
            'Runs a full grid search over all combinations of strategy parameters',
            'Ranks each combination by Sharpe ratio (risk-adjusted return)',
            'Visualizes results as a heatmap (MA Crossover) or ranked table (RSI)',
            'The best-performing combination can be launched as a full backtest with one click',
          ].map((item) => (
            <li key={item} className="flex items-start gap-2.5 text-sm text-outline">
              <span className="material-symbols-outlined text-secondary text-[16px] mt-0.5 flex-shrink-0">
                check_circle
              </span>
              {item}
            </li>
          ))}
        </ul>
      </div>

      {/* Tech Stack */}
      <div className="bg-surface-container-low rounded-xl p-6">
        <p className="text-xs font-bold text-outline uppercase tracking-wider mb-5">Built with</p>
        <div className="space-y-5">
          {TECH.map(({ label, items }) => (
            <div key={label}>
              <p className="text-[10px] font-bold text-outline uppercase tracking-wider mb-2.5">
                {label}
              </p>
              <div className="flex flex-wrap gap-2">
                {items.map((item) => (
                  <span
                    key={item}
                    className="bg-surface-container-high text-on-surface-variant text-xs px-3 py-1.5 rounded-full font-medium"
                  >
                    {item}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

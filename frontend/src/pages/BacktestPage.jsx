import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { runBacktest } from '../api/client'

const MA_DEFAULTS = { short_window: 10, long_window: 50 }
const RSI_DEFAULTS = { rsi_period: 14, oversold: 30, overbought: 70 }
const ML_DEFAULTS = {
  model_type: 'random_forest',
  lookback_window: 252,
  retrain_every: 20,
  long_threshold: 0.6,
  exit_threshold: 0.4,
}

const inputCls =
  'w-full bg-surface-container-lowest border-none focus:ring-1 focus:ring-primary rounded-md py-2.5 px-4 text-sm font-medium text-on-surface'

export default function BacktestPage() {
  const navigate = useNavigate()

  const [symbol, setSymbol] = useState('AAPL')
  const [startDate, setStartDate] = useState('2022-01-01')
  const [endDate, setEndDate] = useState('2024-01-01')
  const [strategy, setStrategy] = useState('ma_crossover')
  const [capital, setCapital] = useState(100000)
  const [maParams, setMaParams] = useState(MA_DEFAULTS)
  const [mlParams, setMlParams] = useState(ML_DEFAULTS)
  const [rsiParams, setRsiParams] = useState(RSI_DEFAULTS)
  const [advancedOpen, setAdvancedOpen] = useState(false)
  const [commissionRate, setCommissionRate] = useState(0.1)   // displayed as %
  const [slippageRate, setSlippageRate] = useState(0.05)      // displayed as %
  const [riskPerTrade, setRiskPerTrade] = useState(2.0)       // displayed as %
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError(null)
    setLoading(true)

    try {
      const params = strategy === 'ma_crossover'
        ? { short_window: Number(maParams.short_window), long_window: Number(maParams.long_window) }
        : strategy === 'rsi'
        ? { rsi_period: Number(rsiParams.rsi_period), oversold: Number(rsiParams.oversold), overbought: Number(rsiParams.overbought) }
        : {
            model_type: mlParams.model_type,
            lookback_window: Number(mlParams.lookback_window),
            retrain_every: Number(mlParams.retrain_every),
            long_threshold: Number(mlParams.long_threshold),
            exit_threshold: Number(mlParams.exit_threshold),
          }

      const res = await runBacktest({
        symbol: symbol.toUpperCase().trim(),
        start_date: startDate,
        end_date: endDate,
        strategy,
        parameters: params,
        initial_capital: Number(capital),
        commission_rate: Number(commissionRate) / 100,
        slippage_rate: Number(slippageRate) / 100,
        risk_per_trade: Number(riskPerTrade) / 100,
      })

      navigate(`/results/${res.job_id}`, {
        state: {
          live: true,
          symbol: symbol.toUpperCase().trim(),
          strategy,
          initialCapital: Number(capital),
        },
      })
    } catch (err) {
      setError(err.message)
      setLoading(false)
    }
  }

  return (
    <div className="fade-in max-w-xl mx-auto mt-8">
      <div className="bg-surface-container-low p-8 rounded-xl">
        <h2 className="text-lg font-headline font-semibold text-white mb-6">Configure Backtest</h2>
        <form onSubmit={handleSubmit} className="space-y-5">
          <div className="space-y-1.5">
            <label className="text-[11px] font-bold text-outline uppercase tracking-wider">Symbol</label>
            <input className={inputCls} type="text" value={symbol} onChange={(e) => setSymbol(e.target.value)} required />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label className="text-[11px] font-bold text-outline uppercase tracking-wider">Start Date</label>
              <input className={inputCls + ' py-2 px-3 text-xs'} type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} required />
            </div>
            <div className="space-y-1.5">
              <label className="text-[11px] font-bold text-outline uppercase tracking-wider">End Date</label>
              <input className={inputCls + ' py-2 px-3 text-xs'} type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} required />
            </div>
          </div>

          <div className="space-y-1.5">
            <label className="text-[11px] font-bold text-outline uppercase tracking-wider">Strategy</label>
            <select className={inputCls + ' appearance-none'} value={strategy} onChange={(e) => setStrategy(e.target.value)}>
              <option value="ma_crossover">Moving Average Crossover</option>
              <option value="rsi">RSI Mean-Reversion</option>
            </select>
          </div>

          <div className="pt-4 border-t border-outline-variant/10">
            <h3 className="text-xs font-bold text-white mb-4">Parameters</h3>
            {strategy === 'ma_crossover' ? (
              <div className="space-y-4">
                <ParamRow label="Fast Period" value={maParams.short_window} onChange={(v) => setMaParams((p) => ({ ...p, short_window: v }))} />
                <ParamRow label="Slow Period" value={maParams.long_window} onChange={(v) => setMaParams((p) => ({ ...p, long_window: v }))} />
              </div>
            ) : (
              <div className="space-y-4">
                <ParamRow label="RSI Period" value={rsiParams.rsi_period} onChange={(v) => setRsiParams((p) => ({ ...p, rsi_period: v }))} />
                <ParamRow label="Oversold" value={rsiParams.oversold} onChange={(v) => setRsiParams((p) => ({ ...p, oversold: v }))} step={1} />
                <ParamRow label="Overbought" value={rsiParams.overbought} onChange={(v) => setRsiParams((p) => ({ ...p, overbought: v }))} step={1} />
              </div>
            )}
            <ParamRow label="Initial Capital" value={capital} onChange={setCapital} className="mt-4" inputClassName="w-24" />
          </div>

          {/* Advanced */}
          <div className="pt-4 border-t border-outline-variant/10">
            <button
              type="button"
              onClick={() => setAdvancedOpen((v) => !v)}
              className="flex items-center justify-between w-full text-xs font-bold text-outline hover:text-on-surface transition-colors"
            >
              <span className="uppercase tracking-wider">Advanced</span>
              <span className="material-symbols-outlined text-base">{advancedOpen ? 'expand_less' : 'expand_more'}</span>
            </button>
            {advancedOpen && (
              <div className="mt-4 space-y-4">
                <ParamRow label="Commission %" value={commissionRate} onChange={setCommissionRate} step={0.01} inputClassName="w-20" />
                <ParamRow label="Slippage %" value={slippageRate} onChange={setSlippageRate} step={0.01} inputClassName="w-20" />
                <ParamRow label="Risk per Trade %" value={riskPerTrade} onChange={setRiskPerTrade} step={0.5} inputClassName="w-20" />
              </div>
            )}
          </div>

          {error && (
            <div className="bg-error-container/20 text-error rounded-md px-4 py-3 text-xs">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-gradient-to-br from-primary to-primary-container text-on-primary-container font-bold py-3.5 rounded-md text-sm mt-4 shadow-lg shadow-primary/10 hover:shadow-primary/20 transition-all active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? 'Starting...' : 'Run Backtest'}
          </button>
        </form>
      </div>
    </div>
  )
}

function ParamRow({ label, value, onChange, step, className = '', inputClassName = 'w-16' }) {
  return (
    <div className={`flex items-center justify-between ${className}`}>
      <span className="text-xs text-outline">{label}</span>
      <input
        className={`bg-surface-container-lowest border-none ${inputClassName} py-1 px-2 rounded text-xs text-right tabular-nums text-on-surface`}
        type="number"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        step={step}
      />
    </div>
  )
}

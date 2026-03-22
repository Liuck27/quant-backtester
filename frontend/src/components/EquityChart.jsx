import {
  ComposedChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer,
} from 'recharts'

const fmt = (v) =>
  v >= 1_000_000
    ? `$${(v / 1_000_000).toFixed(2)}M`
    : `$${(v / 1_000).toFixed(1)}k`

const fmtDate = (s) => {
  if (!s) return ''
  const d = new Date(s)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

const CustomTooltip = ({ active, payload }) => {
  if (!active || !payload?.length) return null
  const d = payload[0].payload
  const ret = d.initialEquity
    ? (((d.equity - d.initialEquity) / d.initialEquity) * 100).toFixed(2)
    : null
  return (
    <div className="bg-surface-container-highest border border-outline-variant/20 rounded-lg px-3 py-2 shadow-2xl backdrop-blur-md">
      <div className="text-[10px] text-outline uppercase font-bold tracking-tighter mb-1">{fmtDate(d.time)}</div>
      <div className="text-sm font-bold tabular-nums text-white">{fmt(d.equity)}</div>
      {ret !== null && (
        <div className={`text-[10px] tabular-nums ${parseFloat(ret) >= 0 ? 'text-secondary' : 'text-tertiary'}`}>
          {parseFloat(ret) >= 0 ? '+' : ''}{ret}%
        </div>
      )}
    </div>
  )
}

const TradeDot = (props) => {
  const { cx, cy, payload } = props
  if (!payload.fillDirection) return null
  const isBuy = payload.fillDirection === 'BUY'
  const color = isBuy ? '#4edea3' : '#ffb3ad'
  return <circle cx={cx} cy={cy} r={4} fill={color} />
}

export default function EquityChart({ equityData, fills = [], live = false }) {
  if (!equityData?.length) {
    return (
      <div className="flex items-center justify-center h-full text-outline font-body text-sm">
        {live ? 'Waiting for data...' : 'No data'}
      </div>
    )
  }

  const fillMap = {}
  fills.forEach((f) => { fillMap[f.time] = f.direction })

  const initialEquity = equityData[0]?.equity

  const chartData = equityData.map((pt) => ({
    ...pt,
    initialEquity,
    fillDirection: fillMap[pt.time] ?? null,
  }))

  const equities = chartData.map((d) => d.equity)
  const minEq = Math.min(...equities)
  const maxEq = Math.max(...equities)
  const pad = (maxEq - minEq) * 0.05 || 1000
  const domain = [minEq - pad, maxEq + pad]

  const tickCount = Math.min(chartData.length, 6)
  const step = Math.floor(chartData.length / tickCount)
  const ticks = chartData
    .filter((_, i) => i % step === 0)
    .map((d) => d.time)

  return (
    <ResponsiveContainer width="100%" height="100%">
      <ComposedChart data={chartData} margin={{ top: 8, right: 16, bottom: 0, left: 8 }}>
        <defs>
          <linearGradient id="eqGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%"  stopColor="#adc6ff" stopOpacity={0.2} />
            <stop offset="95%" stopColor="#adc6ff" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#424754" strokeOpacity={0.15} vertical={false} />
        <XAxis
          dataKey="time"
          ticks={ticks}
          tickFormatter={fmtDate}
          tick={{ fill: '#8c909f', fontSize: 10, fontFamily: 'Inter' }}
          axisLine={{ stroke: '#424754', strokeOpacity: 0.2 }}
          tickLine={false}
        />
        <YAxis
          domain={domain}
          tickFormatter={fmt}
          tick={{ fill: '#8c909f', fontSize: 10, fontFamily: 'Inter' }}
          axisLine={false}
          tickLine={false}
          width={56}
        />
        <Tooltip content={<CustomTooltip />} />
        <Area
          type="monotone"
          dataKey="equity"
          stroke="#adc6ff"
          strokeWidth={2.5}
          fill="url(#eqGrad)"
          dot={<TradeDot />}
          activeDot={{ r: 4, fill: '#adc6ff' }}
          isAnimationActive={!live}
        />
      </ComposedChart>
    </ResponsiveContainer>
  )
}

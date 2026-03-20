import {
  ComposedChart, Area, Scatter, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ReferenceLine,
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
    <div className="bg-panel border border-border rounded px-3 py-2 font-mono text-xs">
      <div className="text-dim mb-1">{fmtDate(d.time)}</div>
      <div className="text-bright">{fmt(d.equity)}</div>
      {ret !== null && (
        <div className={parseFloat(ret) >= 0 ? 'text-accent' : 'text-red'}>
          {parseFloat(ret) >= 0 ? '+' : ''}{ret}%
        </div>
      )}
    </div>
  )
}

// Custom dot for trade markers
const TradeDot = (props) => {
  const { cx, cy, payload } = props
  if (!payload.fillDirection) return null
  const isBuy = payload.fillDirection === 'BUY'
  const color = isBuy ? '#00c896' : '#e04848'
  const size = 5
  // Triangle up for BUY, down for SELL
  const points = isBuy
    ? `${cx},${cy - size} ${cx - size},${cy + size} ${cx + size},${cy + size}`
    : `${cx},${cy + size} ${cx - size},${cy - size} ${cx + size},${cy - size}`
  return <polygon points={points} fill={color} opacity={0.85} />
}

export default function EquityChart({ equityData, fills = [], live = false }) {
  if (!equityData?.length) {
    return (
      <div className="flex items-center justify-center h-full text-dim font-mono text-sm">
        {live ? 'Waiting for data…' : 'No data'}
      </div>
    )
  }

  // Merge fills into equity data by matching closest time
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
      <ComposedChart data={chartData} margin={{ top: 4, right: 16, bottom: 0, left: 8 }}>
        <defs>
          <linearGradient id="eqGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%"  stopColor="#00c896" stopOpacity={0.18} />
            <stop offset="95%" stopColor="#00c896" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#1c2030" vertical={false} />
        <XAxis
          dataKey="time"
          ticks={ticks}
          tickFormatter={fmtDate}
          tick={{ fill: '#4a5268', fontSize: 10, fontFamily: 'JetBrains Mono' }}
          axisLine={{ stroke: '#1c2030' }}
          tickLine={false}
        />
        <YAxis
          domain={domain}
          tickFormatter={fmt}
          tick={{ fill: '#4a5268', fontSize: 10, fontFamily: 'JetBrains Mono' }}
          axisLine={false}
          tickLine={false}
          width={56}
        />
        <Tooltip content={<CustomTooltip />} />
        <Area
          type="monotone"
          dataKey="equity"
          stroke="#00c896"
          strokeWidth={1.5}
          fill="url(#eqGrad)"
          dot={<TradeDot />}
          activeDot={{ r: 3, fill: '#00c896' }}
          isAnimationActive={!live}
        />
      </ComposedChart>
    </ResponsiveContainer>
  )
}

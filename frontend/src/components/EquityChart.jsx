import {
  ComposedChart, Area, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer,
} from 'recharts'

const computeSMA = (data, window) =>
  data.map((_, i) =>
    i < window - 1
      ? null
      : data.slice(i - window + 1, i + 1).reduce((s, d) => s + (d.price ?? 0), 0) / window
  )

const fmtMoney = (v) =>
  v >= 1_000_000
    ? `$${(v / 1_000_000).toFixed(2)}M`
    : `$${(v / 1_000).toFixed(1)}k`

const fmtPrice = (v) => `$${Number(v).toFixed(2)}`

const fmtDate = (s) => {
  if (!s) return ''
  const d = new Date(s)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

const EquityTooltip = ({ active, payload }) => {
  if (!active || !payload?.length) return null
  const d = payload[0].payload
  const ret = d.initialEquity
    ? (((d.equity - d.initialEquity) / d.initialEquity) * 100).toFixed(2)
    : null
  return (
    <div className="bg-surface-container-highest border border-outline-variant/20 rounded-lg px-3 py-2 shadow-2xl backdrop-blur-md">
      <div className="text-[10px] text-outline uppercase font-bold tracking-tighter mb-1">{fmtDate(d.time)}</div>
      <div className="text-sm font-bold tabular-nums text-white">{fmtMoney(d.equity)}</div>
      {ret !== null && (
        <div className={`text-[10px] tabular-nums ${parseFloat(ret) >= 0 ? 'text-secondary' : 'text-tertiary-container'}`}>
          {parseFloat(ret) >= 0 ? '+' : ''}{ret}%
        </div>
      )}
    </div>
  )
}

const PriceTooltip = ({ active, payload }) => {
  if (!active || !payload?.length) return null
  const d = payload[0].payload
  const ret = d.initialPrice && d.price
    ? (((d.price - d.initialPrice) / d.initialPrice) * 100).toFixed(2)
    : null
  return (
    <div className="bg-surface-container-highest border border-outline-variant/20 rounded-lg px-3 py-2 shadow-2xl backdrop-blur-md">
      <div className="text-[10px] text-outline uppercase font-bold tracking-tighter mb-1">{fmtDate(d.time)}</div>
      <div className="text-sm font-bold tabular-nums text-white">{fmtPrice(d.price)}</div>
      {ret !== null && (
        <div className={`text-[10px] tabular-nums ${parseFloat(ret) >= 0 ? 'text-secondary' : 'text-tertiary-container'}`}>
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
  const color = isBuy ? '#4edea3' : '#ff5451'
  return <circle cx={cx} cy={cy} r={4} fill={color} />
}

export default function EquityChart({ equityData, fills = [], live = false, mode = 'equity', showMA = false, maParams = null }) {
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
  const initialPrice = equityData[0]?.price

  const chartData = equityData.map((pt) => ({
    ...pt,
    initialEquity,
    initialPrice,
    fillDirection: fillMap[pt.time] ?? null,
  }))

  const tickCount = Math.min(chartData.length, 6)
  const step = Math.floor(chartData.length / tickCount)
  const ticks = chartData
    .filter((_, i) => i % step === 0)
    .map((d) => d.time)

  if (mode === 'price') {
    const hasPriceData = chartData.some((d) => d.price != null)
    if (!hasPriceData) {
      return (
        <div className="flex items-center justify-center h-full text-outline font-body text-sm">
          Price data not available for this backtest
        </div>
      )
    }

    // Inject MA values if requested
    let priceChartData = chartData
    if (showMA && maParams) {
      const shortVals = computeSMA(chartData, maParams.shortWindow)
      const longVals  = computeSMA(chartData, maParams.longWindow)
      priceChartData = chartData.map((d, i) => ({
        ...d,
        maShort: shortVals[i],
        maLong:  longVals[i],
      }))
    }

    const prices = priceChartData.map((d) => d.price).filter((p) => p != null)
    const minP = Math.min(...prices)
    const maxP = Math.max(...prices)
    const pad = (maxP - minP) * 0.05 || 1
    const domain = [minP - pad, maxP + pad]

    return (
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={priceChartData} margin={{ top: 8, right: 16, bottom: 0, left: 8 }}>
          <defs>
            <linearGradient id="priceGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%"  stopColor="#c9a7ff" stopOpacity={0.2} />
              <stop offset="95%" stopColor="#c9a7ff" stopOpacity={0} />
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
            tickFormatter={fmtPrice}
            tick={{ fill: '#8c909f', fontSize: 10, fontFamily: 'Inter' }}
            axisLine={false}
            tickLine={false}
            width={64}
          />
          <Tooltip content={<PriceTooltip />} />
          {showMA && maParams && (
            <>
              <Line type="monotone" dataKey="maShort" stroke="#ffd966" strokeWidth={1.5} dot={false} isAnimationActive={false} connectNulls name={`MA ${maParams.shortWindow}`} />
              <Line type="monotone" dataKey="maLong"  stroke="#ff8c42" strokeWidth={1.5} dot={false} isAnimationActive={false} connectNulls name={`MA ${maParams.longWindow}`} />
            </>
          )}
          <Area
            type="monotone"
            dataKey="price"
            stroke="#c9a7ff"
            strokeWidth={2.5}
            fill="url(#priceGrad)"
            dot={<TradeDot />}
            activeDot={{ r: 4, fill: '#c9a7ff' }}
            isAnimationActive={!live}
          />
        </ComposedChart>
      </ResponsiveContainer>
    )
  }

  // Default: equity mode
  const equities = chartData.map((d) => d.equity)
  const minEq = Math.min(...equities)
  const maxEq = Math.max(...equities)
  const pad = (maxEq - minEq) * 0.05 || 1000
  const domain = [minEq - pad, maxEq + pad]

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
          tickFormatter={fmtMoney}
          tick={{ fill: '#8c909f', fontSize: 10, fontFamily: 'Inter' }}
          axisLine={false}
          tickLine={false}
          width={56}
        />
        <Tooltip content={<EquityTooltip />} />
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

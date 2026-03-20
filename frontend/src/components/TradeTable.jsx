const fmtDate = (s) => {
  if (!s) return '—'
  const d = new Date(s)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

export default function TradeTable({ trades = [] }) {
  if (!trades.length) return (
    <div className="text-dim font-mono text-sm text-center py-8">No trades recorded</div>
  )

  return (
    <div className="overflow-auto">
      <table className="w-full text-xs font-mono border-collapse">
        <thead>
          <tr className="border-b border-border">
            {['Date', 'Symbol', 'Direction', 'Qty', 'Price', 'Commission'].map((h) => (
              <th key={h} className="text-left text-dim uppercase tracking-widest py-2 px-3 font-normal whitespace-nowrap">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {trades.map((t, i) => {
            const isBuy = t.direction === 'BUY'
            return (
              <tr key={i} className="border-b border-border/40 hover:bg-panel transition-colors">
                <td className="py-2 px-3 text-dim">{fmtDate(t.timestamp)}</td>
                <td className="py-2 px-3 text-text">{t.symbol}</td>
                <td className="py-2 px-3">
                  <span
                    className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                      isBuy
                        ? 'bg-accent/10 text-accent'
                        : 'bg-red/10 text-red'
                    }`}
                  >
                    {t.direction}
                  </span>
                </td>
                <td className="py-2 px-3 text-right text-text">{t.quantity}</td>
                <td className="py-2 px-3 text-right text-bright">
                  ${Number(t.price).toFixed(2)}
                </td>
                <td className="py-2 px-3 text-right text-dim">
                  ${Number(t.commission ?? 0).toFixed(4)}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

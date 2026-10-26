export default function KpiCard({ label, value, color, hot }) {
  return (
    <div className={`kpi${hot ? ' is-hot' : ''}`}>
      <div className="kpi-label">{label}</div>
      <div className="kpi-value" style={color ? { color } : undefined}>
        {value}
      </div>
    </div>
  )
}

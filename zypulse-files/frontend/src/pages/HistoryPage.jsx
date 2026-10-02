import { useState, useEffect } from 'react'
import { api } from '../api/client.js'

const FILTERS = [
  { key: 'all', label: 'All' },
  { key: 'glucose', label: 'Glucose' },
  { key: 'medication', label: 'Medication' },
  { key: 'activity', label: 'Activity' },
  { key: 'meals', label: 'Meals' },
]

function describe(record) {
  const type = record.record_type
  if (type === 'glucose_fasting' || type === 'glucose_evening') {
    const period = type === 'glucose_fasting' ? 'Fasting' : 'Evening'
    return { icon: '🩸', title: `Glucose (${period})`, detail: `${record.value_numeric} mmol/L`, sub: record.notes || '' }
  }
  if (type === 'medication_morning' || type === 'medication_evening') {
    const period = type === 'medication_morning' ? 'Morning' : 'Evening'
    return { icon: '💊', title: `Medication (${period})`, detail: record.value_text || '', sub: '' }
  }
  if (type === 'activity') {
    let meta = {}
    try { meta = JSON.parse(record.value_text || '{}') } catch { /* ignore */ }
    return { icon: '🏃', title: `Activity (${meta.type || 'activity'})`, detail: `${record.value_numeric} min`, sub: meta.location || '' }
  }
  if (type === 'note') {
    return { icon: '📝', title: 'Note', detail: record.value_text || '', sub: record.include_in_visit_summary ? 'Included in visit summary' : '' }
  }
  if (type === 'meal') {
    let meta = {}
    try { meta = JSON.parse(record.value_text || '{}') } catch { /* ignore */ }
    const items = (meta.items || []).map((it) => it.food_name).join(', ')
    const totals = meta.totals
    const detail = items || (meta.meal_type || 'meal')
    const sub = [
      meta.meal_type ? meta.meal_type.charAt(0).toUpperCase() + meta.meal_type.slice(1) : '',
      totals ? `~${totals.carbs}g carbs · ~${totals.sugar}g sugar` : '',
      record.include_in_visit_summary ? 'In visit summary' : '',
    ].filter(Boolean).join(' · ')
    return { icon: '🍽️', title: 'Meal', detail, sub }
  }
  return { icon: '•', title: type, detail: '', sub: '' }
}

export default function HistoryPage({ userId }) {
  const [category, setCategory] = useState('all')
  const [records, setRecords] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    loadHistory()
  }, [userId, category])

  const loadHistory = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await api.getHistory({ user_id: userId, category, limit: 300 })
      setRecords(data)
    } catch (err) {
      setError('Unable to load history.')
    } finally {
      setLoading(false)
    }
  }

  if (loading) return <div className="loading">Loading your history...</div>
  if (error) return <div className="error-msg">{error}</div>

  return (
    <div>
      <div className="card">
        <div className="card-title">📜 My History</div>
        <div className="filter-chips">
          {FILTERS.map((f) => (
            <button
              key={f.key}
              className={`chip ${category === f.key ? 'active' : ''}`}
              onClick={() => setCategory(f.key)}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      {records.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">🗒️</div>
          No {category === 'all' ? '' : category} entries yet.
        </div>
      ) : (
        records.map((r) => {
          const d = describe(r)
          return (
            <div key={r.record_id} className="history-item">
              <div className="history-icon">{d.icon}</div>
              <div className="history-body">
                <div className="history-title">{d.title}</div>
                <div className="history-detail">{d.detail}</div>
                {d.sub && <div className="history-sub">{d.sub}</div>}
              </div>
              <div className="history-date">{r.recorded_date}</div>
            </div>
          )
        })
      )}
    </div>
  )
}

import { useState, useEffect } from 'react'
import { api } from '../api/client.js'
import { translateText } from '../i18n.jsx'

const FILTERS = [
  { key: 'all', label: 'All' },
  { key: 'glucose', label: 'Glucose' },
  { key: 'medication', label: 'Medication' },
  { key: 'activity', label: 'Activity' },
  { key: 'meals', label: 'Meals' },
]

// Bundled demo images are public assets (/sample-photos/...). Uploaded
// originals are private: photo_ref is "photo:<key>" and is only readable
// through the ownership-checked /api/photos endpoint.
function photoHref(record, userId) {
  const ref = record.photo_ref
  if (!ref) return null
  if (ref.startsWith('photo:')) {
    return api.photoUrl(ref.slice('photo:'.length), userId)
  }
  return ref
}

function describe(record, t, userId) {
  const type = record.record_type
  if (type === 'glucose_fasting' || type === 'glucose_evening') {
    const period = t(type === 'glucose_fasting' ? 'Fasting' : 'Evening')
    return { icon: '🩸', title: `${t('Glucose')} (${period})`, detail: `${record.value_numeric} mmol/L`, sub: record.notes || '', photo: photoHref(record, userId) }
  }
  if (type === 'medication_morning' || type === 'medication_evening') {
    const period = t(type === 'medication_morning' ? 'Morning' : 'Evening')
    return { icon: '💊', title: `${t('Medication')} (${period})`, detail: record.value_text || '', sub: '', photo: photoHref(record, userId) }
  }
  if (type === 'activity') {
    let meta = {}
    try { meta = JSON.parse(record.value_text || '{}') } catch { /* ignore */ }
    return { icon: '🏃', title: `Activity (${meta.type || 'activity'})`, detail: `${record.value_numeric} min`, sub: meta.location || '', photo: photoHref(record, userId) }
  }
  if (type === 'note') {
    return { icon: '📝', title: 'Note', detail: record.value_text || '', sub: record.include_in_visit_summary ? 'Included in visit summary' : '', photo: photoHref(record, userId) }
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
    return { icon: '🍽️', title: 'Meal', detail, sub, photo: photoHref(record, userId) }
  }
  return { icon: '•', title: type, detail: '', sub: '', photo: photoHref(record, userId) }
}

function formatWhen(iso, fallbackDate) {
  if (!iso) return fallbackDate
  const then = new Date(iso)
  if (Number.isNaN(then.getTime())) return fallbackDate
  const minutes = Math.round((Date.now() - then.getTime()) / 60000)
  if (minutes >= 0 && minutes < 1) return 'Just now'
  if (minutes >= 1 && minutes < 60) return `${minutes} min ago`
  if (minutes >= 60 && minutes < 1440) return `${Math.floor(minutes / 60)}h ago`
  return new Intl.DateTimeFormat(undefined, { timeZone: 'Asia/Singapore', dateStyle: 'medium', timeStyle: 'short' }).format(then)
}

export default function HistoryPage({ userId, language }) {
  const t = (text) => translateText(language, text)
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

  if (loading) return <div className="loading">{t('Loading your history...')}</div>
  if (error) return <div className="error-msg">{error}</div>

  return (
    <div>
      <div className="card">
        <div className="card-title">📜 {t('My History')}</div>
        <div className="filter-chips">
          {FILTERS.map((f) => (
            <button
              key={f.key}
              className={`chip ${category === f.key ? 'active' : ''}`}
              onClick={() => setCategory(f.key)}
            >
              {t(f.label)}
            </button>
          ))}
        </div>
      </div>

      {records.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">🗒️</div>
          {category === 'all' ? t('No entries yet.') : `${t('No entries yet.')} (${t(category)})`}
        </div>
      ) : (
        records.map((r) => {
          const d = describe(r, t, userId)
          return (
            <div key={r.record_id} className="history-item">
              <div className="history-icon">{d.icon}</div>
              <div className="history-body">
                <div className="history-title">{d.title}</div>
                <div className="history-detail">{d.detail}</div>
                {d.sub && <div className="history-sub">{d.sub}</div>}
                {d.photo && (
                  <a className="history-photo-link" href={d.photo} target="_blank" rel="noreferrer">📷 {t('View original photo')}</a>
                )}
              </div>
              <div className="history-date" title={r.recorded_at}>{formatWhen(r.recorded_at, r.recorded_date)}</div>
            </div>
          )
        })
      )}
    </div>
  )
}

import { useState, useEffect } from 'react'
import { api } from '../api/client.js'
import { translateText } from '../i18n.jsx'

// Records whose doctor-visit note (and, for activities, the entry itself)
// can be edited from History.
const EDITABLE_TYPES = new Set([
  'glucose_fasting', 'glucose_evening',
  'medication_morning', 'medication_evening',
  'activity', 'activity_planned',
])

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
    const subParts = [
      record.notes || '',
      record.include_in_visit_summary ? t('In visit summary') : '',
    ].filter(Boolean)
    return { icon: '🩸', title: `${t('Glucose')} (${period})`, detail: `${record.value_numeric} mmol/L`, sub: subParts.join(' · '), photo: photoHref(record, userId) }
  }
  if (type === 'medication_morning' || type === 'medication_evening') {
    const period = t(type === 'medication_morning' ? 'Morning' : 'Evening')
    const subParts = [
      record.visit_note || '',
      record.include_in_visit_summary ? t('In visit summary') : '',
    ].filter(Boolean)
    return { icon: '💊', title: `${t('Medication')} (${period})`, detail: record.value_text || '', sub: subParts.join(' · '), photo: photoHref(record, userId) }
  }
  if (type === 'activity' || type === 'activity_planned') {
    let meta = {}
    try { meta = JSON.parse(record.value_text || '{}') } catch { /* ignore */ }
    const planned = type === 'activity_planned'
    const subParts = [
      meta.location || '',
      record.avg_heart_rate ? `${t('Avg heart rate')}: ${record.avg_heart_rate} bpm` : '',
      planned ? t('Planned - not counted as completed exercise') : '',
      meta.source_event_id ? `${t('From demo event')} ${meta.source_event_id}` : '',
      record.visit_note || '',
      record.include_in_visit_summary ? t('In visit summary') : '',
    ].filter(Boolean)
    return {
      icon: planned ? '📅' : '🏃',
      title: planned ? `Activity (${meta.type || 'activity'}) · ${t('Planned')}` : `Activity (${meta.type || 'activity'})`,
      detail: `${record.value_numeric} min`,
      sub: subParts.join(' · '),
      photo: photoHref(record, userId),
    }
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
  const [editing, setEditing] = useState(null)
  const [form, setForm] = useState({})
  const [actionError, setActionError] = useState(null)
  const [confirmDelete, setConfirmDelete] = useState(null)

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

  const isActivity = (record) => record.record_type === 'activity' || record.record_type === 'activity_planned'
  // Glucose and meal keep their note text in `notes`; medication and activity
  // keep it in `visit_note` because their `notes` column holds a summary.
  const noteValue = (record) => (record.record_type === 'meal' || record.record_type.startsWith('glucose')
    ? (record.notes || '')
    : (record.visit_note || ''))

  const startEdit = (record) => {
    let meta = {}
    try { meta = JSON.parse(record.value_text || '{}') } catch { /* ignore */ }
    setActionError(null)
    if (isActivity(record)) {
      setForm({
        kind: 'activity',
        activity_type: meta.type || 'walking',
        duration_min: record.value_numeric ?? '',
        location: meta.location || '',
        recorded_date: record.recorded_date,
        avg_heart_rate: record.avg_heart_rate ?? '',
        status: record.record_type === 'activity_planned' ? 'planned' : 'completed',
        note: record.visit_note || '',
        include_in_visit: Boolean(record.include_in_visit_summary),
      })
    } else {
      setForm({
        kind: 'note',
        note: noteValue(record),
        include_in_visit: Boolean(record.include_in_visit_summary),
      })
    }
    setEditing(record.record_id)
  }

  const saveEdit = async (record) => {
    setActionError(null)
    try {
      if (form.kind === 'activity') {
        const rawRate = String(form.avg_heart_rate ?? '').trim()
        let avgHeartRate = null
        if (rawRate !== '') {
          avgHeartRate = Number(rawRate)
          if (!Number.isInteger(avgHeartRate) || avgHeartRate < 20 || avgHeartRate > 250) {
            setActionError(t('Enter a whole number between 20 and 250 bpm, or leave the field empty.'))
            return
          }
        }
        await api.updateActivity(record.record_id, {
          activity_type: form.activity_type,
          duration_min: Number(form.duration_min),
          location: form.location || null,
          recorded_date: form.recorded_date,
          avg_heart_rate: avgHeartRate,
          clear_heart_rate: rawRate === '',
          status: form.status,
          visit_note: form.note.trim() || null,
          include_in_visit: form.include_in_visit,
        })
      } else {
        await api.updateVisitNote(record.record_id, {
          note: form.note.trim() || null,
          include_in_visit: form.include_in_visit,
          clear_note: !form.note.trim(),
        })
      }
      setEditing(null)
      await loadHistory()
    } catch (err) {
      setActionError(err.message || 'Unable to update entry.')
    }
  }

  const removeEntry = async (recordId) => {
    setActionError(null)
    try {
      await api.deleteActivity(recordId)
      setConfirmDelete(null)
      await loadHistory()
    } catch (err) {
      setActionError(err.message || 'Unable to delete activity.')
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
          if (editing === r.record_id) {
            if (form.kind === 'activity') {
              return (
                <div key={r.record_id} className="history-item activity-edit" data-testid="activity-edit">
                  <div style={{ flex: 1 }}>
                    <div className="form-group">
                      <label className="form-label">{t('Status')}</label>
                      <select className="form-select" value={form.status} onChange={e => setForm({ ...form, status: e.target.value })}>
                        <option value="planned">{t('Planned')}</option>
                        <option value="completed">{t('Completed')}</option>
                      </select>
                    </div>
                    <div className="form-group">
                      <label className="form-label">{t('Activity Type')}</label>
                      <select className="form-select" value={form.activity_type} onChange={e => setForm({ ...form, activity_type: e.target.value })}>
                        <option value="walking">{t('Walking')}</option><option value="exercise">{t('Exercise')}</option><option value="stretching">{t('Stretching')}</option><option value="cycling">{t('Cycling')}</option><option value="swimming">{t('Swimming')}</option><option value="group exercise">{t('Group exercise')}</option><option value="strength">{t('Strength')}</option>
                      </select>
                    </div>
                    <div className="form-group">
                      <label className="form-label">{t('Duration (minutes)')}</label>
                      <input className="form-input" type="number" min="0" max="600" value={form.duration_min} onChange={e => setForm({ ...form, duration_min: e.target.value })} />
                    </div>
                    <div className="form-group">
                      <label className="form-label">{t('Location (optional)')}</label>
                      <input className="form-input" type="text" value={form.location} onChange={e => setForm({ ...form, location: e.target.value })} />
                    </div>
                    <div className="form-group">
                      <label className="form-label">{t('Average heart rate (bpm, optional)')}</label>
                      <input className="form-input" type="number" min="20" max="250" step="1" placeholder={t('Leave empty if not measured')} value={form.avg_heart_rate} onChange={e => setForm({ ...form, avg_heart_rate: e.target.value })} />
                    </div>
                    <div className="form-group">
                      <label className="form-label">{t('Date')}</label>
                      <input className="form-input" type="date" value={form.recorded_date} onChange={e => setForm({ ...form, recorded_date: e.target.value })} />
                    </div>
                    <div className="form-group">
                      <label className="form-label">{t('Notes (optional)')}</label>
                      <textarea className="form-textarea" value={form.note} onChange={e => setForm({ ...form, note: e.target.value })} />
                    </div>
                    <label className="checkbox-row">
                      <input type="checkbox" checked={form.include_in_visit} onChange={e => setForm({ ...form, include_in_visit: e.target.checked })} />
                      {t('Include this note in visit summary for my doctor')}
                    </label>
                    {actionError && <div className="error-msg">{actionError}</div>}
                    <div style={{ display: 'flex', gap: 8 }}>
                      <button className="btn btn-primary btn-sm" onClick={() => saveEdit(r)}>{t('Save changes')}</button>
                      <button className="btn btn-secondary btn-sm" onClick={() => { setEditing(null); setActionError(null) }}>{t('Cancel')}</button>
                    </div>
                  </div>
                </div>
              )
            }
            return (
              <div key={r.record_id} className="history-item visit-note-edit" data-testid="visit-note-edit">
                <div style={{ flex: 1 }}>
                  <div className="form-group">
                    <label className="form-label">{t('Notes (optional)')}</label>
                    <textarea className="form-textarea" value={form.note} onChange={e => setForm({ ...form, note: e.target.value })} />
                  </div>
                  <label className="checkbox-row">
                    <input type="checkbox" checked={form.include_in_visit} onChange={e => setForm({ ...form, include_in_visit: e.target.checked })} />
                    {t('Include this note in visit summary for my doctor')}
                  </label>
                  {actionError && <div className="error-msg">{actionError}</div>}
                  <div style={{ display: 'flex', gap: 8 }}>
                    <button className="btn btn-primary btn-sm" onClick={() => saveEdit(r)}>{t('Save changes')}</button>
                    <button className="btn btn-secondary btn-sm" onClick={() => { setEditing(null); setActionError(null) }}>{t('Cancel')}</button>
                  </div>
                </div>
              </div>
            )
          }
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
                {EDITABLE_TYPES.has(r.record_type) && (
                  <div className="history-actions">
                    <button className="btn-link" onClick={() => startEdit(r)}>✎ {t('Edit')}</button>
                    {isActivity(r) && (confirmDelete === r.record_id ? (
                      <>
                        <button className="btn-link danger" onClick={() => removeEntry(r.record_id)}>{t('Confirm delete')}</button>
                        <button className="btn-link" onClick={() => setConfirmDelete(null)}>{t('Cancel')}</button>
                      </>
                    ) : (
                      <button className="btn-link" onClick={() => setConfirmDelete(r.record_id)}>🗑 {t('Delete')}</button>
                    ))}
                  </div>
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

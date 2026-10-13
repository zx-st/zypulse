import { useState, useEffect, useCallback } from 'react'
import { api } from '../api/client.js'
import { translateText } from '../i18n.jsx'
import Healthy365Handoff from './Healthy365Handoff.jsx'

const DEMO_NOTICE = 'Synthetic demo catalogue - not real Healthy 365 activities and not bookable.'
const HANDOFF_NOTICE = 'Demo simulation only. No real Healthy 365 registration or data transfer occurs.'

function formatWhen(event) {
  const date = `${event.date} ${event.start_time}`
  return `${event.weekday} ${date}`
}

function durationLabel(event, t) {
  return event.duration_min ? `${event.duration_min} ${t('min')}` : t('Duration not specified')
}

export default function Healthy365Section({ userId, language, onAddToActivityLog }) {
  const t = (text) => translateText(language, text)
  const [mode, setMode] = useState('recommended')
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [selected, setSelected] = useState(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [handoffOpen, setHandoffOpen] = useState(false)
  const [toast, setToast] = useState(null)

  const load = useCallback(async (nextMode) => {
    setLoading(true)
    setError(null)
    try {
      const result = await api.getHealthy365Events({ user_id: userId, mode: nextMode, limit: 20 })
      setData(result)
    } catch (err) {
      setError(err.message || 'Unable to load Healthy 365 demo activities.')
    } finally {
      setLoading(false)
    }
  }, [userId])

  useEffect(() => { load(mode) }, [load, mode])

  const switchMode = (next) => {
    setMode(next)
    setSelected(null)
    setHandoffOpen(false)
    setToast(null)
  }

  const openDetail = async (event) => {
    setDetailLoading(true)
    setToast(null)
    try {
      const detail = await api.getHealthy365Event(event.event_id, userId)
      setSelected(detail)
    } catch {
      setSelected(event)
    } finally {
      setDetailLoading(false)
    }
  }

  const events = data?.events || []

  if (handoffOpen && selected) {
    return (
      <Healthy365Handoff
        event={selected}
        language={language}
        userId={userId}
        onBack={() => { setHandoffOpen(false); setToast(null) }}
        onAddToActivityLog={onAddToActivityLog}
      />
    )
  }

  if (selected) {
    const logged = selected.activity_log_entries || []
    return (
      <div className="card h365-card-panel">
        <div className="h365-demo-banner">🧪 {t('DEMO / SYNTHETIC')} — {t(DEMO_NOTICE)}</div>
        <div className="card-title">{selected.title}</div>
        <div className="h365-meta">{t('Activity type')}: {selected.activity_type}</div>
        <div className="h365-meta">{t('General location')}: {selected.location_area}</div>
        {selected.venue_hint && <div className="h365-meta">{t('Venue area')}: {selected.venue_hint}</div>}
        <div className="h365-meta">📅 {formatWhen(selected)}</div>
        <div className="h365-meta">⏱ {durationLabel(selected, t)}</div>
        <div className="h365-meta">{t('Experience level')}: {selected.experience_level ? selected.experience_level : t('Not specified')}</div>
        <div className="h365-meta">{t('Demo registration status')}: {selected.demo_registration_status}</div>
        <div className="h365-meta">{t('Event ID')}: <code>{selected.event_id}</code></div>
        <div className="h365-desc">{selected.description}</div>
        {selected.already_registered && (
          <div className="h365-note">{t('A demo registration for this event is already recorded locally.')}</div>
        )}
        {logged.length > 0 && (
          <div className="h365-note">
            {t('Already in your Activity Log')} ({logged.map((r) => (r.record_type === 'activity_planned' ? t('Planned') : t('Completed'))).join(', ')})
          </div>
        )}

        <div className="h365-detail-actions">
          <button className="btn btn-primary btn-sm" onClick={() => setHandoffOpen(true)}>
            {t('Continue to Healthy 365 (Demo)')}
          </button>
          <button className="btn btn-secondary btn-sm" onClick={() => { setSelected(null); setToast(null) }}>
            {t('Back to list')}
          </button>
        </div>

        <div className="h365-add-block">
          <div className="h365-add-title">{t('Add to Activity Log')}</div>
          <div className="h365-add-hint">{t('You can edit the details before saving.')}</div>
          <div className="h365-add-buttons">
            <button className="btn btn-secondary btn-sm" onClick={() => onAddToActivityLog(selected, 'planned')}>
              {t('Planned')}
            </button>
            <button className="btn btn-primary btn-sm" onClick={() => onAddToActivityLog(selected, 'completed')}>
              {t('Completed')}
            </button>
          </div>
        </div>
        {toast && <div className="h365-toast">{toast}</div>}
      </div>
    )
  }

  return (
    <div className="card">
      <div className="card-title">🤝 {t('Healthy 365 Activities')} <span className="badge badge-warn">{t('DEMO')}</span></div>
      <div className="h365-demo-banner">🧪 {t('DEMO / SYNTHETIC')} — {t(DEMO_NOTICE)}</div>
      <div className="h365-hint">
        {t('Synthetic Healthy 365-style activities for demonstration. Ranking is deterministic and based only on your stored preferences.')}
      </div>

      <div className="filter-chips h365-mode-chips">
        <button className={`chip ${mode === 'recommended' ? 'active' : ''}`} onClick={() => switchMode('recommended')}>
          {t('Recommended for You')}
        </button>
        <button className={`chip ${mode === 'nearest' ? 'active' : ''}`} onClick={() => switchMode('nearest')}>
          {t('Nearest First')}
        </button>
      </div>

      {loading && <div className="loading">{t('Loading demo activities...')}</div>}
      {error && <div className="error-msg">{error}</div>}

      {!loading && !error && data && (
        <>
          <div className="h365-explain">
            {mode === 'recommended'
              ? (data.personalisation?.available
                ? `✨ ${data.personalisation.explanation}`
                : `ℹ️ ${data.notice}`)
              : `📍 ${data.distance_policy}`}
          </div>
          {mode === 'nearest' && <div className="h365-explain h365-explain-sub">{data.notice}</div>}

          {events.length === 0 ? (
            <div className="empty-state">{t('No demo activities available.')}</div>
          ) : (
            events.map((event) => (
              <div key={event.event_id} className="activity-card h365-event">
                <div className="activity-content">
                  <div className="activity-title">
                    {event.title} <span className="badge badge-warn">{t('DEMO')}</span>
                  </div>
                  <div className="activity-meta">
                    {event.activity_type} · {event.location_area} · {formatWhen(event)} · {durationLabel(event, t)}
                  </div>
                  <div className="activity-desc">{event.description}</div>
                  <div className="h365-tags">
                    <span className="badge">{t('Experience level')}: {event.experience_level ? event.experience_level : t('Not specified')}</span>
                    <span className="badge badge-info">{t('Demo registration status')}: {event.demo_registration_status}</span>
                  </div>
                  {(event.match_reasons || []).length > 0 && (
                    <div className="h365-tags">
                      {event.match_reasons.map((reason) => (
                        <span className="badge badge-info h365-reason" key={reason}>{t(reason)}</span>
                      ))}
                    </div>
                  )}
                  <div className="h365-card-actions">
                    <button className="btn btn-secondary btn-sm" onClick={() => openDetail(event)} disabled={detailLoading}>
                      {t('View details')}
                    </button>
                    <button className="btn btn-primary btn-sm" onClick={() => onAddToActivityLog(event, 'planned')}>
                      {t('Add to Activity Log')}
                    </button>
                  </div>
                </div>
              </div>
            ))
          )}
          <div className="h365-footnote">{HANDOFF_NOTICE}</div>
        </>
      )}
    </div>
  )
}

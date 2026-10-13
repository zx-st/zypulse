import { useState } from 'react'
import { api } from '../api/client.js'
import { translateText } from '../i18n.jsx'

const SIM_NOTICE = 'Demo simulation only. No real Healthy 365 registration or data transfer occurs.'
const REGISTRATION_LINE = 'Demo registration recorded locally — no actual registration was made.'

export default function Healthy365Handoff({ event, language, userId, onBack, onAddToActivityLog }) {
  const t = (text) => translateText(language, text)
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  const register = async () => {
    setBusy(true)
    setError(null)
    setResult(null)
    try {
      const response = await api.registerHealthy365({ user_id: userId, event_id: event.event_id })
      setResult(response)
    } catch (err) {
      setError(err.message || 'Demo registration failed.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="h365-handoff" data-testid="h365-handoff">
      <div className="h365-handoff-ribbon">{t('SIMULATED EXTERNAL APP — NOT THE REAL HEALTHY 365')}</div>
      <div className="h365-handoff-frame">
        <div className="h365-handoff-appbar">
          <span className="h365-handoff-dot" /> <span>{t('Healthy 365 — simulated demo screen')}</span>
        </div>

        <div className="h365-handoff-body">
          <div className="h365-handoff-title">{event.title}</div>
          <div className="h365-handoff-row"><span>{t('Activity type')}</span><b>{event.activity_type}</b></div>
          <div className="h365-handoff-row"><span>{t('General location')}</span><b>{event.location_area}</b></div>
          <div className="h365-handoff-row"><span>{t('Date / time')}</span><b>{event.weekday} {event.date} {event.start_time}</b></div>
          <div className="h365-handoff-row"><span>{t('Duration')}</span><b>{event.duration_min ? `${event.duration_min} ${t('min')}` : t('Duration not specified')}</b></div>
          <div className="h365-handoff-row"><span>{t('Experience level')}</span><b>{event.experience_level || t('Not specified')}</b></div>
          <div className="h365-handoff-row"><span>{t('Demo registration status')}</span><b>{event.demo_registration_status}</b></div>
          <div className="h365-handoff-row"><span>{t('Event ID')}</span><b><code>{event.event_id}</code></b></div>
          <div className="h365-handoff-desc">{event.description}</div>

          <div className="h365-handoff-warning">
            <div>⚠️ {SIM_NOTICE}</div>
            <div>{t('No Singpass, NRIC or health information is requested. Nothing is shared externally.')}</div>
          </div>

          {!result && (
            <button className="btn btn-primary h365-handoff-cta" onClick={register} disabled={busy}>
              {busy ? t('Recording demo...') : t('Register (Demo)')}
            </button>
          )}
          {error && <div className="error-msg">{error}</div>}
          {result && (
            <div className="h365-handoff-result" data-testid="h365-register-result">
              <div className="h365-handoff-result-title">
                {result.duplicate ? t('Already recorded as a demo registration') : t('Demo registration recorded')}
              </div>
              <div className="h365-handoff-conf">{t(REGISTRATION_LINE)}</div>
              {result.confirmation_id && (
                <div className="h365-handoff-conf">{t('Demo confirmation')}: <code>{result.confirmation_id}</code></div>
              )}
              <div className="h365-handoff-conf-note">
                {t('This is a local demo record only. It is not attendance and is not sent to Healthy 365.')}
              </div>
            </div>
          )}

          <div className="h365-add-block">
            <div className="h365-add-title">{t('Add to Activity Log')}</div>
            <div className="h365-add-hint">{t('You can edit the details before saving.')}</div>
            <div className="h365-add-buttons">
              <button className="btn btn-secondary btn-sm" onClick={() => onAddToActivityLog(event, 'planned')}>
                {t('Planned')}
              </button>
              <button className="btn btn-primary btn-sm" onClick={() => onAddToActivityLog(event, 'completed')}>
                {t('Completed')}
              </button>
            </div>
          </div>

          <button className="btn btn-secondary h365-handoff-back" onClick={onBack}>
            ← {t('Return to ZyPulse')}
          </button>
        </div>
      </div>
      <div className="h365-handoff-footnote">{SIM_NOTICE}</div>
    </div>
  )
}

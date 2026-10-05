import { useState, useEffect } from 'react'
import { api } from '../api/client.js'
import { translateText } from '../i18n.jsx'

export default function ActivitiesPage({ userId, language }) {
  const t = (text) => translateText(language, text)
  const [activities, setActivities] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [filterType, setFilterType] = useState('')
  const [showConsent, setShowConsent] = useState(null)
  const [consentResult, setConsentResult] = useState(null)

  useEffect(() => {
    loadActivities()
  }, [userId])

  const loadActivities = async () => {
    setLoading(true)
    setError(null)
    try {
      const params = { user_id: userId }
      if (filterType) params.activity_type = filterType
      const result = await api.searchActivities(params)
      setActivities(result)
    } catch (err) {
      setError('Unable to load activities.')
    } finally {
      setLoading(false)
    }
  }

  const handleRegister = (activity) => {
    setShowConsent(activity)
    setConsentResult(null)
  }

  const handleConfirmRegistration = () => {
    // Simulated registration - no data is sent anywhere
    const confirmationId = 'SIM-' + Date.now().toString().slice(-6)
    setConsentResult({
      success: true,
      confirmationId: confirmationId,
      message: 'Registration simulated. No information has been sent to HPB or Healthy 365.',
      simulated: true,
    })
  }

  const handleCancel = () => {
    setShowConsent(null)
    setConsentResult(null)
  }

  const statusBadge = (status) => {
    const map = { open: 'badge-open', waitlist: 'badge-waitlist', closed: 'badge-closed' }
    return map[status] || 'badge-closed'
  }

  const statusLabel = (status) => {
    const map = { open: 'Open', waitlist: 'Waitlist', closed: 'Closed' }
    return map[status] || status
  }

  if (loading) return <div className="loading">{t('Loading activities...')}</div>
  if (error) return <div className="error-msg">{error}</div>

  return (
    <div>
      <div className="card">
        <div className="card-title">🤝 {t('Community Activities')}</div>
        <div style={{ fontSize: '0.85rem', color: 'var(--gray)', marginBottom: 12 }}>
          {t('Find health activities near you. All activities are from a demo catalogue.')}
        </div>

        <div className="form-group">
          <label className="form-label">{t('Filter by type')}</label>
          <select className="form-select" value={filterType} onChange={e => setFilterType(e.target.value)}>
            <option value="">{t('All types')}</option><option value="walking">{t('Walking')}</option><option value="exercise">{t('Exercise')}</option><option value="education">{t('Education')}</option><option value="mindfulness">{t('Mindfulness')}</option><option value="support">{t('Support')}</option>
          </select>
        </div>
        <button className="btn btn-secondary" onClick={loadActivities} style={{ marginBottom: 12 }}>
          {t('Search')}
        </button>
      </div>

      <span className="simulated-tag" style={{ display: 'block', textAlign: 'center', marginBottom: 12 }}>
        DEMO/SYNTHETIC - Not live Healthy 365 listings
      </span>

      {activities.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">🔍</div>
          {t('No activities found. Try a different filter.')}
        </div>
      ) : (
        activities.map(activity => (
          <div key={activity.activity_id} className="activity-card">
            <div className="activity-title">{activity.title}</div>
            <div className="activity-meta">
              {activity.organiser} • {activity.location}
            </div>
            <div className="activity-meta">
              {new Date(activity.datetime).toLocaleDateString('en-SG', { weekday: 'short', day: 'numeric', month: 'short' })} • {activity.duration_min} min • {activity.intensity} intensity
            </div>
            <div className="activity-desc">{activity.description}</div>
            <div style={{ marginBottom: 8 }}>
              <span className={`activity-badge ${statusBadge(activity.registration_status)}`}>
                {t(statusLabel(activity.registration_status))}
              </span>
              {activity.accessibility === 'wheelchair_accessible' && (
                <span className="activity-badge badge-open">♿ {t('Accessible')}</span>
              )}
            </div>
            {activity.registration_status !== 'closed' && (
              <button className="btn btn-primary" onClick={() => handleRegister(activity)}>
                {t('Register (Simulated)')}
              </button>
            )}
          </div>
        ))
      )}

      {/* Consent Modal - 5-step gate */}
      {showConsent && (
        <div className="consent-overlay" onClick={handleCancel}>
          <div className="consent-modal" onClick={e => e.stopPropagation()}>
            {!consentResult ? (
              <>
                <div className="card-title" style={{ marginBottom: 16 }}>📋 Registration Consent</div>

                <div style={{ marginBottom: 16, fontSize: '0.85rem' }}>
                  <strong>Activity:</strong> {showConsent.title}
                </div>

                <div style={{ marginBottom: 16, fontSize: '0.85rem' }}>
                  <strong>Step 1 of 5:</strong> Review the information that would be shared.
                </div>

                <div style={{ background: 'var(--gray-light)', borderRadius: 8, padding: 12, marginBottom: 16 }}>
                  <div className="consent-field">
                    <span style={{ fontSize: '0.85rem' }}>Name</span>
                    <span style={{ fontSize: '0.85rem', fontWeight: 600 }}>Mr Tan</span>
                  </div>
                  <div className="consent-field">
                    <span style={{ fontSize: '0.85rem' }}>General area</span>
                    <span style={{ fontSize: '0.85rem', fontWeight: 600 }}>East Singapore (Tampines)</span>
                  </div>
                  <div className="consent-field">
                    <span style={{ fontSize: '0.85rem' }}>Activity interest</span>
                    <span style={{ fontSize: '0.85rem', fontWeight: 600 }}>{showConsent.type}</span>
                  </div>
                </div>

                <div style={{ marginBottom: 16, fontSize: '0.85rem', color: 'var(--gray)' }}>
                  <strong>Purpose:</strong> To register your interest in this activity with the organiser.
                  <br /><br />
                  <span style={{ color: 'var(--red)', fontWeight: 600 }}>
                    ⚠️ SIMULATED: No information is sent to HPB or Healthy 365. No Healthpoints are awarded.
                  </span>
                </div>

                <div style={{ display: 'flex', gap: 8 }}>
                  <button className="btn btn-secondary" onClick={handleCancel} style={{ flex: 1 }}>
                    Cancel
                  </button>
                  <button className="btn btn-primary" onClick={handleConfirmRegistration} style={{ flex: 1 }}>
                    Confirm
                  </button>
                </div>
              </>
            ) : (
              <>
                <div className="card-title" style={{ marginBottom: 16 }}>✅ Registration Complete</div>
                <div className="success-msg" style={{ marginBottom: 16 }}>
                  {consentResult.message}
                </div>
                <div style={{ fontSize: '0.85rem', marginBottom: 16 }}>
                  <strong>Confirmation ID:</strong> {consentResult.confirmationId}
                  <br />
                  <strong>Activity:</strong> {showConsent.title}
                </div>
                <div style={{ fontSize: '0.8rem', color: 'var(--gray)', marginBottom: 16, fontStyle: 'italic' }}>
                  This is a simulated confirmation. To register for real activities, please use the official Healthy 365 app.
                </div>
                <button className="btn btn-primary" onClick={handleCancel}>
                  Done
                </button>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

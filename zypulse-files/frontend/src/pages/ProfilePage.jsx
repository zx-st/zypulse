import { useState, useEffect } from 'react'
import { api } from '../api/client.js'
import { LANGUAGES, useTranslation } from '../i18n.jsx'

// Fictional Mr Tan prototype defaults (no NRIC, no Singpass, no full address)
const MR_TAN_DEFAULTS = {
  display_name: 'Mr Tan',
  location_area: 'East Singapore (Tampines)',
  contact_email: '',
  contact_phone: '',
  language: 'en',
  goals: '',
  barriers: '',
  activity_types: '',
  availability: '',
  accessibility_json: { larger_text: false },
}

export default function ProfilePage({ userId, language, setLanguage, setPage, setLargerText }) {
  const t = useTranslation(language)
  const [form, setForm] = useState({ ...MR_TAN_DEFAULTS })
  const [accessibility, setAccessibility] = useState(MR_TAN_DEFAULTS.accessibility_json)
  const [loaded, setLoaded] = useState(false)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState(null)
  const [signedOut, setSignedOut] = useState(false)

  useEffect(() => {
    loadProfile()
  }, [userId])

  const loadProfile = async () => {
    try {
      const prefs = await api.getPreferences(userId)
      setForm({
        display_name: prefs.display_name || MR_TAN_DEFAULTS.display_name,
        location_area: prefs.location_area || MR_TAN_DEFAULTS.location_area,
        contact_email: prefs.contact_email || '',
        contact_phone: prefs.contact_phone || '',
        language: prefs.language || 'en',
        goals: (prefs.goals || []).join('\n'),
        barriers: (prefs.barriers || []).join('\n'),
        activity_types: (prefs.activity_types || []).join(', '),
        availability: (prefs.availability || []).join(', '),
        accessibility_json: prefs.accessibility_json || MR_TAN_DEFAULTS.accessibility_json,
      })
      const savedAccessibility = { larger_text: Boolean(prefs.accessibility_json?.larger_text) }
      setAccessibility(savedAccessibility)
      setLargerText(savedAccessibility.larger_text)
    } catch (err) {
      // Use fictional defaults if no preferences stored yet
      setForm({ ...MR_TAN_DEFAULTS })
      setAccessibility(MR_TAN_DEFAULTS.accessibility_json)
      setLargerText(false)
    } finally {
      setLoaded(true)
    }
  }

  const handleLanguage = async (code) => {
    setLanguage(code) // immediate UI shortcut
    setForm((f) => ({ ...f, language: code }))
    try {
      await api.updatePreferences(userId, { language: code })
    } catch (err) {
      setError('Could not save language preference.')
    }
  }

  const handleAccessibility = async (key) => {
    const next = { ...accessibility, [key]: !accessibility[key] }
    setAccessibility(next)
    if (key === 'larger_text') setLargerText(next.larger_text)
    setForm((f) => ({ ...f, accessibility_json: next }))
    try {
      await api.updatePreferences(userId, { accessibility_json: next })
    } catch (err) {
      setError('Could not save accessibility setting.')
    }
  }

  const handleSave = async (e) => {
    e.preventDefault()
    setSaving(true)
    setSaved(false)
    setError(null)
    try {
      await api.updatePreferences(userId, {
        display_name: form.display_name,
        location_area: form.location_area,
        contact_email: form.contact_email || null,
        contact_phone: form.contact_phone || null,
        language: form.language,
        goals: listFromText(form.goals),
        barriers: listFromText(form.barriers),
        activity_types: listFromText(form.activity_types),
        availability: listFromText(form.availability),
        accessibility_json: accessibility,
      })
      setSaved(true)
    } catch (err) {
      setError(err.message || 'Could not save profile.')
    } finally {
      setSaving(false)
    }
  }

  if (signedOut) {
    return (
      <div className="card">
        <div className="card-title">👋 {t('signedOut')}</div>
        <p style={{ fontSize: '0.9rem', color: 'var(--gray-dark)', marginBottom: 12 }}>
          {t('profileSafety')}
        </p>
        <button className="btn btn-primary" onClick={() => setSignedOut(false)}>
          {t('returnProfile')}
        </button>
      </div>
    )
  }

  return (
    <div>
      <div className="card">
        <div className="card-title">👤 {t('profileTitle')}</div>
        <div className="profile-content">
          <form onSubmit={handleSave}>
            <div className="form-group">
              <label className="form-label">{t('displayName')}</label>
              <input
                className="form-input"
                type="text"
                value={form.display_name}
                onChange={(e) => setForm({ ...form, display_name: e.target.value })}
                maxLength={100}
              />
            </div>

            <div className="form-group">
              <label className="form-label">{t('location')}</label>
              <input
                className="form-input"
                type="text"
                value={form.location_area}
                onChange={(e) => setForm({ ...form, location_area: e.target.value })}
                placeholder="e.g. East Singapore (Tampines)"
              />
            </div>

            <div className="form-group">
              <label className="form-label">{t('email')}</label>
              <input
                className="form-input"
                type="email"
                value={form.contact_email}
                onChange={(e) => setForm({ ...form, contact_email: e.target.value })}
                placeholder="optional"
              />
            </div>

            <div className="form-group">
              <label className="form-label">{t('phone')}</label>
              <input
                className="form-input"
                type="tel"
                value={form.contact_phone}
                onChange={(e) => setForm({ ...form, contact_phone: e.target.value })}
                placeholder="optional"
              />
            </div>

            <div className="form-group">
              <label className="form-label">{t('preferredLanguage')}</label>
              <select
                className="form-select"
                value={form.language}
                onChange={(e) => handleLanguage(e.target.value)}
              >
                {LANGUAGES.map((l) => (
                  <option key={l.code} value={l.code}>{l.label}</option>
                ))}
              </select>
              <div style={{ fontSize: '0.75rem', color: 'var(--gray)', marginTop: 4 }}>
                {t('languageHelp')}
              </div>
            </div>

            <div className="form-group">
              <label className="form-label">{t('goals')}</label>
              <textarea className="form-textarea" value={form.goals} onChange={(e) => setForm({ ...form, goals: e.target.value })} placeholder="One goal per line, e.g. Walk regularly" />
            </div>
            <div className="form-group">
              <label className="form-label">{t('barriers')}</label>
              <textarea className="form-textarea" value={form.barriers} onChange={(e) => setForm({ ...form, barriers: e.target.value })} placeholder="One item per line, e.g. Busy work schedule" />
            </div>
            <div className="form-group">
              <label className="form-label">{t('activities')}</label>
              <input className="form-input" value={form.activity_types} onChange={(e) => setForm({ ...form, activity_types: e.target.value })} placeholder="e.g. walking, parks" />
            </div>
            <div className="form-group">
              <label className="form-label">{t('availability')}</label>
              <input className="form-input" value={form.availability} onChange={(e) => setForm({ ...form, availability: e.target.value })} placeholder="e.g. weekday evenings, weekend mornings" />
            </div>

            <div className="form-group">
              <label className="form-label">{t('accessibility')}</label>
              <div className="toggle-row">
                <span>{t('largerText')}</span>
                <button type="button" className={`toggle ${accessibility.larger_text ? 'on' : ''}`} onClick={() => handleAccessibility('larger_text')}>
                  {accessibility.larger_text ? t('on') : t('off')}
                </button>
              </div>
            </div>

            {saved && <div className="success-msg">{t('profileSaved')}</div>}
            {error && <div className="error-msg">{error}</div>}

            <button type="submit" className="btn btn-primary" disabled={saving}>
              {saving ? t('saving') : t('saveProfile')}
            </button>
          </form>
        </div>
      </div>

      <div className="card">
        <div className="card-title">🔗 {t('quickLinks')}</div>
        <button className="btn btn-secondary" style={{ marginBottom: 8 }} onClick={() => setPage('notifications')}>
          🔔 {t('reminders')}
        </button>
        <button className="btn btn-secondary" onClick={() => setPage('summary')}>
          🩺 {t('healthSummary')}
        </button>
      </div>

      <div className="card">
        <div className="card-title">❓ {t('help')}</div>
        <div style={{ fontSize: '0.85rem', color: 'var(--gray-dark)', lineHeight: 1.7 }}>
          <p><strong>Is this a medical device?</strong> No. ZyPulse is a self-care support prototype. Always consult your doctor for medical advice.</p>
          <p><strong>Where is my data?</strong> All data shown is synthetic demo data for Mr Tan. Nothing is sent to HPB or Healthy 365.</p>
          <p><strong>Can ZyPulse change my medication?</strong> No. It never diagnoses or recommends treatment changes.</p>
        </div>
      </div>

      <div className="card">
        <button className="btn btn-danger" onClick={() => setSignedOut(true)}>
          {t('signOut')}
        </button>
        <div style={{ fontSize: '0.75rem', color: 'var(--gray)', marginTop: 6, textAlign: 'center' }}>
          {t('signOutNote')}
        </div>
      </div>
    </div>
  )
}

function listFromText(value) {
  return value.split(/[\n,]/).map(item => item.trim()).filter(Boolean)
}

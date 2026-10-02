import { useState, useEffect } from 'react'
import { api } from '../api/client.js'

// Fictional Mr Tan prototype defaults (no NRIC, no Singpass, no full address)
const MR_TAN_DEFAULTS = {
  display_name: 'Mr Tan',
  location_area: 'East Singapore (Tampines)',
  contact_email: '',
  contact_phone: '',
  language: 'en',
  accessibility_json: { larger_text: false, reduced_motion: false, high_contrast: false },
}

const LANGUAGES = [
  { code: 'en', label: 'English' },
  { code: 'zh', label: '中文' },
  { code: 'ms', label: 'Bahasa Melayu' },
  { code: 'ta', label: 'தமிழ்' },
]

export default function ProfilePage({ userId, language, setLanguage, setPage }) {
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
        accessibility_json: prefs.accessibility_json || MR_TAN_DEFAULTS.accessibility_json,
      })
      setAccessibility(prefs.accessibility_json || MR_TAN_DEFAULTS.accessibility_json)
    } catch (err) {
      // Use fictional defaults if no preferences stored yet
      setForm({ ...MR_TAN_DEFAULTS })
      setAccessibility(MR_TAN_DEFAULTS.accessibility_json)
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
        accessibility_json: accessibility,
      })
      setSaved(true)
    } catch (err) {
      setError(err.message || 'Could not save profile.')
    } finally {
      setSaving(false)
    }
  }

  // Apply larger-text accessibility locally within this page only (no global redesign)
  const contentClass = `profile-content${accessibility.larger_text ? ' a11y-large' : ''}`

  if (signedOut) {
    return (
      <div className="card">
        <div className="card-title">👋 Signed out (prototype)</div>
        <p style={{ fontSize: '0.9rem', color: 'var(--gray-dark)', marginBottom: 12 }}>
          This is a self-care prototype. No account data leaves your device in this demo.
        </p>
        <button className="btn btn-primary" onClick={() => setSignedOut(false)}>
          Return to Profile
        </button>
      </div>
    )
  }

  return (
    <div>
      <div className="card">
        <div className="card-title">👤 Profile</div>
        <div className={contentClass}>
          <form onSubmit={handleSave}>
            <div className="form-group">
              <label className="form-label">Preferred / display name</label>
              <input
                className="form-input"
                type="text"
                value={form.display_name}
                onChange={(e) => setForm({ ...form, display_name: e.target.value })}
                maxLength={100}
              />
            </div>

            <div className="form-group">
              <label className="form-label">General location</label>
              <input
                className="form-input"
                type="text"
                value={form.location_area}
                onChange={(e) => setForm({ ...form, location_area: e.target.value })}
                placeholder="e.g. East Singapore (Tampines)"
              />
            </div>

            <div className="form-group">
              <label className="form-label">Contact email (optional)</label>
              <input
                className="form-input"
                type="email"
                value={form.contact_email}
                onChange={(e) => setForm({ ...form, contact_email: e.target.value })}
                placeholder="optional"
              />
            </div>

            <div className="form-group">
              <label className="form-label">Contact phone (optional)</label>
              <input
                className="form-input"
                type="tel"
                value={form.contact_phone}
                onChange={(e) => setForm({ ...form, contact_phone: e.target.value })}
                placeholder="optional"
              />
            </div>

            <div className="form-group">
              <label className="form-label">Preferred language</label>
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
                You can also switch language any time from the top-right shortcut.
              </div>
            </div>

            <div className="form-group">
              <label className="form-label">Accessibility / settings</label>
              <div className="toggle-row">
                <span>Larger text</span>
                <button type="button" className={`toggle ${accessibility.larger_text ? 'on' : ''}`} onClick={() => handleAccessibility('larger_text')}>
                  {accessibility.larger_text ? 'On' : 'Off'}
                </button>
              </div>
              <div className="toggle-row">
                <span>Reduced motion</span>
                <button type="button" className={`toggle ${accessibility.reduced_motion ? 'on' : ''}`} onClick={() => handleAccessibility('reduced_motion')}>
                  {accessibility.reduced_motion ? 'On' : 'Off'}
                </button>
              </div>
              <div className="toggle-row">
                <span>High contrast</span>
                <button type="button" className={`toggle ${accessibility.high_contrast ? 'on' : ''}`} onClick={() => handleAccessibility('high_contrast')}>
                  {accessibility.high_contrast ? 'On' : 'Off'}
                </button>
              </div>
            </div>

            {saved && <div className="success-msg">Profile saved.</div>}
            {error && <div className="error-msg">{error}</div>}

            <button type="submit" className="btn btn-primary" disabled={saving}>
              {saving ? 'Saving...' : 'Save Profile'}
            </button>
          </form>
        </div>
      </div>

      <div className="card">
        <div className="card-title">🔗 Quick links</div>
        <button className="btn btn-secondary" style={{ marginBottom: 8 }} onClick={() => setPage('notifications')}>
          🔔 Notifications &amp; reminders
        </button>
        <button className="btn btn-secondary" onClick={() => setPage('summary')}>
          🩺 Health Summary &amp; Notes for Doctor
        </button>
      </div>

      <div className="card">
        <div className="card-title">❓ Help</div>
        <div style={{ fontSize: '0.85rem', color: 'var(--gray-dark)', lineHeight: 1.7 }}>
          <p><strong>Is this a medical device?</strong> No. ZyPulse is a self-care support prototype. Always consult your doctor for medical advice.</p>
          <p><strong>Where is my data?</strong> All data shown is synthetic demo data for Mr Tan. Nothing is sent to HPB or Healthy 365.</p>
          <p><strong>Can ZyPulse change my medication?</strong> No. It never diagnoses or recommends treatment changes.</p>
        </div>
      </div>

      <div className="card">
        <button className="btn btn-danger" onClick={() => setSignedOut(true)}>
          Sign out
        </button>
        <div style={{ fontSize: '0.75rem', color: 'var(--gray)', marginTop: 6, textAlign: 'center' }}>
          Prototype only - no account is actually closed.
        </div>
      </div>
    </div>
  )
}

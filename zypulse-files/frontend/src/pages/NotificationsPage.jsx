import { useState, useEffect } from 'react'
import { api } from '../api/client.js'

// Example prototype reminders. These are NOT medical advice and contain no dosing guidance.
const REMINDER_DEFS = [
  {
    key: 'medication',
    icon: '💊',
    label: 'Scheduled medication',
    example: 'Time for your scheduled medication. (Reminder only - no dosing advice.)',
    defaultTime: '08:00',
  },
  {
    key: 'meal_logging',
    icon: '🍽️',
    label: 'Meal / logging routine',
    example: "Don't forget to log today's meals and glucose readings.",
    defaultTime: '12:30',
  },
  {
    key: 'planned_activity',
    icon: '🏃',
    label: 'Planned activity',
    example: 'Time for your planned walk or activity. Stay hydrated!',
    defaultTime: '17:30',
  },
]

const emptySettings = () =>
  REMINDER_DEFS.reduce((acc, r) => {
    acc[r.key] = { enabled: true, time: r.defaultTime }
    return acc
  }, {})

export default function NotificationsPage({ userId }) {
  const [settings, setSettings] = useState(emptySettings())
  const [loaded, setLoaded] = useState(false)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    loadSettings()
  }, [userId])

  const loadSettings = async () => {
    try {
      const prefs = await api.getPreferences(userId)
      if (prefs.reminder_settings) {
        // Merge with defaults so newly added keys are present
        const merged = emptySettings()
        for (const r of REMINDER_DEFS) {
          if (prefs.reminder_settings[r.key]) merged[r.key] = prefs.reminder_settings[r.key]
        }
        setSettings(merged)
      }
    } catch (err) {
      setSettings(emptySettings())
    } finally {
      setLoaded(true)
    }
  }

  const toggle = (key) => {
    setSettings((s) => ({ ...s, [key]: { ...s[key], enabled: !s[key].enabled } }))
    setSaved(false)
  }

  const setTime = (key, time) => {
    setSettings((s) => ({ ...s, [key]: { ...s[key], time } }))
    setSaved(false)
  }

  const handleSave = async () => {
    setSaving(true)
    setSaved(false)
    setError(null)
    try {
      await api.updatePreferences(userId, { reminder_settings: settings })
      setSaved(true)
    } catch (err) {
      setError(err.message || 'Could not save reminders.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div>
      <div className="card">
        <div className="card-title">🔔 Notifications</div>
        <div style={{ fontSize: '0.85rem', color: 'var(--gray)', marginBottom: 12 }}>
          Prototype reminders. These do not send real notifications and contain no medical or dosing advice.
        </div>

        {REMINDER_DEFS.map((r) => {
          const cfg = settings[r.key] || { enabled: true, time: r.defaultTime }
          return (
            <div key={r.key} className="notif-card">
              <div className="notif-head">
                <span className="notif-icon">{r.icon}</span>
                <span className="notif-label">{r.label}</span>
                <button type="button" className={`toggle ${cfg.enabled ? 'on' : ''}`} onClick={() => toggle(r.key)}>
                  {cfg.enabled ? 'On' : 'Off'}
                </button>
              </div>
              <div className="notif-example">{r.example}</div>
              <div className="notif-time">
                <label className="form-label">Remind at</label>
                <input
                  className="form-input"
                  type="time"
                  value={cfg.time}
                  disabled={!cfg.enabled}
                  onChange={(e) => setTime(r.key, e.target.value)}
                />
              </div>
            </div>
          )
        })}

        {saved && <div className="success-msg">Reminders saved.</div>}
        {error && <div className="error-msg">{error}</div>}

        <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
          {saving ? 'Saving...' : 'Save Reminders'}
        </button>
      </div>

      <div className="card">
        <div className="card-title">📋 Upcoming (example panel)</div>
        {REMINDER_DEFS.filter((r) => settings[r.key]?.enabled).length === 0 ? (
          <div style={{ fontSize: '0.85rem', color: 'var(--gray)' }}>No reminders enabled.</div>
        ) : (
          REMINDER_DEFS.filter((r) => settings[r.key]?.enabled).map((r) => (
            <div key={r.key} className="notif-upcoming">
              <span>{r.icon} {r.label}</span>
              <span className="notif-time-pill">{settings[r.key].time}</span>
            </div>
          ))
        )}
      </div>
    </div>
  )
}

import { useState, useEffect } from 'react'
import { api } from '../api/client.js'

const REMINDER_DEFS = [
  { key: 'medication', icon: '💊', label: 'Scheduled medication', example: 'Time for your scheduled medication. (Reminder only - no dosing advice.)', defaultTime: '08:00' },
  { key: 'meal_logging', icon: '🍽️', label: 'Meal / logging routine', example: "Don't forget to log today's meals and glucose readings.", defaultTime: '12:30' },
  { key: 'planned_activity', icon: '🏃', label: 'Planned activity', example: 'Time for your planned walk or activity. Stay hydrated!', defaultTime: '17:30' },
]
const emptySettings = () => REMINDER_DEFS.reduce((acc, r) => ({ ...acc, [r.key]: { enabled: true, time: r.defaultTime } }), {})
const displayTime = (iso) => new Intl.DateTimeFormat(undefined, { timeZone: 'Asia/Singapore', dateStyle: 'medium', timeStyle: 'short' }).format(new Date(iso))

export default function NotificationsPage({ userId, language, setPage }) {
  const [settings, setSettings] = useState(emptySettings())
  const [notifications, setNotifications] = useState([])
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState(null)
  const backLabel = language === 'zh' ? '← 返回个人资料' : '← Back to profile'

  const load = async () => {
    try {
      const [prefs, messages] = await Promise.all([api.getPreferences(userId), api.getNotifications(userId)])
      const merged = emptySettings()
      for (const r of REMINDER_DEFS) if (prefs.reminder_settings?.[r.key]) merged[r.key] = prefs.reminder_settings[r.key]
      setSettings(merged); setNotifications(messages)
    } catch (err) { setError(err.message || 'Could not load reminders.') }
  }
  useEffect(() => { load(); const timer = setInterval(load, 60000); return () => clearInterval(timer) }, [userId])
  const toggle = (key) => { setSettings(s => ({ ...s, [key]: { ...s[key], enabled: !s[key].enabled } })); setSaved(false) }
  const setTime = (key, time) => { setSettings(s => ({ ...s, [key]: { ...s[key], time } })); setSaved(false) }
  const save = async () => { setSaving(true); setError(null); try { await api.updatePreferences(userId, { reminder_settings: settings }); setSaved(true) } catch (err) { setError(err.message || 'Could not save reminders.') } finally { setSaving(false) } }
  const read = async (id) => { await api.markNotificationRead(id, userId); await load() }

  return <div>
    <div className="card"><button className="page-back" onClick={() => setPage('profile')}>{backLabel}</button><div className="card-title">🔔 Notifications & reminders</div><div style={{ fontSize: '0.85rem', color: 'var(--gray)', marginBottom: 12 }}>Times are fixed to Singapore time (Asia/Singapore). Reminders are delivered to this in-app inbox, including when the app was closed.</div>
      {REMINDER_DEFS.map(r => { const cfg = settings[r.key]; return <div key={r.key} className="notif-card"><div className="notif-head"><span className="notif-icon">{r.icon}</span><span className="notif-label">{r.label}</span><button type="button" className={`toggle ${cfg.enabled ? 'on' : ''}`} onClick={() => toggle(r.key)}>{cfg.enabled ? 'On' : 'Off'}</button></div><div className="notif-example">{r.example}</div><div className="notif-time"><label className="form-label">Remind at</label><input className="form-input" type="time" value={cfg.time} disabled={!cfg.enabled} onChange={e => setTime(r.key, e.target.value)} /></div></div> })}
      {saved && <div className="success-msg">Reminders saved.</div>}{error && <div className="error-msg">{error}</div>}<button className="btn btn-primary" onClick={save} disabled={saving}>{saving ? 'Saving...' : 'Save reminders'}</button>
    </div>
    <div className="card"><div className="card-title">📬 Reminder inbox</div>{notifications.length === 0 ? <div style={{ fontSize: '0.85rem', color: 'var(--gray)' }}>No delivered reminders yet.</div> : notifications.map(n => <div key={n.notification_id} className="notif-upcoming"><span><strong>{n.title}</strong><br /><small>{n.body} · {displayTime(n.due_at)}{n.status === 'overdue' ? ' · overdue' : ''}</small></span>{n.status !== 'read' && <button className="btn btn-secondary" onClick={() => read(n.notification_id)}>Mark read</button>}</div>)}</div>
  </div>
}

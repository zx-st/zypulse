import { useState } from 'react'
import { api } from '../api/client.js'

export default function LogPage({ userId }) {
  const [tab, setTab] = useState('glucose')
  const [success, setSuccess] = useState(null)
  const [error, setError] = useState(null)

  const today = new Date().toISOString().split('T')[0]

  // Glucose form state
  const [glucoseValue, setGlucoseValue] = useState('')
  const [glucosePeriod, setGlucosePeriod] = useState('fasting')
  const [glucoseDate, setGlucoseDate] = useState(today)
  const [glucoseNotes, setGlucoseNotes] = useState('')

  // Medication form state
  const [medPeriod, setMedPeriod] = useState('morning')
  const [medStatus, setMedStatus] = useState('taken')
  const [medDate, setMedDate] = useState(today)

  // Activity form state
  const [actType, setActType] = useState('walking')
  const [actDuration, setActDuration] = useState('')
  const [actLocation, setActLocation] = useState('')
  const [actDate, setActDate] = useState(today)

  const handleGlucoseSubmit = async (e) => {
    e.preventDefault()
    setSuccess(null)
    setError(null)
    try {
      const value = parseFloat(glucoseValue)
      if (isNaN(value) || value < 1 || value > 35) {
        setError('Please enter a valid glucose reading (1-35 mmol/L).')
        return
      }
      await api.logGlucose({
        user_id: userId,
        value: value,
        period: glucosePeriod,
        recorded_date: glucoseDate,
        notes: glucoseNotes || null,
      })
      setSuccess('Glucose reading saved successfully!')
      setGlucoseValue('')
      setGlucoseNotes('')
    } catch (err) {
      setError(err.message || 'Failed to save reading.')
    }
  }

  const handleMedSubmit = async (e) => {
    e.preventDefault()
    setSuccess(null)
    setError(null)
    try {
      await api.logMedication({
        user_id: userId,
        period: medPeriod,
        status: medStatus,
        recorded_date: medDate,
      })
      setSuccess('Medication status saved!')
    } catch (err) {
      setError(err.message || 'Failed to save medication log.')
    }
  }

  const handleActivitySubmit = async (e) => {
    e.preventDefault()
    setSuccess(null)
    setError(null)
    try {
      const duration = parseInt(actDuration)
      if (isNaN(duration) || duration < 0 || duration > 600) {
        setError('Please enter a valid duration (0-600 minutes).')
        return
      }
      await api.logActivity({
        user_id: userId,
        activity_type: actType,
        duration_min: duration,
        location: actLocation || null,
        recorded_date: actDate,
      })
      setSuccess('Activity saved!')
      setActDuration('')
      setActLocation('')
    } catch (err) {
      setError(err.message || 'Failed to save activity.')
    }
  }

  return (
    <div>
      <div className="card">
        <div className="card-title">📝 Record Your Self-Care</div>

        <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
          {['glucose', 'medication', 'activity'].map(t => (
            <button
              key={t}
              className={`btn ${tab === t ? 'btn-primary' : 'btn-secondary'}`}
              style={{ flex: 1, fontSize: '0.85rem', padding: '8px' }}
              onClick={() => { setTab(t); setSuccess(null); setError(null); }}
            >
              {t === 'glucose' ? '🩸 Glucose' : t === 'medication' ? '💊 Medication' : '🏃 Activity'}
            </button>
          ))}
        </div>

        {success && <div className="success-msg">{success}</div>}
        {error && <div className="error-msg">{error}</div>}

        {tab === 'glucose' && (
          <form onSubmit={handleGlucoseSubmit}>
            <div className="form-group">
              <label className="form-label">Reading (mmol/L)</label>
              <input
                className="form-input"
                type="number"
                step="0.1"
                min="1"
                max="35"
                placeholder="e.g. 7.2"
                value={glucoseValue}
                onChange={e => setGlucoseValue(e.target.value)}
                required
              />
            </div>
            <div className="form-group">
              <label className="form-label">When</label>
              <select className="form-select" value={glucosePeriod} onChange={e => setGlucosePeriod(e.target.value)}>
                <option value="fasting">Fasting (before breakfast)</option>
                <option value="evening">Evening</option>
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Date</label>
              <input className="form-input" type="date" value={glucoseDate} onChange={e => setGlucoseDate(e.target.value)} required />
            </div>
            <div className="form-group">
              <label className="form-label">Notes (optional)</label>
              <textarea className="form-textarea" value={glucoseNotes} onChange={e => setGlucoseNotes(e.target.value)} placeholder="Any observations..." />
            </div>
            <button type="submit" className="btn btn-primary">Save Reading</button>
          </form>
        )}

        {tab === 'medication' && (
          <form onSubmit={handleMedSubmit}>
            <div className="form-group">
              <label className="form-label">Medication</label>
              <div style={{ padding: '10px 12px', background: 'var(--gray-light)', borderRadius: 8, fontSize: '0.9rem' }}>
                Metformin 500mg (prescribed twice daily)
              </div>
            </div>
            <div className="form-group">
              <label className="form-label">Dose Time</label>
              <select className="form-select" value={medPeriod} onChange={e => setMedPeriod(e.target.value)}>
                <option value="morning">Morning</option>
                <option value="evening">Evening</option>
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Status</label>
              <select className="form-select" value={medStatus} onChange={e => setMedStatus(e.target.value)}>
                <option value="taken">Taken</option>
                <option value="missed">Missed</option>
                <option value="skipped">Skipped</option>
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Date</label>
              <input className="form-input" type="date" value={medDate} onChange={e => setMedDate(e.target.value)} required />
            </div>
            <button type="submit" className="btn btn-primary">Save Status</button>
          </form>
        )}

        {tab === 'activity' && (
          <form onSubmit={handleActivitySubmit}>
            <div className="form-group">
              <label className="form-label">Activity Type</label>
              <select className="form-select" value={actType} onChange={e => setActType(e.target.value)}>
                <option value="walking">Walking</option>
                <option value="exercise">Exercise</option>
                <option value="stretching">Stretching</option>
                <option value="cycling">Cycling</option>
                <option value="swimming">Swimming</option>
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Duration (minutes)</label>
              <input className="form-input" type="number" min="0" max="600" placeholder="e.g. 30" value={actDuration} onChange={e => setActDuration(e.target.value)} required />
            </div>
            <div className="form-group">
              <label className="form-label">Location (optional)</label>
              <input className="form-input" type="text" placeholder="e.g. Tampines Eco Green" value={actLocation} onChange={e => setActLocation(e.target.value)} />
            </div>
            <div className="form-group">
              <label className="form-label">Date</label>
              <input className="form-input" type="date" value={actDate} onChange={e => setActDate(e.target.value)} required />
            </div>
            <button type="submit" className="btn btn-primary">Save Activity</button>
          </form>
        )}
      </div>
    </div>
  )
}

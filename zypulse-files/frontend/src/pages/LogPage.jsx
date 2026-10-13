import { useState } from 'react'
import { api } from '../api/client.js'
import { translateText } from '../i18n.jsx'
import PhotoLogWorkflow from '../components/PhotoLogWorkflow.jsx'

export default function LogPage({ userId, language, initialTab = 'glucose', initialLocation = '', activityDraft = null }) {
  const t = (text) => translateText(language, text)
  const [tab, setTab] = useState(initialTab)
  const [success, setSuccess] = useState(null)
  const [error, setError] = useState(null)
  const [glucosePhotoOpen, setGlucosePhotoOpen] = useState(false)
  const [medPhotoOpen, setMedPhotoOpen] = useState(false)

  const today = new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Singapore' }).format(new Date())

  // Glucose form state
  const [glucoseValue, setGlucoseValue] = useState('')
  const [glucosePeriod, setGlucosePeriod] = useState('fasting')
  const [glucoseDate, setGlucoseDate] = useState(today)
  const [glucoseNotes, setGlucoseNotes] = useState('')
  // Optional opt-in: the note is only shown in the doctor visit summary when ticked.
  const [glucoseInclude, setGlucoseInclude] = useState(false)

  // Medication form state
  const [medPeriod, setMedPeriod] = useState('morning')
  const [medStatus, setMedStatus] = useState('taken')
  const [medDate, setMedDate] = useState(today)
  const [medNotes, setMedNotes] = useState('')
  const [medInclude, setMedInclude] = useState(false)

  // Activity form state (optionally pre-filled from a Healthy 365 demo event)
  const [actType, setActType] = useState(activityDraft?.activity_type || 'walking')
  const [actDuration, setActDuration] = useState(activityDraft?.duration_min ? String(activityDraft.duration_min) : '')
  const [actLocation, setActLocation] = useState(activityDraft?.location || initialLocation)
  const [actDate, setActDate] = useState(activityDraft?.recorded_date || today)
  const [actStatus, setActStatus] = useState(activityDraft?.status || 'completed')
  const [actHeartRate, setActHeartRate] = useState('')
  const [actEventId, setActEventId] = useState(activityDraft?.source_event_id || '')
  const [actNotes, setActNotes] = useState('')
  const [actInclude, setActInclude] = useState(false)
  const [duplicate, setDuplicate] = useState(null)

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
        include_in_visit: glucoseInclude,
      })
      setSuccess('Glucose reading saved successfully!')
      setGlucoseValue('')
      setGlucoseNotes('')
      setGlucoseInclude(false)
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
        visit_note: medNotes.trim() || null,
        include_in_visit: medInclude,
      })
      setSuccess('Medication status saved!')
      setMedNotes('')
      setMedInclude(false)
    } catch (err) {
      setError(err.message || 'Failed to save medication log.')
    }
  }

  const handleActivitySubmit = async (e) => {
    e.preventDefault()
    setSuccess(null)
    setError(null)
    setDuplicate(null)
    try {
      const duration = parseInt(actDuration)
      if (isNaN(duration) || duration < 0 || duration > 600) {
        setError('Please enter a valid duration (0-600 minutes).')
        return
      }
      const rawHeartRate = actHeartRate.trim()
      let heartRate = null
      if (rawHeartRate !== '') {
        heartRate = Number(rawHeartRate)
        if (!Number.isInteger(heartRate) || heartRate < 20 || heartRate > 250) {
          setError(t('Enter a whole number between 20 and 250 bpm, or leave the field empty.'))
          return
        }
      }
      const response = await api.logActivity({
        user_id: userId,
        activity_type: actType,
        duration_min: duration,
        location: actLocation || null,
        recorded_date: actDate,
        avg_heart_rate: heartRate,
        status: actStatus,
        source_event_id: actEventId || null,
        visit_note: actNotes.trim() || null,
        include_in_visit: actInclude,
      })
      if (response?.duplicate) {
        setDuplicate(response.message || t('This demo event is already in your Activity Log.'))
      } else {
        setSuccess(actStatus === 'planned'
          ? t('Planned activity saved. It is not counted as completed exercise.')
          : 'Activity saved!')
        setActDuration('')
        setActLocation('')
        setActHeartRate('')
        setActNotes('')
        setActInclude(false)
      }
    } catch (err) {
      setError(err.message || 'Failed to save activity.')
    }
  }

  const confirmGlucosePhoto = async (payload) => {
    const res = await api.logGlucose({
      user_id: userId,
      value: payload.value,
      period: payload.period,
      recorded_date: payload.recorded_date,
      notes: payload.notes,
      photo_ref: payload.photo_ref,
    })
    setSuccess(t('Glucose reading saved from photo.'))
    return res // lets the photo workflow attach the uploaded original
  }

  const confirmMedPhoto = async (payload) => {
    const res = await api.logMedication({
      user_id: userId,
      period: payload.period,
      status: payload.status,
      medication_name: payload.medication_name,
      dose: payload.dose,
      recorded_date: today,
      notes: payload.notes,
      photo_ref: payload.photo_ref,
    })
    setSuccess(t('Medication logged from photo.'))
    return res
  }

  return (
    <div>
      <div className="card">
        <div className="card-title">📝 {t('Record Your Self-Care')}</div>

        <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
          {['glucose', 'medication', 'activity'].map(t => (
            <button
              key={t}
              className={`btn ${tab === t ? 'btn-primary' : 'btn-secondary'}`}
              style={{ flex: 1, fontSize: '0.85rem', padding: '8px' }}
              onClick={() => { setTab(t); setSuccess(null); setError(null); }}
            >
              {t === 'glucose' ? `🩸 ${translateText(language, 'Glucose')}` : t === 'medication' ? `💊 ${translateText(language, 'Medication')}` : `🏃 ${translateText(language, 'Activity')}`}
            </button>
          ))}
        </div>

        {success && <div className="success-msg">{success}</div>}
        {error && <div className="error-msg">{error}</div>}

        {tab === 'glucose' && (
          <>
            <div className="photo-entry">
              <button type="button" className="btn btn-secondary btn-sm" onClick={() => setGlucosePhotoOpen((o) => !o)}>📷 {t('Scan Reading')}</button>
              <span className="photo-filename">{t('or enter manually below')}</span>
            </div>
            {glucosePhotoOpen && (
              <PhotoLogWorkflow logType="glucose" userId={userId} language={language} today={today}
                onConfirm={confirmGlucosePhoto} onCancel={() => setGlucosePhotoOpen(false)} />
            )}
            <form onSubmit={handleGlucoseSubmit}>
            <div className="form-group">
              <label className="form-label">{t('Reading (mmol/L)')}</label>
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
              <label className="form-label">{t('When')}</label>
              <select className="form-select" value={glucosePeriod} onChange={e => setGlucosePeriod(e.target.value)}>
                <option value="fasting">{t('Fasting (before breakfast)')}</option>
                <option value="evening">{t('Evening')}</option>
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">{t('Date')}</label>
              <input className="form-input" type="date" value={glucoseDate} onChange={e => setGlucoseDate(e.target.value)} required />
            </div>
            <div className="form-group">
              <label className="form-label">{t('Notes (optional)')}</label>
              <textarea className="form-textarea" value={glucoseNotes} onChange={e => setGlucoseNotes(e.target.value)} placeholder={t('Any observations...')} />
            </div>
            <label className="checkbox-row">
              <input type="checkbox" checked={glucoseInclude} onChange={(e) => setGlucoseInclude(e.target.checked)} />
              {t('Include this note in visit summary for my doctor')}
            </label>
            <button type="submit" className="btn btn-primary">{t('Save Reading')}</button>
            </form>
          </>
        )}

        {tab === 'medication' && (
          <>
            <div className="photo-entry">
              <button type="button" className="btn btn-secondary btn-sm" onClick={() => setMedPhotoOpen((o) => !o)}>📷 {t('Scan Medication')}</button>
              <span className="photo-filename">{t('or enter manually below')}</span>
            </div>
            {medPhotoOpen && (
              <PhotoLogWorkflow logType="medication" userId={userId} language={language} today={today}
                onConfirm={confirmMedPhoto} onCancel={() => setMedPhotoOpen(false)} />
            )}
            <form onSubmit={handleMedSubmit}>
            <div className="form-group">
              <label className="form-label">{t('Medication')}</label>
              <div style={{ padding: '10px 12px', background: 'var(--gray-light)', borderRadius: 8, fontSize: '0.9rem' }}>
                Metformin 500mg (prescribed twice daily)
              </div>
            </div>
            <div className="form-group">
              <label className="form-label">{t('Dose Time')}</label>
              <select className="form-select" value={medPeriod} onChange={e => setMedPeriod(e.target.value)}>
                <option value="morning">{t('Morning')}</option>
                <option value="evening">{t('Evening')}</option>
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">{t('Status')}</label>
              <select className="form-select" value={medStatus} onChange={e => setMedStatus(e.target.value)}>
                <option value="taken">{t('Taken')}</option>
                <option value="missed">{t('Missed')}</option>
                <option value="skipped">{t('Skipped')}</option>
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">{t('Date')}</label>
              <input className="form-input" type="date" value={medDate} onChange={e => setMedDate(e.target.value)} required />
            </div>
            <div className="form-group">
              <label className="form-label">{t('Notes (optional)')}</label>
              <textarea className="form-textarea" value={medNotes} onChange={e => setMedNotes(e.target.value)} placeholder={t('Any observations...')} />
            </div>
            <label className="checkbox-row">
              <input type="checkbox" checked={medInclude} onChange={(e) => setMedInclude(e.target.checked)} />
              {t('Include this note in visit summary for my doctor')}
            </label>
            <button type="submit" className="btn btn-primary">{t('Save Status')}</button>
            </form>
          </>
        )}

        {tab === 'activity' && (
          <form onSubmit={handleActivitySubmit}>
            {actEventId && (
              <div className="h365-draft-note">
                🧪 {t('Pre-filled from Healthy 365 demo event')} <code>{actEventId}</code> — {t('edit anything before saving.')}
              </div>
            )}
            <div className="form-group">
              <label className="form-label">{t('Activity Type')}</label>
              <select className="form-select" value={actType} onChange={e => setActType(e.target.value)}>
                <option value="walking">{t('Walking')}</option><option value="exercise">{t('Exercise')}</option><option value="stretching">{t('Stretching')}</option><option value="cycling">{t('Cycling')}</option><option value="swimming">{t('Swimming')}</option><option value="group exercise">{t('Group exercise')}</option><option value="strength">{t('Strength')}</option>
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">{t('Status')}</label>
              <select className="form-select" value={actStatus} onChange={e => setActStatus(e.target.value)}>
                <option value="planned">{t('Planned')}</option>
                <option value="completed">{t('Completed')}</option>
              </select>
              {actStatus === 'planned' && (
                <div className="h365-draft-note">{t('Planned activities are kept separate and are not counted as completed exercise.')}</div>
              )}
            </div>
            <div className="form-group">
              <label className="form-label">{t('Duration (minutes)')}</label>
              <input className="form-input" type="number" min="0" max="600" placeholder="e.g. 30" value={actDuration} onChange={e => setActDuration(e.target.value)} required />
            </div>
            <div className="form-group">
              <label className="form-label">{t('Location (optional)')}</label>
              <input className="form-input" type="text" placeholder="e.g. Tampines Eco Green" value={actLocation} onChange={e => setActLocation(e.target.value)} />
            </div>
            <div className="form-group">
              <label className="form-label">{t('Average heart rate (bpm, optional)')}</label>
              <input
                className="form-input"
                type="number"
                min="20"
                max="250"
                step="1"
                inputMode="numeric"
                placeholder={t('Leave empty if not measured')}
                value={actHeartRate}
                onChange={e => setActHeartRate(e.target.value)}
              />
              <div className="h365-draft-note">{t('Only enter a value you measured yourself. ZyPulse does not estimate heart rate and does not judge intensity or fitness from it.')}</div>
            </div>
            <div className="form-group">
              <label className="form-label">{t('Date')}</label>
              <input className="form-input" type="date" value={actDate} onChange={e => setActDate(e.target.value)} required />
            </div>
            <div className="form-group">
              <label className="form-label">{t('Notes (optional)')}</label>
              <textarea className="form-textarea" value={actNotes} onChange={e => setActNotes(e.target.value)} placeholder={t('Any observations...')} />
            </div>
            <label className="checkbox-row">
              <input type="checkbox" checked={actInclude} onChange={(e) => setActInclude(e.target.checked)} />
              {t('Include this note in visit summary for my doctor')}
            </label>
            {duplicate && <div className="h365-draft-note h365-duplicate">{duplicate}</div>}
            <button type="submit" className="btn btn-primary">{t('Save Activity')}</button>
          </form>
        )}
      </div>
    </div>
  )
}

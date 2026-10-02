import { useState, useEffect } from 'react'
import { api } from '../api/client.js'

export default function SummaryPage({ userId, language, setPage }) {
  const [trends, setTrends] = useState(null)
  const [notes, setNotes] = useState([])
  const [noteText, setNoteText] = useState('')
  const [includeInVisit, setIncludeInVisit] = useState(false)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    loadAll()
  }, [userId])

  const loadAll = async () => {
    setLoading(true)
    setError(null)
    try {
      const [gf, ge, med, act, noteList, mealList] = await Promise.all([
        api.getTrends({ user_id: userId, metric: 'glucose', period: 'fasting', days: 7 }),
        api.getTrends({ user_id: userId, metric: 'glucose', period: 'evening', days: 7 }),
        api.getTrends({ user_id: userId, metric: 'medication', days: 30 }),
        api.getTrends({ user_id: userId, metric: 'activity', days: 30 }),
        api.getHistory({ user_id: userId, category: 'notes', limit: 200 }),
        api.getHistory({ user_id: userId, category: 'meals', limit: 200 }),
      ])
      setTrends({ gf, ge, med, act })
      setNotes(noteList.concat(mealList))
    } catch (err) {
      setError('Unable to load health summary.')
    } finally {
      setLoading(false)
    }
  }

  // Visit notes = user notes flagged for visit, plus meals flagged with a note.
  const visitNotes = notes.filter(
    (n) => n.include_in_visit_summary && (n.record_type !== 'meal' || (n.notes && n.notes.trim()))
  )
  const suggested = buildSuggestedQuestions(trends)

  const handleAddNote = async (e) => {
    e.preventDefault()
    if (!noteText.trim()) return
    setSaving(true)
    setMsg(null)
    setError(null)
    try {
      await api.createNote({
        user_id: userId,
        content: noteText.trim(),
        include_in_visit: includeInVisit,
      })
      setNoteText('')
      setIncludeInVisit(false)
      setMsg('Note saved.')
      await loadAll()
    } catch (err) {
      setError(err.message || 'Could not save note.')
    } finally {
      setSaving(false)
    }
  }

  const toggleInclude = async (note) => {
    try {
      await api.updateNote(note.record_id, { include_in_visit: !note.include_in_visit_summary })
      await loadAll()
    } catch (err) {
      setError('Could not update note.')
    }
  }

  if (loading) return <div className="loading">Loading your health summary...</div>
  if (error) return <div className="error-msg">{error}</div>

  const t = trends
  return (
    <div>
      <div className="card">
        <div className="card-title">🩺 Health Summary</div>
        <div className="summary-grid">
          <div className="summary-cell">
            <div className="summary-num">{t.gf.average ?? '–'}</div>
            <div className="summary-cap">Fasting glucose (7d, mmol/L)</div>
          </div>
          <div className="summary-cell">
            <div className="summary-num">{t.med.adherence_rate != null ? `${t.med.adherence_rate}%` : '–'}</div>
            <div className="summary-cap">Med adherence (30d)</div>
          </div>
          <div className="summary-cell">
            <div className="summary-num">{t.act.activity_days ?? '–'}</div>
            <div className="summary-cap">Active days (30d)</div>
          </div>
          <div className="summary-cell">
            <div className="summary-num">{t.act.total_duration_min ?? '–'}</div>
            <div className="summary-cap">Active mins (30d)</div>
          </div>
        </div>
        <div style={{ fontSize: '0.75rem', color: 'var(--gray)', fontStyle: 'italic', marginTop: 8 }}>
          All values calculated by deterministic code. ZyPulse explains but never recalculates.
        </div>
      </div>

      <div className="card">
        <div className="card-title">📈 Trends</div>
        <TrendLine label="Fasting glucose (7d)" avg={t.gf.average} note={t.gf.notes} direction={t.gf.trend_direction} pct={t.gf.trend_pct} />
        <TrendLine label="Evening glucose (7d)" avg={t.ge.average} note={t.ge.notes} direction={t.ge.trend_direction} pct={t.ge.trend_pct} />
        <TrendLine label="Medication adherence (30d)" avg={t.med.adherence_rate} note={t.med.notes} direction={t.med.trend_direction} pct={null} />
        <TrendLine label="Activity (30d)" avg={t.act.activity_days} note={t.act.notes} direction={null} pct={null} />
      </div>

      <div className="card">
        <div className="card-title">📝 Add a Note</div>
        <form onSubmit={handleAddNote}>
          <div className="form-group">
            <textarea
              className="form-textarea"
              value={noteText}
              onChange={(e) => setNoteText(e.target.value)}
              placeholder="Write a note for your own reference (e.g. 'Felt dizzy after morning walk')."
              maxLength={1000}
            />
          </div>
          <label className="checkbox-row">
            <input type="checkbox" checked={includeInVisit} onChange={(e) => setIncludeInVisit(e.target.checked)} />
            Include in visit summary for my doctor
          </label>
          {msg && <div className="success-msg">{msg}</div>}
          {error && <div className="error-msg">{error}</div>}
          <button type="submit" className="btn btn-primary" disabled={saving || !noteText.trim()}>
            {saving ? 'Saving...' : 'Save Note'}
          </button>
        </form>
      </div>

      <div className="card">
        <div className="card-title">👨‍⚕️ Notes for My Doctor</div>
        {visitNotes.length === 0 ? (
          <div style={{ fontSize: '0.85rem', color: 'var(--gray)' }}>
            No notes selected yet. Add a note above and tick "Include in visit summary".
          </div>
        ) : (
          visitNotes.map((n) => {
            let mealLabel = 'Meal'
            if (n.record_type === 'meal') {
              try { mealLabel = (JSON.parse(n.value_text || '{}').meal_type || 'meal') } catch { /* ignore */ }
            }
            return (
              <div key={n.record_id} className="visit-note">
                <div>
                  {n.record_type === 'meal'
                    ? <>🍽️ <em>{mealLabel} note:</em> {n.notes}</>
                    : n.value_text}
                </div>
                <div className="visit-note-date">{n.recorded_date}</div>
              </div>
            )
          })
        )}
      </div>

      <div className="card">
        <div className="card-title">💡 Questions you could ask</div>
        <div style={{ fontSize: '0.8rem', color: 'var(--gray)', marginBottom: 8 }}>
          ZyPulse suggests topics to discuss - it does NOT diagnose or recommend treatment changes.
        </div>
        {suggested.length === 0 ? (
          <div style={{ fontSize: '0.85rem', color: 'var(--gray)' }}>Keep logging to get personalised suggestions.</div>
        ) : (
          suggested.map((q, i) => (
            <div key={i} className="suggested-q">
              <span>❓ {q}</span>
              <button className="btn btn-secondary btn-sm" onClick={() => setPage && setPage('chat')}>
                Ask Coach
              </button>
            </div>
          ))
        )}
      </div>
    </div>
  )
}

function TrendLine({ label, avg, note, direction, pct }) {
  const badge = direction
    ? <span className={`trend-badge ${badgeClass(direction)}`}>{badgeLabel(direction)}{pct != null ? ` (${pct > 0 ? '+' : ''}${pct}%)` : ''}</span>
    : null
  return (
    <div className="trend-row">
      <span className="trend-label">{label}</span>
      <span className="trend-value">{avg != null ? avg : '–'} {badge}</span>
    </div>
  )
}

function badgeClass(direction) {
  const map = {
    stable: 'badge-stable', increasing: 'badge-increasing', decreasing: 'badge-decreasing',
    insufficient_data: 'badge-insufficient', below_target: 'badge-below-target',
  }
  return map[direction] || 'badge-insufficient'
}

function badgeLabel(direction) {
  const map = { stable: 'Stable', increasing: 'Increasing', decreasing: 'Decreasing', insufficient_data: 'Insufficient', below_target: 'Below target' }
  return map[direction] || direction
}

// Deterministic, safe suggestions - questions to ask a professional, never advice.
function buildSuggestedQuestions(trends) {
  const q = []
  if (!trends) return q
  const { med, gf, act } = trends
  if (med && med.missed_doses && med.missed_doses > 0) {
    q.push('Ask your pharmacist about simple strategies to remember your prescribed medication.')
  }
  if (gf && (gf.trend_direction === 'increasing' || (gf.average && gf.average > 7))) {
    q.push('Ask your doctor how your recent glucose trend fits your management plan.')
  }
  if (act && act.activity_days != null && act.activity_days < 10) {
    q.push('Ask about physical activities that suit your routine and energy levels.')
  }
  q.push('Bring this summary to your next appointment so your doctor can see your self-care record.')
  q.push('Ask your care team about any side effects you have noticed.')
  return q.slice(0, 5)
}

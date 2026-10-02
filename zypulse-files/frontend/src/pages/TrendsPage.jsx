import { useState, useEffect } from 'react'
import { api } from '../api/client.js'

export default function TrendsPage({ userId }) {
  const [glucoseFasting, setGlucoseFasting] = useState(null)
  const [glucoseEvening, setGlucoseEvening] = useState(null)
  const [medication, setMedication] = useState(null)
  const [activity, setActivity] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    loadTrends()
  }, [userId])

  const loadTrends = async () => {
    setLoading(true)
    setError(null)
    try {
      const [gf, ge, med, act] = await Promise.all([
        api.getTrends({ user_id: userId, metric: 'glucose', period: 'fasting', days: 7 }),
        api.getTrends({ user_id: userId, metric: 'glucose', period: 'evening', days: 7 }),
        api.getTrends({ user_id: userId, metric: 'medication', days: 30 }),
        api.getTrends({ user_id: userId, metric: 'activity', days: 30 }),
      ])
      setGlucoseFasting(gf)
      setGlucoseEvening(ge)
      setMedication(med)
      setActivity(act)
    } catch (err) {
      setError('Unable to load trends. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const trendBadgeClass = (direction) => {
    const map = {
      stable: 'badge-stable',
      increasing: 'badge-increasing',
      decreasing: 'badge-decreasing',
      insufficient_data: 'badge-insufficient',
      below_target: 'badge-below-target',
    }
    return map[direction] || 'badge-insufficient'
  }

  const trendLabel = (direction) => {
    const map = {
      stable: 'Stable',
      increasing: 'Increasing',
      decreasing: 'Decreasing',
      insufficient_data: 'Insufficient data',
      below_target: 'Below target',
    }
    return map[direction] || direction
  }

  if (loading) return <div className="loading">Loading your trends...</div>
  if (error) return <div className="error-msg">{error}</div>

  return (
    <div>
      <div className="card">
        <div className="card-title">🩸 Glucose Trends (7 days)</div>

        {glucoseFasting && !glucoseFasting.insufficient_data && (
          <>
            <div className="trend-row">
              <span className="trend-label">Fasting average</span>
              <span className="trend-value">{glucoseFasting.average} mmol/L</span>
            </div>
            <div className="trend-row">
              <span className="trend-label">Fasting range</span>
              <span className="trend-value">{glucoseFasting.min_value} – {glucoseFasting.max_value}</span>
            </div>
            <div className="trend-row">
              <span className="trend-label">Fasting trend</span>
              <span className="trend-value">
                <span className={`trend-badge ${trendBadgeClass(glucoseFasting.trend_direction)}`}>
                  {trendLabel(glucoseFasting.trend_direction)}
                </span>
                {glucoseFasting.trend_pct !== null && ` (${glucoseFasting.trend_pct > 0 ? '+' : ''}${glucoseFasting.trend_pct}%)`}
              </span>
            </div>
            <div className="trend-row">
              <span className="trend-label">Readings</span>
              <span className="trend-value">{glucoseFasting.readings_count}</span>
            </div>
          </>
        )}

        {glucoseFasting && glucoseFasting.insufficient_data && (
          <div style={{ color: 'var(--gray)', fontSize: '0.85rem' }}>{glucoseFasting.notes}</div>
        )}

        <div style={{ borderTop: '1px solid var(--border)', margin: '12px 0' }} />

        {glucoseEvening && !glucoseEvening.insufficient_data && (
          <>
            <div className="trend-row">
              <span className="trend-label">Evening average</span>
              <span className="trend-value">{glucoseEvening.average} mmol/L</span>
            </div>
            <div className="trend-row">
              <span className="trend-label">Evening range</span>
              <span className="trend-value">{glucoseEvening.min_value} – {glucoseEvening.max_value}</span>
            </div>
            <div className="trend-row">
              <span className="trend-label">Evening trend</span>
              <span className="trend-value">
                <span className={`trend-badge ${trendBadgeClass(glucoseEvening.trend_direction)}`}>
                  {trendLabel(glucoseEvening.trend_direction)}
                </span>
              </span>
            </div>
          </>
        )}

        {glucoseEvening && glucoseEvening.insufficient_data && (
          <div style={{ color: 'var(--gray)', fontSize: '0.85rem' }}>{glucoseEvening.notes}</div>
        )}

        <div style={{ marginTop: 12, fontSize: '0.75rem', color: 'var(--gray)', fontStyle: 'italic' }}>
          All values calculated by deterministic code. AI explains but never calculates.
        </div>
      </div>

      <div className="card">
        <div className="card-title">💊 Medication Adherence (30 days)</div>
        {medication && !medication.insufficient_data && (
          <>
            <div className="trend-row">
              <span className="trend-label">Adherence rate</span>
              <span className="trend-value">
                <span className={`trend-badge ${trendBadgeClass(medication.trend_direction)}`}>
                  {medication.adherence_rate}%
                </span>
              </span>
            </div>
            <div className="trend-row">
              <span className="trend-label">Doses taken</span>
              <span className="trend-value">{medication.taken_doses} / {medication.expected_doses}</span>
            </div>
            <div className="trend-row">
              <span className="trend-label">Missed doses</span>
              <span className="trend-value">{medication.missed_doses}</span>
            </div>
            <div style={{ marginTop: 8, fontSize: '0.85rem', color: 'var(--gray-dark)' }}>{medication.notes}</div>
          </>
        )}
        {medication && medication.insufficient_data && (
          <div style={{ color: 'var(--gray)', fontSize: '0.85rem' }}>{medication.notes}</div>
        )}
      </div>

      <div className="card">
        <div className="card-title">🏃 Activity Summary (30 days)</div>
        {activity && !activity.insufficient_data && (
          <>
            <div className="trend-row">
              <span className="trend-label">Active days</span>
              <span className="trend-value">{activity.activity_days} / 30</span>
            </div>
            <div className="trend-row">
              <span className="trend-label">Total duration</span>
              <span className="trend-value">{activity.total_duration_min} min</span>
            </div>
            <div className="trend-row">
              <span className="trend-label">Average per session</span>
              <span className="trend-value">{activity.avg_duration_min} min</span>
            </div>
            <div style={{ marginTop: 8, fontSize: '0.85rem', color: 'var(--gray-dark)' }}>{activity.notes}</div>
          </>
        )}
        {activity && activity.insufficient_data && (
          <div style={{ color: 'var(--gray)', fontSize: '0.85rem' }}>{activity.notes}</div>
        )}
      </div>

      <button className="btn btn-secondary" onClick={loadTrends} style={{ marginBottom: 20 }}>
        Refresh Trends
      </button>
    </div>
  )
}

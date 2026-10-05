import { useState, useEffect } from 'react'
import { api } from '../api/client.js'
import { translateText } from '../i18n.jsx'

export default function ActivitiesPage({ userId, language }) {
  const t = (text) => translateText(language, text)
  const [activities, setActivities] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [filterType, setFilterType] = useState('')

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
      setError(err.message || 'Unable to load sports facilities.')
    } finally {
      setLoading(false)
    }
  }

  if (loading) return <div className="loading">{t('Loading activities...')}</div>
  if (error) return <div className="error-msg">{error}</div>

  return (
    <div>
      <div className="card">
        <div className="card-title">🤝 {t('Nearby Sports Facilities')}</div>
        <div style={{ fontSize: '0.85rem', color: 'var(--gray)', marginBottom: 12 }}>
          {t('Explore sports facilities and the activities they support across Singapore.')}
        </div>

        <div className="form-group">
          <label className="form-label">{t('Filter by type')}</label>
          <select className="form-select" value={filterType} onChange={e => setFilterType(e.target.value)}>
            <option value="">{t('All types')}</option><option value="badminton">{t('Badminton')}</option><option value="swimming">{t('Swimming')}</option><option value="tennis">{t('Tennis')}</option><option value="gymnasium">{t('Gymnasium')}</option><option value="fitness">{t('Fitness')}</option>
          </select>
        </div>
        <button className="btn btn-secondary" onClick={loadActivities} style={{ marginBottom: 12 }}>
          {t('Search')}
        </button>
      </div>

      <div style={{ fontSize: '0.78rem', color: 'var(--gray)', textAlign: 'center', marginBottom: 12 }}>
        {t('Source: Sport Singapore via data.gov.sg. Facility availability is not shown.')}
      </div>

      {activities.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">🔍</div>
          {t('No activities found. Try a different filter.')}
        </div>
      ) : (
        activities.map(activity => (
          <div key={activity.activity_id} className="activity-card">
            <div className="activity-title">{activity.title}</div>
            <div className="activity-meta">{activity.location}</div>
            <div className="activity-desc">{activity.description}</div>
            <div style={{ marginBottom: 8 }}>
              {activity.sports.map(sport => (
                <span className="activity-badge badge-open" key={sport}>{sport}</span>
              ))}
            </div>
          </div>
        ))
      )}
    </div>
  )
}

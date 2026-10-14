import { useState, useEffect } from 'react'
import { api } from '../api/client.js'
import { translateText } from '../i18n.jsx'
import Healthy365Section from '../components/Healthy365Section.jsx'

export default function ActivitiesPage({ userId, language, onRecordActivity, onAddToActivityLog, exploreTab = 'events', onExploreTabChange }) {
  const t = (text) => translateText(language, text)
  const [activities, setActivities] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [filterType, setFilterType] = useState('')
  // Controlled by App when provided, so Today's shortcuts can open a specific tab.
  const [localTab, setLocalTab] = useState(exploreTab)
  const tab = onExploreTabChange ? (exploreTab || 'events') : localTab
  const selectTab = (next) => {
    if (onExploreTabChange) onExploreTabChange(next)
    else setLocalTab(next)
  }

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

  // Facilities load as soon as their tab is opened — no Healthy 365 content to scroll past.
  useEffect(() => {
    if (tab === 'facilities') loadActivities()
  }, [tab, userId, filterType])

  return (
    <div>
      <div className="zv-tabs" role="tablist" aria-label="Explore">
        <button
          type="button"
          role="tab"
          className="zv-tab"
          aria-selected={tab === 'events'}
          onClick={() => selectTab('events')}
        >
          <span aria-hidden="true">🎉</span>
          {t('Healthy365 Events')}
        </button>
        <button
          type="button"
          role="tab"
          className="zv-tab"
          aria-selected={tab === 'facilities'}
          onClick={() => selectTab('facilities')}
        >
          <span aria-hidden="true">🏟️</span>
          {t('Sports Facilities')}
        </button>
      </div>

      {tab === 'events' && (
        <Healthy365Section userId={userId} language={language} onAddToActivityLog={onAddToActivityLog} />
      )}

      {tab === 'facilities' && (
        <>
          <div className="card">
            <div className="card-title">🤝 {t('Nearby Sports Facilities')}</div>
            <div style={{ fontSize: '0.9rem', color: 'var(--gray)', marginBottom: 12 }}>
              {t('Explore sports facilities and the activities they support across Singapore.')}
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="facility-filter">{t('Filter by type')}</label>
              <select id="facility-filter" className="form-select" value={filterType} onChange={e => setFilterType(e.target.value)}>
                <option value="">{t('All types')}</option><option value="badminton">{t('Badminton')}</option><option value="swimming">{t('Swimming')}</option><option value="tennis">{t('Tennis')}</option><option value="gymnasium">{t('Gymnasium')}</option><option value="fitness">{t('Fitness')}</option>
              </select>
            </div>
            <button className="btn btn-secondary" onClick={loadActivities} style={{ marginBottom: 12 }}>
              {t('Search')}
            </button>
          </div>

          <div style={{ fontSize: '0.8125rem', color: 'var(--gray)', textAlign: 'center', marginBottom: 12 }}>
            {t('Source: Sport Singapore via data.gov.sg. Facility availability is not shown.')}
          </div>

          {loading && <div className="loading">{t('Loading activities...')}</div>}
          {error && <div className="error-msg">{error}</div>}

          {!loading && !error && activities.length === 0 ? (
            <div className="empty-state">
              <div className="empty-state-icon">🔍</div>
              {t('No activities found. Try a different filter.')}
            </div>
          ) : (
            <div className="facility-grid">
              {activities.map(activity => (
                <div key={activity.activity_id} className="activity-card">
                  <div className="activity-content">
                  <div className="activity-title">{activity.title}</div>
                  <div className="activity-meta">{activity.location}</div>
                  <div className="activity-desc">{activity.description}</div>
                  <div style={{ marginBottom: 8 }}>
                    {activity.sports.map(sport => (
                      <span className="activity-badge badge-open" key={sport}>{sport}</span>
                    ))}
                  </div>
                  </div>
                  <button
                    type="button"
                    className="activity-record-button"
                    title={t('Record Activity')}
                    aria-label={`${t('Record Activity')} · ${activity.title}`}
                    onClick={() => onRecordActivity(activity)}
                  >
                    <svg width="23" height="23" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                      <path d="M13.5 5H6a2 2 0 0 0-2 2v11a2 2 0 0 0 2 2h11a2 2 0 0 0 2-2v-7.5" />
                      <path d="m16 3 5 5M10 14l1-4 7-7a2.12 2.12 0 0 1 3 3l-7 7-4 1Z" />
                      <path d="M8 17h5" />
                    </svg>
                    <span className="activity-record-hint">{t('Click to record activity')}</span>
                  </button>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  )
}

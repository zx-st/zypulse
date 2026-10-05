import { useEffect, useState } from 'react'
import { api } from '../api/client.js'
import { translateText } from '../i18n.jsx'

const badgeClass = {
  stable: 'badge-stable',
  increasing: 'badge-increasing',
  decreasing: 'badge-decreasing',
  insufficient_data: 'badge-insufficient',
  below_target: 'badge-below-target',
}

const badgeLabel = {
  stable: 'Stable',
  increasing: 'Increasing',
  decreasing: 'Decreasing',
  insufficient_data: 'Insufficient data',
  below_target: 'Below target',
}

export default function DailyBriefingPage({ userId, language, setPage }) {
  const t = (text) => translateText(language, text)
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [analysis, setAnalysis] = useState(null)

  useEffect(() => {
    const loadBriefing = async () => {
      try {
        const [fasting, evening, medication, activity, meals, preferences] = await Promise.all([
          api.getTrends({ user_id: userId, metric: 'glucose', period: 'fasting', days: 7 }),
          api.getTrends({ user_id: userId, metric: 'glucose', period: 'evening', days: 7 }),
          api.getTrends({ user_id: userId, metric: 'medication', days: 30 }),
          api.getTrends({ user_id: userId, metric: 'activity', days: 30 }),
          api.getHistory({ user_id: userId, category: 'meals', limit: 7 }),
          api.getPreferences(userId),
        ])
        setData({ fasting, evening, medication, activity, meals, preferences })
        const briefing = await api.getDailyBriefing({ user_id: userId, language })
        setAnalysis(briefing)
      } catch (err) {
        setError('Unable to load your daily briefing. Please try again.')
      }
    }
    loadBriefing()
  }, [userId, language])

  if (error) return <div className="error-msg">{error}</div>
  if (!data) return <div className="loading">{t('Preparing your daily briefing...')}</div>

  const { fasting, evening, medication, activity, meals, preferences } = data
  const action = chooseAction({ fasting, evening, medication, activity, meals }, t)
  const signal = getRiskSignal({ fasting, evening, medication, activity, meals }, t)
  const missingProfileItems = getMissingHealthProfileItems(preferences)

  return (
    <div className="daily-briefing">
      <section className="daily-welcome">
        <div>
          <p className="daily-eyebrow">{t('YOUR DAILY BRIEFING')}</p><h1>{t('Good day, Mr Tan')}</h1><p>{t('Your verified self-care snapshot, in one place.')}</p>
        </div>
      </section>

      <section className={`risk-card ${signal.tone}`}>
        <div className="risk-dial" aria-label={`Record-based attention level: ${signal.label}`}>
          <div className="risk-dial-inner"><strong>{signal.label}</strong><span>{t('attention')}</span></div>
        </div>
        <div className="risk-copy">
          <p className="daily-eyebrow">{t("TODAY'S HEALTH RISK CHECK")}</p>
          <h2>{signal.headline}</h2>
          <p>{signal.detail}</p>
        </div>
      </section>

      <section className="daily-action-card">
        <div className="daily-action-label">{t('ONE SMALL THING FOR TODAY')}</div>
        <h2>{action.title}</h2>
        <p>{action.description}</p>
        <button className="btn btn-primary daily-action-button" onClick={() => setPage(action.page)}>{action.button}</button>
      </section>

      {missingProfileItems.length > 0 && (
        <section className="daily-profile-reminder">
          <div><strong>{t('Make your briefing more personal')}</strong><p>Add: {missingProfileItems.join(', ')}.</p></div><button onClick={() => setPage('profile')}>{t('Complete profile')}</button>
        </section>
      )}

      <section className="daily-ai-card">
        <div className="daily-ai-heading">
          <div className="card-title"><span className="daily-ai-icon">✦</span>{t('AI briefing')}</div><span className="daily-ai-source">{t('Based on your records')}</span>
        </div>
        <BriefingInsight text={analysis?.analysis || 'Preparing your data-based briefing...'} />
        {analysis?.safety_status && analysis.safety_status !== 'allow' && <span className={`chat-safety-badge safety-${analysis.safety_status}`}>{analysis.safety_status === 'fallback' ? 'Deterministic mode' : 'Safety filtered'}</span>}
      </section>

      <section className="card daily-continue-card">
        <div className="card-title">{t('Continue with ZyPulse')}</div>
        <div className="daily-links">
          <button onClick={() => setPage('log')}><span className="quick-action-icon">🩸</span><span>{t('Log a reading')}</span></button><button onClick={() => setPage('meals')}><span className="quick-action-icon">🍽️</span><span>{t('Add a meal')}</span></button><button onClick={() => setPage('trends')}><span className="quick-action-icon">📈</span><span>{t('View trends')}</span></button><button onClick={() => setPage('chat')}><span className="quick-action-icon">💬</span><span>{t('Ask Coach')}</span></button>
        </div>
      </section>

      <section className="card daily-record-card">
        <div className="card-title">{t('Your record at a glance')}</div><BriefingTrend label={t('Fasting glucose · 7 days')} value={fasting.average == null ? '—' : `${fasting.average} mmol/L`} trend={fasting} /><BriefingTrend label={t('Medication · 30 days')} value={medication.adherence_rate == null ? '—' : `${medication.adherence_rate}%`} trend={medication} /><BriefingTrend label={t('Activity · 30 days')} value={`${activity.activity_days || 0} ${t('active days')}`} trend={activity} /><button className="daily-text-link" onClick={() => setPage('trends')}>{t('See full trends →')}</button>
      </section>

      <section className="daily-why-card">
        <div className="card-title">{t('Why this next step')}</div>
        <p>{action.rationale}</p>
        <p className="daily-limitation"><strong>{t('What this cannot tell us:')}</strong> {action.limitation}</p>
      </section>

    </div>
  )
}

// This is a record-based attention signal, never a medical risk assessment.
function getRiskSignal({ fasting, evening, medication, activity, meals }, t) {
  const needsAttention = fasting.trend_direction === 'increasing' || medication.trend_direction === 'below_target' || medication.missed_doses > 0
  const limitedData = fasting.insufficient_data || evening.insufficient_data || medication.insufficient_data || activity.insufficient_data || !meals.length
  if (needsAttention) return { tone: 'attention', label: t('Check in'), headline: t('A few records need your attention'), detail: t('This signal is based on what you logged, not a medical assessment.') }
  if (limitedData) return { tone: 'limited', label: t('Building'), headline: t('More records will make this clearer'), detail: t('Add your next routine record to strengthen your self-care picture.') }
  return { tone: 'steady', label: t('Steady'), headline: t('Your recent record looks consistent'), detail: t('Keep logging to maintain a clear picture for yourself and your care team.') }
}

function getMissingHealthProfileItems(preferences = {}) {
  const fields = [
    ['goals', 'a self-care goal'],
    ['barriers', 'a routine barrier'],
    ['activity_types', 'activity preferences'],
    ['availability', 'available times'],
    ['location_area', 'your general area'],
  ]
  return fields.filter(([key]) => !preferences[key] || (Array.isArray(preferences[key]) && preferences[key].length === 0)).map(([, label]) => label)
}

function BriefingTrend({ label, value, trend }) {
  const direction = trend.trend_direction || 'insufficient_data'
  return <div className="trend-row"><span className="trend-label">{label}</span><span className="trend-value">{value} <span className={`trend-badge ${badgeClass[direction] || 'badge-insufficient'}`}>{badgeLabel[direction] || direction}</span></span></div>
}

function BriefingInsight({ text }) {
  const match = text.match(/^(.+?[.!?])\s*(.*)$/s)
  if (!match) return <p className="daily-ai-insight">{text}</p>
  return <div className="daily-ai-insight"><strong>{match[1]}</strong>{match[2] && <span>{match[2]}</span>}</div>
}

function chooseAction({ fasting, evening, medication, activity, meals }, t) {
  if (!meals.length) return {
    title: t('Add your next meal'), button: t('Log a meal'), page: 'meals', description: t('A quick meal entry can make your self-care record more complete.'),
    rationale: t('There are no recent meal records available, while other parts of your routine have some data.'), limitation: t('A meal record helps build context, but it cannot show that a meal caused any glucose change.'),
  }
  if (evening.readings_count < 3) return {
    title: t('Log an evening glucose reading'), button: t('Log a reading'), page: 'log', description: t('If it is part of your usual routine, add your next evening reading.'),
    rationale: `Only ${evening.readings_count} recent evening glucose reading${evening.readings_count === 1 ? ' is' : 's are'} available; three are needed for a 7-day trend.`,
    limitation: t('With limited readings, ZyPulse cannot identify a reliable trend or explain why a value changed.'),
  }
  if (medication.missed_doses > 0) return {
    title: t('Record your next medication status'), button: t('Log medication'), page: 'log', description: t('A simple status check keeps your record ready for your next care conversation.'),
    rationale: t('missed dose') === '漏服次数' ? `近期记录中有 ${medication.missed_doses} 次漏服。这只是记录提醒，并非治疗建议。` : `${medication.missed_doses} missed dose${medication.missed_doses === 1 ? '' : 's'} appear in the recent record. This is a prompt to log, not a treatment recommendation.`,
    limitation: t('This record cannot explain why a dose was missed or whether any health outcome was caused by it.'),
  }
  return {
    title: t('Keep your routine visible'), button: t('Add a record'), page: 'log', description: t('Add your next planned self-care record when it is convenient for you.'),
    rationale: `Your recent record includes ${fasting.readings_count} fasting readings, ${medication.taken_doses || 0} medication statuses, and ${activity.activity_days || 0} active days.`,
    limitation: t('These records describe what was logged; they do not diagnose a condition or establish cause and effect.'),
  }
}

import { useEffect, useState } from 'react'
import { api } from '../api/client.js'

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

export default function DailyBriefingPage({ userId, setPage }) {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    const loadBriefing = async () => {
      try {
        const [fasting, evening, medication, activity, meals] = await Promise.all([
          api.getTrends({ user_id: userId, metric: 'glucose', period: 'fasting', days: 7 }),
          api.getTrends({ user_id: userId, metric: 'glucose', period: 'evening', days: 7 }),
          api.getTrends({ user_id: userId, metric: 'medication', days: 30 }),
          api.getTrends({ user_id: userId, metric: 'activity', days: 30 }),
          api.getHistory({ user_id: userId, category: 'meals', limit: 7 }),
        ])
        setData({ fasting, evening, medication, activity, meals })
      } catch (err) {
        setError('Unable to load your daily briefing. Please try again.')
      }
    }
    loadBriefing()
  }, [userId])

  if (error) return <div className="error-msg">{error}</div>
  if (!data) return <div className="loading">Preparing your daily briefing...</div>

  const { fasting, evening, medication, activity, meals } = data
  const action = chooseAction({ fasting, evening, medication, activity, meals })
  const signal = getRiskSignal({ fasting, evening, medication, activity, meals })

  return (
    <div className="daily-briefing">
      <section className="daily-welcome">
        <div>
          <p className="daily-eyebrow">YOUR DAILY BRIEFING</p>
          <h1>Good day, Mr Tan</h1>
          <p>Your verified self-care snapshot, in one place.</p>
        </div>
      </section>

      <section className={`risk-card ${signal.tone}`}>
        <div className="risk-dial" aria-label={`Record-based attention level: ${signal.label}`}>
          <div className="risk-dial-inner"><strong>{signal.label}</strong><span>attention</span></div>
        </div>
        <div className="risk-copy">
          <p className="daily-eyebrow">TODAY'S HEALTH RISK CHECK</p>
          <h2>{signal.headline}</h2>
          <p>{signal.detail}</p>
        </div>
      </section>

      <section className="daily-action-card">
        <div className="daily-action-label">ONE SMALL THING FOR TODAY</div>
        <h2>{action.title}</h2>
        <p>{action.description}</p>
        <button className="btn btn-primary daily-action-button" onClick={() => setPage(action.page)}>{action.button}</button>
      </section>

      <section className="card">
        <div className="card-title">Continue with ZyPulse</div>
        <div className="daily-links">
          <button onClick={() => setPage('log')}>Log a reading</button>
          <button onClick={() => setPage('meals')}>Add a meal</button>
          <button onClick={() => setPage('trends')}>View trends</button>
          <button onClick={() => setPage('chat')}>Ask Coach</button>
        </div>
      </section>

      <section className="card">
        <div className="card-title">Your record at a glance</div>
        <BriefingTrend label="Fasting glucose · 7 days" value={fasting.average == null ? '—' : `${fasting.average} mmol/L`} trend={fasting} />
        <BriefingTrend label="Medication · 30 days" value={medication.adherence_rate == null ? '—' : `${medication.adherence_rate}%`} trend={medication} />
        <BriefingTrend label="Activity · 30 days" value={`${activity.activity_days || 0} active days`} trend={activity} />
        <button className="daily-text-link" onClick={() => setPage('trends')}>See full trends →</button>
      </section>

      <section className="daily-why-card">
        <div className="card-title">Why this next step</div>
        <p>{action.rationale}</p>
        <p className="daily-limitation"><strong>What this cannot tell us:</strong> {action.limitation}</p>
      </section>

    </div>
  )
}

// This is a record-based attention signal, never a medical risk assessment.
function getRiskSignal({ fasting, evening, medication, activity, meals }) {
  const needsAttention = fasting.trend_direction === 'increasing' || medication.trend_direction === 'below_target' || medication.missed_doses > 0
  const limitedData = fasting.insufficient_data || evening.insufficient_data || medication.insufficient_data || activity.insufficient_data || !meals.length
  if (needsAttention) return { tone: 'attention', label: 'Check in', headline: 'A few records need your attention', detail: 'This signal is based on what you logged, not a medical assessment.' }
  if (limitedData) return { tone: 'limited', label: 'Building', headline: 'More records will make this clearer', detail: 'Add your next routine record to strengthen your self-care picture.' }
  return { tone: 'steady', label: 'Steady', headline: 'Your recent record looks consistent', detail: 'Keep logging to maintain a clear picture for yourself and your care team.' }
}

function BriefingTrend({ label, value, trend }) {
  const direction = trend.trend_direction || 'insufficient_data'
  return <div className="trend-row"><span className="trend-label">{label}</span><span className="trend-value">{value} <span className={`trend-badge ${badgeClass[direction] || 'badge-insufficient'}`}>{badgeLabel[direction] || direction}</span></span></div>
}

function chooseAction({ fasting, evening, medication, activity, meals }) {
  if (!meals.length) return {
    title: 'Add your next meal', button: 'Log a meal', page: 'meals',
    description: 'A quick meal entry can make your self-care record more complete.',
    rationale: 'There are no recent meal records available, while other parts of your routine have some data.',
    limitation: 'A meal record helps build context, but it cannot show that a meal caused any glucose change.',
  }
  if (evening.readings_count < 3) return {
    title: 'Log an evening glucose reading', button: 'Log a reading', page: 'log',
    description: 'If it is part of your usual routine, add your next evening reading.',
    rationale: `Only ${evening.readings_count} recent evening glucose reading${evening.readings_count === 1 ? ' is' : 's are'} available; three are needed for a 7-day trend.`,
    limitation: 'With limited readings, ZyPulse cannot identify a reliable trend or explain why a value changed.',
  }
  if (medication.missed_doses > 0) return {
    title: 'Record your next medication status', button: 'Log medication', page: 'log',
    description: 'A simple status check keeps your record ready for your next care conversation.',
    rationale: `${medication.missed_doses} missed dose${medication.missed_doses === 1 ? '' : 's'} appear in the recent record. This is a prompt to log, not a treatment recommendation.`,
    limitation: 'This record cannot explain why a dose was missed or whether any health outcome was caused by it.',
  }
  return {
    title: 'Keep your routine visible', button: 'Add a record', page: 'log',
    description: 'Add your next planned self-care record when it is convenient for you.',
    rationale: `Your recent record includes ${fasting.readings_count} fasting readings, ${medication.taken_doses || 0} medication statuses, and ${activity.activity_days || 0} active days.`,
    limitation: 'These records describe what was logged; they do not diagnose a condition or establish cause and effect.',
  }
}

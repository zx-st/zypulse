import { useEffect, useState } from 'react'
import ChatPage from './pages/ChatPage.jsx'
import LogPage from './pages/LogPage.jsx'
import TrendsPage from './pages/TrendsPage.jsx'
import ActivitiesPage from './pages/ActivitiesPage.jsx'
import ProfilePage from './pages/ProfilePage.jsx'
import HistoryPage from './pages/HistoryPage.jsx'
import NotificationsPage from './pages/NotificationsPage.jsx'
import SummaryPage from './pages/SummaryPage.jsx'
import MorePage from './pages/MorePage.jsx'
import MealLogPage from './pages/MealLogPage.jsx'
import DailyBriefingPage from './pages/DailyBriefingPage.jsx'
import Header from './components/Header.jsx'
import NavBar from './components/NavBar.jsx'
import LanguageWelcome from './components/LanguageWelcome.jsx'
import { translate } from './i18n.jsx'
import { api } from './api/client.js'

const DEMO_USER = 'mr_tan_001'

export default function App() {
  const [page, updatePage] = useState('daily')
  const [activityLocation, setActivityLocation] = useState(null)
  const [activityDraft, setActivityDraft] = useState(null)
  // Which Explore tab is showing: 'events' (Healthy 365) or 'facilities'.
  const [exploreTab, setExploreTab] = useState('events')
  const setPage = (nextPage) => {
    setActivityLocation(null)
    setActivityDraft(null)
    updatePage(nextPage)
  }
  // Today shortcuts open Explore directly on the requested tab.
  const openExplore = (tab) => {
    setExploreTab(tab)
    setPage('activities')
  }
  const recordActivity = (facility) => {
    setActivityLocation(facility.title || facility.location || '')
    updatePage('log')
  }
  // Healthy 365 demo event -> pre-filled (still editable) Activity Log entry.
  const addToActivityLog = (event, status = 'planned') => {
    setActivityDraft({
      activity_type: event.activity_type,
      duration_min: event.duration_min ?? '',
      location: event.location_area,
      recorded_date: event.date,
      source_event_id: event.event_id,
      status,
    })
    setActivityLocation(null)
    updatePage('log')
  }
  const savedLanguage = localStorage.getItem('zypulse-language')
  const initialLanguage = ['en', 'zh'].includes(savedLanguage) ? savedLanguage : 'en'
  const [language, setLanguage] = useState(initialLanguage)
  const [languageChosen, setLanguageChosen] = useState(() => Boolean(['en', 'zh'].includes(savedLanguage)))
  const [largerText, setLargerText] = useState(false)

  useEffect(() => {
    api.getPreferences(DEMO_USER).then((prefs) => setLargerText(Boolean(prefs.accessibility_json?.larger_text))).catch(() => setLargerText(false))
  }, [])
  useEffect(() => { document.documentElement.classList.toggle('a11y-large-text', largerText) }, [largerText])

  const chooseLanguage = (code) => {
    setLanguage(code)
    localStorage.setItem('zypulse-language', code)
    setLanguageChosen(true)
  }
  const updateLanguage = (code) => {
    setLanguage(code)
    localStorage.setItem('zypulse-language', code)
  }

  const pages = {
    daily: <DailyBriefingPage userId={DEMO_USER} language={language} setPage={setPage} onOpenExplore={openExplore} />,
    chat: <ChatPage userId={DEMO_USER} language={language} />,
    record: <LogPage userId={DEMO_USER} language={language} initialTab="glucose" />,
    log: <LogPage userId={DEMO_USER} language={language} initialTab={activityLocation !== null || activityDraft !== null ? 'activity' : 'glucose'} initialLocation={activityLocation ?? ''} activityDraft={activityDraft} />, trends: <TrendsPage userId={DEMO_USER} language={language} />, activities: <ActivitiesPage userId={DEMO_USER} language={language} onRecordActivity={recordActivity} onAddToActivityLog={addToActivityLog} exploreTab={exploreTab} onExploreTabChange={setExploreTab} />, meals: <LogPage userId={DEMO_USER} language={language} initialTab="meals" />,
    more: <MorePage language={language} setPage={setPage} />,
    profile: <ProfilePage userId={DEMO_USER} language={language} setLanguage={updateLanguage} setPage={setPage} setLargerText={setLargerText} />,
    history: <HistoryPage userId={DEMO_USER} language={language} />, notifications: <NotificationsPage userId={DEMO_USER} language={language} setPage={setPage} />,
    summary: <SummaryPage userId={DEMO_USER} language={language} setPage={setPage} />,
  }

  return (
    <div className="app" lang={language}>
      {!languageChosen ? <LanguageWelcome onContinue={chooseLanguage} /> : <>
      <a className="skip-link" href="#main-content">Skip to content</a>
      <Header language={language} onLanguageChange={updateLanguage} onOpenNotifications={() => setPage('notifications')} />
      <div className="safety-banner">
        {translate(language, 'safety')}
      </div>
      <main id="main-content" className={`main page-${page}`}>
        {pages[page]}
      </main>
      <NavBar page={page} setPage={setPage} language={language} />
      </>}
    </div>
  )
}

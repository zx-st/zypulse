import { useState } from 'react'
import ChatPage from './pages/ChatPage.jsx'
import LogPage from './pages/LogPage.jsx'
import TrendsPage from './pages/TrendsPage.jsx'
import ActivitiesPage from './pages/ActivitiesPage.jsx'
import ProfilePage from './pages/ProfilePage.jsx'
import HistoryPage from './pages/HistoryPage.jsx'
import NotificationsPage from './pages/NotificationsPage.jsx'
import SummaryPage from './pages/SummaryPage.jsx'
import MealLogPage from './pages/MealLogPage.jsx'
import DailyBriefingPage from './pages/DailyBriefingPage.jsx'
import Header from './components/Header.jsx'
import NavBar from './components/NavBar.jsx'
import LanguageWelcome from './components/LanguageWelcome.jsx'
import { translate } from './i18n.jsx'

const DEMO_USER = 'mr_tan_001'

export default function App() {
  const [page, setPage] = useState('daily')
  const savedLanguage = localStorage.getItem('zypulse-language')
  const initialLanguage = ['en', 'zh'].includes(savedLanguage) ? savedLanguage : 'en'
  const [language, setLanguage] = useState(initialLanguage)
  const [languageChosen, setLanguageChosen] = useState(() => Boolean(['en', 'zh'].includes(savedLanguage)))

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
    daily: <DailyBriefingPage userId={DEMO_USER} language={language} setPage={setPage} />,
    chat: <ChatPage userId={DEMO_USER} language={language} />,
    log: <LogPage userId={DEMO_USER} language={language} />, trends: <TrendsPage userId={DEMO_USER} language={language} />, activities: <ActivitiesPage userId={DEMO_USER} language={language} />, meals: <MealLogPage userId={DEMO_USER} language={language} />,
    profile: <ProfilePage userId={DEMO_USER} language={language} setLanguage={updateLanguage} setPage={setPage} />,
    history: <HistoryPage userId={DEMO_USER} language={language} />, notifications: <NotificationsPage userId={DEMO_USER} language={language} />,
    summary: <SummaryPage userId={DEMO_USER} language={language} setPage={setPage} />,
  }

  return (
    <div className="app" lang={language}>
      {!languageChosen ? <LanguageWelcome onContinue={chooseLanguage} /> : <>
      <Header />
      <div className="safety-banner">
        {translate(language, 'safety')}
      </div>
      <main className={`main page-${page}`}>
        {pages[page]}
      </main>
      <NavBar page={page} setPage={setPage} language={language} />
      </>}
    </div>
  )
}

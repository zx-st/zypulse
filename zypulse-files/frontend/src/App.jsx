import { useState, useEffect } from 'react'
import ChatPage from './pages/ChatPage.jsx'
import LogPage from './pages/LogPage.jsx'
import TrendsPage from './pages/TrendsPage.jsx'
import ActivitiesPage from './pages/ActivitiesPage.jsx'
import ProfilePage from './pages/ProfilePage.jsx'
import HistoryPage from './pages/HistoryPage.jsx'
import NotificationsPage from './pages/NotificationsPage.jsx'
import SummaryPage from './pages/SummaryPage.jsx'
import MealLogPage from './pages/MealLogPage.jsx'
import Header from './components/Header.jsx'
import NavBar from './components/NavBar.jsx'

const DEMO_USER = 'mr_tan_001'

export default function App() {
  const [page, setPage] = useState('chat')
  const [language, setLanguage] = useState('en')

  const pages = {
    chat: <ChatPage userId={DEMO_USER} language={language} />,
    log: <LogPage userId={DEMO_USER} />,
    trends: <TrendsPage userId={DEMO_USER} />,
    activities: <ActivitiesPage userId={DEMO_USER} />,
    meals: <MealLogPage userId={DEMO_USER} />,
    profile: <ProfilePage userId={DEMO_USER} language={language} setLanguage={setLanguage} setPage={setPage} />,
    history: <HistoryPage userId={DEMO_USER} />,
    notifications: <NotificationsPage userId={DEMO_USER} />,
    summary: <SummaryPage userId={DEMO_USER} language={language} setPage={setPage} />,
  }

  return (
    <div className="app">
      <Header language={language} setLanguage={setLanguage} />
      <div className="safety-banner">
        ZyPulse is a self-care support prototype, not a medical device. Consult your doctor for medical advice.
      </div>
      <main className="main">
        {pages[page]}
      </main>
      <NavBar page={page} setPage={setPage} />
    </div>
  )
}

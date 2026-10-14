import { translate } from '../i18n.jsx'

// Five primary destinations only. Everything else (Trends, History, Health Summary,
// Notes for My Doctor, Profile, Notifications) lives in the More list.
// `pages` keeps the correct tab highlighted when a secondary screen is open.
const PRIMARY_ITEMS = [
  { key: 'daily', labelKey: 'today', icon: '☀️', pages: ['daily'] },
  { key: 'record', labelKey: 'record', icon: '📝', pages: ['record', 'log', 'meals'] },
  { key: 'chat', labelKey: 'coach', icon: '💬', pages: ['chat'] },
  { key: 'activities', labelKey: 'explore', icon: '🤝', pages: ['activities'] },
  { key: 'more', labelKey: 'more', icon: '☰', pages: ['more', 'trends', 'history', 'summary', 'profile', 'notifications'] },
]

export default function NavBar({ page, setPage, language }) {
  return (
    <nav className="nav" aria-label="Primary navigation">
      {PRIMARY_ITEMS.map((item) => {
        const active = item.pages.includes(page)
        return (
          <button
            key={item.key}
            type="button"
            className={`nav-item ${active ? 'active' : ''}`}
            aria-current={active ? 'page' : undefined}
            onClick={() => setPage(item.key)}
          >
            <span className="nav-icon" aria-hidden="true">{item.icon}</span>
            {translate(language, item.labelKey)}
          </button>
        )
      })}
    </nav>
  )
}

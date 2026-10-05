import { useTranslation } from '../i18n.jsx'

export default function NavBar({ page, setPage, language }) {
  const t = useTranslation(language)
  const items = [
    { key: 'daily', label: t('today'), icon: '☀️' }, { key: 'chat', label: t('coach'), icon: '💬' }, { key: 'log', label: t('log'), icon: '📝' }, { key: 'meals', label: t('meals'), icon: '🍽️' }, { key: 'trends', label: t('trends'), icon: '📊' }, { key: 'activities', label: t('connect'), icon: '🤝' }, { key: 'history', label: t('history'), icon: '📜' }, { key: 'profile', label: t('profile'), icon: '👤' },
  ]

  return (
    <nav className="nav">
      {items.map(item => (
        <button
          key={item.key}
          className={`nav-item ${page === item.key ? 'active' : ''}`}
          onClick={() => setPage(item.key)}
        >
          <span className="nav-icon">{item.icon}</span>
          {item.label}
        </button>
      ))}
    </nav>
  )
}

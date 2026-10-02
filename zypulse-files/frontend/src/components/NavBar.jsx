export default function NavBar({ page, setPage }) {
  const items = [
    { key: 'chat', label: 'Coach', icon: '💬' },
    { key: 'log', label: 'Log', icon: '📝' },
    { key: 'meals', label: 'Meals', icon: '🍽️' },
    { key: 'trends', label: 'Trends', icon: '📊' },
    { key: 'activities', label: 'Connect', icon: '🤝' },
    { key: 'history', label: 'History', icon: '📜' },
    { key: 'profile', label: 'Profile', icon: '👤' },
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

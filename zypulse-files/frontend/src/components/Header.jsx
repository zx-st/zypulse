export default function Header({ language, setLanguage }) {
  const languages = [
    { code: 'en', label: 'EN' },
    { code: 'zh', label: '中文' },
    { code: 'ms', label: 'MS' },
    { code: 'ta', label: 'TA' },
  ]

  return (
    <header className="header">
      <div className="header-title">
        <span className="header-logo">Z</span>
        ZyPulse
      </div>
      <div className="header-lang">
        {languages.map(l => (
          <button
            key={l.code}
            className={`lang-btn ${language === l.code ? 'active' : ''}`}
            onClick={() => setLanguage(l.code)}
          >
            {l.label}
          </button>
        ))}
      </div>
    </header>
  )
}

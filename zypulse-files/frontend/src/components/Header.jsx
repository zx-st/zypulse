import { LANGUAGES } from '../i18n.jsx'

export default function Header({ language, onLanguageChange, onOpenNotifications }) {
  return (
    <header className="header">
      <div className="header-title">
        <span className="header-logo">Z</span>
        ZyPulse
      </div>
      <div className="header-actions">
        {onLanguageChange && (
          <label className="header-language">
            <span className="sr-only">Language</span>
            <select
              value={language}
              aria-label="Language"
              onChange={(e) => onLanguageChange(e.target.value)}
            >
              {LANGUAGES.map((l) => (
                <option key={l.code} value={l.code}>{l.code === 'en' ? 'EN' : '中文'}</option>
              ))}
            </select>
          </label>
        )}
        {onOpenNotifications && (
          <button
            type="button"
            className="header-icon-btn"
            aria-label="Notifications"
            onClick={onOpenNotifications}
          >
            <span aria-hidden="true">🔔</span>
          </button>
        )}
      </div>
    </header>
  )
}

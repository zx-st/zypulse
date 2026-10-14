import { useState } from 'react'
import { translate } from '../i18n.jsx'

// Compact single-column list. No decorative cards, no duplicate entries, no
// placeholder privacy controls — the sharing item is informational text only.
export default function MorePage({ language, setPage }) {
  const [sharingOpen, setSharingOpen] = useState(false)

  const rows = [
    { icon: '📊', label: translate(language, 'trends'), page: 'trends' },
    { icon: '📜', label: translate(language, 'history'), page: 'history' },
    { icon: '🩺', label: translate(language, 'healthSummaryShort'), page: 'summary' },
    { icon: '✍️', label: translate(language, 'notesForDoctor'), page: 'summary' },
  ]

  const accountRows = [
    { icon: '👤', label: translate(language, 'profile'), page: 'profile' },
    { icon: '🔔', label: translate(language, 'notifications'), page: 'notifications' },
  ]

  const renderRow = (row) => (
    <button key={row.label} type="button" className="more__item" onClick={() => setPage(row.page)}>
      <span className="more__icon" aria-hidden="true">{row.icon}</span>
      <span>{row.label}</span>
      <span className="more__chevron" aria-hidden="true">›</span>
    </button>
  )

  return (
    <div className="more">
      <div className="more__label">{translate(language, 'more')}</div>
      <div className="more__list">{rows.map(renderRow)}</div>

      <div className="more__label" style={{ marginTop: 20 }}>{translate(language, 'account')}</div>
      <div className="more__list">{accountRows.map(renderRow)}</div>

      <div className="more__footer">
        <button type="button" className="more__footer-link" onClick={() => setSharingOpen(true)}>
          {translate(language, 'sharingTitle')}
        </button>
      </div>

      {sharingOpen && (
        <div className="modal-backdrop" onClick={() => setSharingOpen(false)}>
          <div
            className="modal"
            role="dialog"
            aria-modal="true"
            aria-label={translate(language, 'sharingTitle')}
            onClick={(e) => e.stopPropagation()}
          >
            <h2>{translate(language, 'sharingTitle')}</h2>
            <p>{translate(language, 'sharingBody')}</p>
            <p><strong>{language === 'zh' ? '此信息仅供参考。' : 'This information is for reference only.'}</strong></p>
            <button type="button" className="btn btn-primary" onClick={() => setSharingOpen(false)}>
              {translate(language, 'close')}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

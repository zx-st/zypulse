import { useState } from 'react'
import { LANGUAGES, useTranslation } from '../i18n.jsx'

export default function LanguageWelcome({ onContinue }) {
  const [language, setLanguage] = useState('en')
  const t = useTranslation(language)

  return <main className="language-welcome" lang={language}>
    <div className="language-card">
      <div className="language-logo">Z</div>
      <h1>{t('welcome')}</h1>
      <h2>{t('chooseLanguage')}</h2>
      <p>{t('languageIntro')}</p>
      <div className="language-options">
        {LANGUAGES.map(item => <button key={item.code} className={language === item.code ? 'selected' : ''} onClick={() => setLanguage(item.code)}>{item.label}</button>)}
      </div>
      <button className="btn btn-primary language-continue" onClick={() => onContinue(language)}>{t('continue')}</button>
    </div>
  </main>
}

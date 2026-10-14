import { useState, useEffect, useRef } from 'react'
import { api } from '../api/client.js'
import { translateText } from '../i18n.jsx'

const INITIAL_GREETING = {
  role: 'assistant',
  content: "Hello Mr Tan! I'm ZyPulse, your self-care companion. I can help you understand your glucose trends, track your medication, and support your daily self-care routine. How can I help you today?",
}

export default function ChatPage({ userId, language }) {
  const t = (text) => translateText(language, text)
  const [messages, setMessages] = useState(() => [{ ...INITIAL_GREETING, content: translateText(language, INITIAL_GREETING.content) }])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [usage, setUsage] = useState(null)
  const [whyOpen, setWhyOpen] = useState({})
  const [savedNote, setSavedNote] = useState(false)
  const [noteError, setNoteError] = useState(null)
  const [savingNote, setSavingNote] = useState(false)
  const messagesEndRef = useRef(null)

  const refreshUsage = async () => {
    try { setUsage(await api.getAiUsage(userId)) } catch { /* coach remains usable if quota display is unavailable */ }
  }

  // Load conversation history on mount
  useEffect(() => {
    // For MVP, we start with the greeting. History is in the backend.
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => { refreshUsage() }, [userId])

  useEffect(() => {
    setMessages(current => current.length === 1 && current[0].role === 'assistant'
      ? [{ ...INITIAL_GREETING, content: translateText(language, INITIAL_GREETING.content) }]
      : current)
  }, [language])

  const handleSend = async () => {
    if (!input.trim() || loading) return

    const userMessage = { role: 'user', content: input.trim() }
    setMessages(prev => [...prev, userMessage])
    setInput('')
    setLoading(true)
    setError(null)

    try {
      const result = await api.chat({
        user_id: userId,
        message: userMessage.content,
        language: language,
      })

      const assistantMessage = {
        role: 'assistant',
        content: result.response,
        safetyStatus: result.safety_status,
      }
      setMessages(prev => [...prev, assistantMessage])
    } catch (err) {
      setError('Unable to reach ZyPulse. Please try again.')
    } finally {
      setLoading(false)
      refreshUsage()
    }
  }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  // The safety engine itself is untouched — this only makes its outcome legible.
  const saveQuestionForDoctor = async (question) => {
    setSavingNote(true)
    setNoteError(null)
    try {
      await api.createNote({
        user_id: userId,
        content: `Question for my doctor: ${question}`.slice(0, 1000),
        include_in_visit: true,
      })
      setSavedNote(true)
    } catch {
      setNoteError(t('Could not save that question. Please try again.'))
    } finally {
      setSavingNote(false)
    }
  }

  const getSafetyBadge = (status, index) => {
    if (!status || status === 'allow') return null
    const labels = {
      blocked: 'Safety redirect',
      fallback: 'Deterministic mode',
      filtered: 'Safety filtered',
    }
    const isBlocked = status === 'blocked'
    const question = messages[index - 1]?.content || ''
    const open = Boolean(whyOpen[index])
    return (
      <div className={`coach-safety ${isBlocked ? '' : 'coach-safety--fallback'}`} role="note">
        <span className="coach-safety__icon" aria-hidden="true">{isBlocked ? '⛔' : 'ℹ️'}</span>
        <div className="coach-safety__body">
          <span className={`chat-safety-badge safety-${status}`}>{labels[status] || status}</span>
          <div className="coach-safety__actions">
            <button
              type="button"
              className="coach-safety__why"
              aria-expanded={open}
              onClick={() => setWhyOpen((s) => ({ ...s, [index]: !s[index] }))}
            >
              {t('Why was this redirected?')}
            </button>
            {isBlocked && (
              <button
                type="button"
                className="btn btn-primary btn-sm"
                disabled={savingNote}
                onClick={() => saveQuestionForDoctor(question)}
              >
                {t('Save question for my doctor')}
              </button>
            )}
          </div>
          {open && (
            <div className="coach-safety__reason">
              {isBlocked
                ? t('Questions about changing your medication, or about diagnosis and cause, are redirected. ZyPulse cannot answer them safely — please ask your doctor.')
                : t('The AI answer is unavailable, so this reply uses information calculated directly from your own records.')}
            </div>
          )}
          {isBlocked && savedNote && <div className="coach-safety__reason">{t('Question saved to Notes for My Doctor.')}</div>}
          {isBlocked && noteError && <div className="coach-safety__reason">{noteError}</div>}
        </div>
      </div>
    )
  }

  return (
    <div className="chat-container">
      {usage && <div className="chat-usage" aria-live="polite">
        {language === 'zh'
          ? `今日 AI 助手剩余 ${usage.chat.remaining_today} / ${usage.chat.daily_limit} 次`
          : `${usage.chat.remaining_today} / ${usage.chat.daily_limit} AI questions remaining today`}
      </div>}
      <div className="chat-messages">
        {messages.map((msg, idx) => (
          <div key={idx} className={`chat-msg ${msg.role}`}>
            {msg.content}
            {msg.safetyStatus && getSafetyBadge(msg.safetyStatus, idx)}
          </div>
        ))}
        {loading && (
          <div className="chat-msg assistant">
            <span style={{ opacity: 0.6 }}>{t('ZyPulse is thinking...')}</span>
          </div>
        )}
        {error && <div className="error-msg">{error}</div>}
        <div ref={messagesEndRef} />
      </div>

      <div className="chat-input-area">
        <input
          className="chat-input"
          type="text"
          placeholder={t('Ask about your trends, log a reading, or get self-care tips...')}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={handleKeyPress}
          disabled={loading}
          maxLength={500}
        />
        <button
          className="chat-send"
          onClick={handleSend}
          disabled={loading || !input.trim()}
        >
          ➤
        </button>
      </div>
    </div>
  )
}

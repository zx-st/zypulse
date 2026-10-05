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
  const messagesEndRef = useRef(null)

  // Load conversation history on mount
  useEffect(() => {
    // For MVP, we start with the greeting. History is in the backend.
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

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
    }
  }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const getSafetyBadge = (status) => {
    if (!status || status === 'allow') return null
    const labels = {
      blocked: 'Safety redirect',
      fallback: 'Deterministic mode',
      filtered: 'Safety filtered',
    }
    return (
      <span className={`chat-safety-badge safety-${status}`}>
        {labels[status] || status}
      </span>
    )
  }

  return (
    <div className="chat-container">
      <div className="chat-messages">
        {messages.map((msg, idx) => (
          <div key={idx} className={`chat-msg ${msg.role}`}>
            {msg.content}
            {msg.safetyStatus && getSafetyBadge(msg.safetyStatus)}
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

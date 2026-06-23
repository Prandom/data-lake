import { useState, useRef, useEffect } from 'react'
import { Send, Sparkles, Bot, User, Loader2, Zap } from 'lucide-react'
import { cn } from '@/lib/utils'
import { queryAgent } from '@/lib/api'

function ChatMessage({ message, index }) {
  const isUser = message.role === 'user'

  return (
    <div
      style={{
        display: 'flex',
        gap: '1rem',
        flexDirection: isUser ? 'row-reverse' : 'row',
        animation: 'fade-in 0.35s ease-out forwards',
        animationDelay: `${Math.min(index * 30, 150)}ms`,
        opacity: 0,
      }}
    >
      {/* Avatar */}
      <div style={{
        width: '36px', height: '36px',
        borderRadius: '50%',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        flexShrink: 0,
        marginTop: '2px',
        background: isUser
          ? 'linear-gradient(135deg, oklch(0.56 0.22 275 / 0.35), oklch(0.57 0.22 310 / 0.25))'
          : 'var(--color-surface-3)',
        border: isUser
          ? '1px solid oklch(0.56 0.22 275 / 0.3)'
          : '1px solid var(--color-border)',
      }}>
        {isUser
          ? <User size={15} style={{ color: 'oklch(0.78 0.15 275)' }} />
          : <Bot size={15} style={{ color: 'var(--color-text-muted)' }} />
        }
      </div>

      {/* Bubble */}
      <div style={{
        maxWidth: '72%',
        padding: '0.875rem 1.125rem',
        borderRadius: isUser ? '1.25rem 1.25rem 0.375rem 1.25rem' : '1.25rem 1.25rem 1.25rem 0.375rem',
        fontSize: '0.9375rem',
        lineHeight: 1.65,
        color: isUser ? '#fff' : 'var(--color-text-primary)',
        background: isUser
          ? 'linear-gradient(135deg, oklch(0.54 0.22 275), oklch(0.52 0.22 305))'
          : 'var(--color-surface-2)',
        border: isUser ? 'none' : '1px solid var(--color-border)',
        boxShadow: isUser
          ? '0 4px 16px oklch(0.56 0.22 275 / 0.25)'
          : '0 2px 8px oklch(0 0 0 / 0.2)',
      }}>
        {message.content}

        {/* Sources */}
        {message.sources?.length > 0 && (
          <div style={{
            marginTop: '0.875rem',
            paddingTop: '0.75rem',
            borderTop: '1px solid oklch(1 0 0 / 0.1)',
          }}>
            <p style={{ fontSize: '0.6875rem', fontWeight: 600, color: 'oklch(0.75 0 0)', marginBottom: '0.5rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Sources
            </p>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.375rem' }}>
              {message.sources.map((source, i) => (
                <span key={i} style={{
                  padding: '0.25rem 0.625rem',
                  borderRadius: '9999px',
                  fontSize: '0.75rem',
                  background: 'oklch(0 0 0 / 0.2)',
                  color: 'oklch(0.85 0.05 275)',
                  border: '1px solid oklch(1 0 0 / 0.12)',
                }}>{source}</span>
              ))}
            </div>
          </div>
        )}

        {/* Meta */}
        {message.provider && (
          <p style={{
            marginTop: '0.5rem',
            fontSize: '0.6875rem',
            color: isUser ? 'oklch(0.85 0.08 275)' : 'var(--color-text-faint)',
            display: 'flex',
            alignItems: 'center',
            gap: '0.25rem',
          }}>
            <Zap size={10} /> via {message.provider} · {message.iterations} step{message.iterations !== 1 ? 's' : ''}
          </p>
        )}
      </div>
    </div>
  )
}

function TypingIndicator() {
  return (
    <div style={{
      display: 'flex',
      gap: '1rem',
      animation: 'fade-in 0.3s ease-out forwards',
    }}>
      <div style={{
        width: '36px', height: '36px',
        borderRadius: '50%',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        flexShrink: 0,
        background: 'var(--color-surface-3)',
        border: '1px solid var(--color-border)',
      }}>
        <Bot size={15} style={{ color: 'var(--color-text-muted)' }} />
      </div>
      <div style={{
        padding: '0.875rem 1.125rem',
        borderRadius: '1.25rem 1.25rem 1.25rem 0.375rem',
        background: 'var(--color-surface-2)',
        border: '1px solid var(--color-border)',
        display: 'flex',
        alignItems: 'center',
        gap: '0.375rem',
      }}>
        {[0, 150, 300].map(delay => (
          <div key={delay} style={{
            width: '8px', height: '8px',
            borderRadius: '50%',
            background: 'var(--color-text-muted)',
            animation: 'pulse-soft 1.4s ease-in-out infinite',
            animationDelay: `${delay}ms`,
          }} />
        ))}
      </div>
    </div>
  )
}

const SUGGESTIONS = [
  'What are my notes on system design?',
  'Summarize my most recent documents',
  'What files mention machine learning?',
  'Find my notes about database indexing',
]

export default function ChatPage() {
  const [messages, setMessages] = useState([])
  const [input, setInput]       = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const messagesEndRef = useRef(null)
  const inputRef       = useRef(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isLoading])

  useEffect(() => { inputRef.current?.focus() }, [])

  async function handleSubmit(e) {
    e.preventDefault()
    const trimmed = input.trim()
    if (!trimmed || isLoading) return

    const userMessage = { role: 'user', content: trimmed, id: Date.now() }
    setMessages(prev => [...prev, userMessage])
    setInput('')
    setIsLoading(true)

    try {
      const result = await queryAgent(trimmed)
      const agentMessage = {
        role: 'assistant',
        content: result.response,
        provider: result.provider,
        iterations: result.iterations,
        sources: result.tools_called
          ?.filter(t => t.tool === 'semantic_search')
          ?.flatMap(t => {
            try {
              const parsed = typeof t.result === 'string' ? JSON.parse(t.result) : t.result
              return parsed.results?.map(r => r.path?.split('/').pop()) || []
            } catch { return [] }
          })
          ?.filter(Boolean)
          ?.filter((v, i, a) => a.indexOf(v) === i) || [],
        id: Date.now() + 1,
      }
      setMessages(prev => [...prev, agentMessage])
    } catch (error) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `Sorry, something went wrong: ${error.message}`,
        id: Date.now() + 1,
      }])
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', background: 'var(--color-surface-0)' }}>

      {/* ── Messages area ── */}
      <div style={{ flex: 1, overflowY: 'auto', position: 'relative' }}>
        {messages.length === 0 ? (
          /* Empty state */
          <div style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            height: '100%',
            padding: '3rem 2rem',
            textAlign: 'center',
            animation: 'fade-in 0.5s ease-out forwards',
          }}>
            {/* Glow icon */}
            <div style={{
              width: '80px', height: '80px',
              borderRadius: '22px',
              background: 'linear-gradient(135deg, oklch(0.56 0.22 275 / 0.18), oklch(0.57 0.22 310 / 0.12))',
              border: '1px solid oklch(0.56 0.22 275 / 0.25)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              marginBottom: '1.75rem',
              boxShadow: '0 0 48px oklch(0.56 0.22 275 / 0.2)',
              animation: 'float 4s ease-in-out infinite',
            }}>
              <Sparkles size={34} style={{ color: 'oklch(0.72 0.17 275)' }} />
            </div>

            <h2 style={{
              fontFamily: "'Plus Jakarta Sans', sans-serif",
              fontSize: '1.625rem',
              fontWeight: 700,
              color: 'var(--color-text-primary)',
              marginBottom: '0.625rem',
              letterSpacing: '-0.035em',
            }}>What would you like to know?</h2>
            <p style={{
              fontSize: '0.9375rem',
              color: 'var(--color-text-secondary)',
              maxWidth: '440px',
              lineHeight: 1.65,
              marginBottom: '2.5rem',
            }}>
              Ask me anything about your indexed files. I can search, summarize, and synthesize across all your connected sources.
            </p>

            {/* Suggestion chips */}
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(2, 1fr)',
              gap: '0.75rem',
              maxWidth: '560px',
              width: '100%',
            }}>
              {SUGGESTIONS.map((s, i) => (
                <button
                  key={s}
                  onClick={() => setInput(s)}
                  style={{
                    padding: '0.875rem 1rem',
                    borderRadius: '0.875rem',
                    fontSize: '0.875rem',
                    textAlign: 'left',
                    color: 'var(--color-text-secondary)',
                    background: 'var(--color-surface-1)',
                    border: '1px solid var(--color-border)',
                    cursor: 'pointer',
                    transition: 'all 0.2s ease',
                    lineHeight: 1.5,
                    animation: 'fade-in 0.4s ease-out both',
                    animationDelay: `${0.1 + i * 0.07}s`,
                    opacity: 0,
                  }}
                  onMouseEnter={e => {
                    e.currentTarget.style.borderColor = 'oklch(0.56 0.22 275 / 0.4)'
                    e.currentTarget.style.background = 'var(--color-surface-2)'
                    e.currentTarget.style.color = 'var(--color-text-primary)'
                    e.currentTarget.style.transform = 'translateY(-1px)'
                    e.currentTarget.style.boxShadow = '0 4px 16px oklch(0 0 0 / 0.25)'
                  }}
                  onMouseLeave={e => {
                    e.currentTarget.style.borderColor = 'var(--color-border)'
                    e.currentTarget.style.background = 'var(--color-surface-1)'
                    e.currentTarget.style.color = 'var(--color-text-secondary)'
                    e.currentTarget.style.transform = 'translateY(0)'
                    e.currentTarget.style.boxShadow = 'none'
                  }}
                >{s}</button>
              ))}
            </div>
          </div>
        ) : (
          /* Message list */
          <div style={{
            maxWidth: '760px',
            margin: '0 auto',
            padding: '2.5rem 2rem',
            display: 'flex',
            flexDirection: 'column',
            gap: '1.5rem',
          }}>
            {messages.map((msg, i) => (
              <ChatMessage key={msg.id} message={msg} index={i} />
            ))}
            {isLoading && <TypingIndicator />}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* ── Input bar ── */}
      <div style={{
        borderTop: '1px solid var(--color-border)',
        background: 'oklch(0.12 0.012 265 / 0.90)',
        backdropFilter: 'blur(16px)',
        WebkitBackdropFilter: 'blur(16px)',
        padding: '1.25rem 2rem 1.625rem',
      }}>
        <form
          onSubmit={handleSubmit}
          style={{
            maxWidth: '760px',
            margin: '0 auto',
            display: 'flex',
            alignItems: 'flex-end',
            gap: '0.75rem',
          }}
        >
          <div style={{ flex: 1, position: 'relative' }}>
            <input
              ref={inputRef}
              id="chat-input"
              type="text"
              value={input}
              onChange={e => setInput(e.target.value)}
              placeholder="Ask about your files…"
              disabled={isLoading}
              style={{
                width: '100%',
                padding: '0.9375rem 1.25rem',
                borderRadius: '0.875rem',
                fontSize: '0.9375rem',
                background: 'var(--color-surface-2)',
                border: '1px solid var(--color-border)',
                color: 'var(--color-text-primary)',
                outline: 'none',
                transition: 'all 0.2s ease',
                fontFamily: 'inherit',
                lineHeight: 1.5,
              }}
              onFocus={e => {
                e.target.style.borderColor = 'oklch(0.56 0.22 275 / 0.5)'
                e.target.style.boxShadow = '0 0 0 3px oklch(0.56 0.22 275 / 0.1)'
                e.target.style.background = 'var(--color-surface-3)'
              }}
              onBlur={e => {
                e.target.style.borderColor = 'var(--color-border)'
                e.target.style.boxShadow = 'none'
                e.target.style.background = 'var(--color-surface-2)'
              }}
            />
          </div>

          <button
            type="submit"
            id="chat-submit"
            disabled={!input.trim() || isLoading}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: '48px', height: '48px',
              borderRadius: '0.875rem',
              border: 'none',
              cursor: input.trim() && !isLoading ? 'pointer' : 'not-allowed',
              transition: 'all 0.2s ease',
              flexShrink: 0,
              background: input.trim() && !isLoading
                ? 'linear-gradient(135deg, oklch(0.56 0.22 275), oklch(0.57 0.22 310))'
                : 'var(--color-surface-2)',
              color: input.trim() && !isLoading ? '#fff' : 'var(--color-text-faint)',
              boxShadow: input.trim() && !isLoading ? '0 4px 16px oklch(0.56 0.22 275 / 0.35)' : 'none',
            }}
            onMouseEnter={e => {
              if (input.trim() && !isLoading) e.currentTarget.style.transform = 'scale(1.05)'
            }}
            onMouseLeave={e => { e.currentTarget.style.transform = 'scale(1)' }}
          >
            {isLoading
              ? <Loader2 size={20} style={{ animation: 'spin 0.8s linear infinite' }} />
              : <Send size={18} />
            }
          </button>
        </form>

        <p style={{
          textAlign: 'center',
          fontSize: '0.75rem',
          color: 'var(--color-text-faint)',
          marginTop: '0.625rem',
          maxWidth: '760px',
          margin: '0.625rem auto 0',
        }}>
          Searches across your indexed files and data sources
        </p>
      </div>
    </div>
  )
}

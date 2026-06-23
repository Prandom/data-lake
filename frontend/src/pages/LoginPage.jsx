import { useState } from 'react'
import { Navigate } from 'react-router-dom'
import { Database, Sparkles, Loader2, AlertCircle, ArrowRight } from 'lucide-react'
import { useAuth } from '@/hooks/useAuth'

/**
 * Login page — Firebase Auth integration.
 * Premium redesign: spacious, glassmorphism card, rich visual hierarchy.
 */
export default function LoginPage() {
  const { user, loginWithGoogle, loginWithEmail, signupWithEmail, error, clearError } = useAuth()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [isSignUp, setIsSignUp] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  if (user) return <Navigate to="/" replace />

  async function handleGoogleLogin() {
    try {
      setSubmitting(true)
      await loginWithGoogle()
    } catch {
      // error handled in hook
    } finally {
      setSubmitting(false)
    }
  }

  async function handleEmailSubmit(e) {
    e.preventDefault()
    if (!email.trim() || !password.trim()) return
    try {
      setSubmitting(true)
      if (isSignUp) await signupWithEmail(email, password)
      else          await loginWithEmail(email, password)
    } catch {
      // error handled in hook
    } finally {
      setSubmitting(false)
    }
  }

  function toggleMode() {
    setIsSignUp(p => !p)
    clearError()
  }

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'var(--color-surface-0)',
      position: 'relative',
      overflow: 'hidden',
      padding: '2rem',
    }}>
      {/* Background glow orbs */}
      <div style={{
        position: 'absolute', top: '-20%', left: '50%',
        transform: 'translateX(-50%)',
        width: '900px', height: '500px',
        background: 'radial-gradient(ellipse, oklch(0.56 0.22 275 / 0.12) 0%, transparent 70%)',
        pointerEvents: 'none',
      }} />
      <div style={{
        position: 'absolute', bottom: '0', right: '-10%',
        width: '600px', height: '400px',
        background: 'radial-gradient(ellipse, oklch(0.57 0.22 310 / 0.08) 0%, transparent 70%)',
        pointerEvents: 'none',
      }} />

      {/* Card */}
      <div style={{
        width: '100%',
        maxWidth: '440px',
        position: 'relative',
        zIndex: 1,
      }}>
        {/* Logo section */}
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          marginBottom: '2.5rem',
          animation: 'fade-in 0.5s ease-out forwards',
        }}>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: '72px', height: '72px',
            borderRadius: '20px',
            background: 'linear-gradient(135deg, oklch(0.56 0.22 275 / 0.2), oklch(0.57 0.22 310 / 0.15))',
            border: '1px solid oklch(0.56 0.22 275 / 0.3)',
            marginBottom: '1.25rem',
            boxShadow: '0 0 40px oklch(0.56 0.22 275 / 0.2)',
            animation: 'float 4s ease-in-out infinite',
          }}>
            <Database size={32} style={{ color: 'oklch(0.75 0.15 275)' }} />
          </div>
          <h1 style={{
            fontFamily: "'Plus Jakarta Sans', sans-serif",
            fontSize: '1.875rem',
            fontWeight: 800,
            letterSpacing: '-0.04em',
            color: 'var(--color-text-primary)',
            marginBottom: '0.375rem',
          }}>DataLake</h1>
          <p style={{
            fontSize: '0.9375rem',
            color: 'var(--color-text-secondary)',
            fontWeight: 400,
          }}>Your Personal Knowledge Engine</p>
        </div>

        {/* Glass card */}
        <div style={{
          background: 'oklch(0.14 0.012 265 / 0.85)',
          backdropFilter: 'blur(24px) saturate(1.5)',
          WebkitBackdropFilter: 'blur(24px) saturate(1.5)',
          border: '1px solid var(--color-border)',
          borderRadius: '1.5rem',
          padding: '2.25rem',
          boxShadow: '0 24px 64px oklch(0 0 0 / 0.55), inset 0 1px 0 oklch(1 0 0 / 0.05)',
          animation: 'slide-up 0.5s ease-out 0.1s both',
        }}>
          {/* Card heading */}
          <h2 style={{
            fontFamily: "'Plus Jakarta Sans', sans-serif",
            fontSize: '1.125rem',
            fontWeight: 700,
            color: 'var(--color-text-primary)',
            marginBottom: '0.375rem',
            letterSpacing: '-0.02em',
          }}>
            {isSignUp ? 'Create your account' : 'Welcome back'}
          </h2>
          <p style={{
            fontSize: '0.875rem',
            color: 'var(--color-text-muted)',
            marginBottom: '1.75rem',
          }}>
            {isSignUp
              ? 'Join and start indexing your knowledge'
              : 'Sign in to access your data lake'}
          </p>

          {/* Error banner */}
          {error && (
            <div style={{
              display: 'flex',
              alignItems: 'flex-start',
              gap: '0.625rem',
              padding: '0.875rem 1rem',
              marginBottom: '1.25rem',
              borderRadius: '0.75rem',
              background: 'oklch(0.63 0.22 25 / 0.12)',
              border: '1px solid oklch(0.63 0.22 25 / 0.25)',
              animation: 'fade-in-fast 0.2s ease-out',
            }}>
              <AlertCircle size={16} style={{ color: 'oklch(0.72 0.20 25)', flexShrink: 0, marginTop: '1px' }} />
              <p style={{ fontSize: '0.875rem', color: 'oklch(0.80 0.15 25)', lineHeight: 1.5 }}>{error}</p>
            </div>
          )}

          {/* Google button */}
          <button
            id="login-google"
            type="button"
            onClick={handleGoogleLogin}
            disabled={submitting}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '0.75rem',
              width: '100%',
              padding: '0.8125rem 1.25rem',
              borderRadius: '0.875rem',
              fontSize: '0.9375rem',
              fontWeight: 500,
              color: '#1a1a1a',
              background: '#ffffff',
              border: 'none',
              cursor: submitting ? 'not-allowed' : 'pointer',
              opacity: submitting ? 0.6 : 1,
              transition: 'all 0.15s ease',
              boxShadow: '0 2px 8px oklch(0 0 0 / 0.25)',
              marginBottom: '1.25rem',
            }}
            onMouseEnter={e => { if (!submitting) e.currentTarget.style.background = '#f0f0f0' }}
            onMouseLeave={e => { e.currentTarget.style.background = '#ffffff' }}
          >
            <svg width="20" height="20" viewBox="0 0 24 24">
              <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" />
              <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
              <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
              <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
            </svg>
            Continue with Google
          </button>

          {/* Divider */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.75rem',
            marginBottom: '1.25rem',
          }}>
            <div style={{ flex: 1, height: '1px', background: 'var(--color-border)' }} />
            <span style={{ fontSize: '0.75rem', color: 'var(--color-text-faint)', fontWeight: 500, letterSpacing: '0.05em', textTransform: 'uppercase' }}>or</span>
            <div style={{ flex: 1, height: '1px', background: 'var(--color-border)' }} />
          </div>

          {/* Email form */}
          <form onSubmit={handleEmailSubmit}>
            <div style={{ marginBottom: '0.875rem' }}>
              <label style={{
                display: 'block',
                fontSize: '0.8125rem',
                fontWeight: 500,
                color: 'var(--color-text-secondary)',
                marginBottom: '0.5rem',
                letterSpacing: '-0.01em',
              }}>Email address</label>
              <input
                id="login-email"
                type="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                placeholder="you@example.com"
                required
                autoComplete="email"
                style={{
                  width: '100%',
                  padding: '0.8125rem 1rem',
                  borderRadius: '0.75rem',
                  fontSize: '0.9375rem',
                  background: 'var(--color-surface-2)',
                  border: '1px solid var(--color-border)',
                  color: 'var(--color-text-primary)',
                  outline: 'none',
                  transition: 'all 0.15s ease',
                  fontFamily: 'inherit',
                }}
                onFocus={e => {
                  e.target.style.borderColor = 'oklch(0.56 0.22 275 / 0.6)'
                  e.target.style.boxShadow = '0 0 0 3px oklch(0.56 0.22 275 / 0.12)'
                  e.target.style.background = 'var(--color-surface-3)'
                }}
                onBlur={e => {
                  e.target.style.borderColor = 'var(--color-border)'
                  e.target.style.boxShadow = 'none'
                  e.target.style.background = 'var(--color-surface-2)'
                }}
              />
            </div>

            <div style={{ marginBottom: '1.5rem' }}>
              <label style={{
                display: 'block',
                fontSize: '0.8125rem',
                fontWeight: 500,
                color: 'var(--color-text-secondary)',
                marginBottom: '0.5rem',
                letterSpacing: '-0.01em',
              }}>Password</label>
              <input
                id="login-password"
                type="password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                placeholder={isSignUp ? 'Min. 6 characters' : 'Enter your password'}
                required
                autoComplete={isSignUp ? 'new-password' : 'current-password'}
                style={{
                  width: '100%',
                  padding: '0.8125rem 1rem',
                  borderRadius: '0.75rem',
                  fontSize: '0.9375rem',
                  background: 'var(--color-surface-2)',
                  border: '1px solid var(--color-border)',
                  color: 'var(--color-text-primary)',
                  outline: 'none',
                  transition: 'all 0.15s ease',
                  fontFamily: 'inherit',
                }}
                onFocus={e => {
                  e.target.style.borderColor = 'oklch(0.56 0.22 275 / 0.6)'
                  e.target.style.boxShadow = '0 0 0 3px oklch(0.56 0.22 275 / 0.12)'
                  e.target.style.background = 'var(--color-surface-3)'
                }}
                onBlur={e => {
                  e.target.style.borderColor = 'var(--color-border)'
                  e.target.style.boxShadow = 'none'
                  e.target.style.background = 'var(--color-surface-2)'
                }}
              />
            </div>

            {/* Submit */}
            <button
              id="login-submit"
              type="submit"
              disabled={submitting}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '0.5rem',
                width: '100%',
                padding: '0.875rem 1.25rem',
                borderRadius: '0.875rem',
                fontSize: '0.9375rem',
                fontWeight: 600,
                color: '#fff',
                background: submitting
                  ? 'oklch(0.47 0.195 275)'
                  : 'linear-gradient(135deg, oklch(0.56 0.22 275), oklch(0.57 0.22 310))',
                border: 'none',
                cursor: submitting ? 'not-allowed' : 'pointer',
                transition: 'all 0.2s ease',
                boxShadow: submitting ? 'none' : '0 8px 24px oklch(0.56 0.22 275 / 0.35)',
                letterSpacing: '-0.01em',
                fontFamily: "'Plus Jakarta Sans', sans-serif",
              }}
              onMouseEnter={e => { if (!submitting) e.currentTarget.style.transform = 'translateY(-1px)' }}
              onMouseLeave={e => { e.currentTarget.style.transform = 'translateY(0)' }}
            >
              {submitting
                ? <Loader2 size={18} style={{ animation: 'spin 0.8s linear infinite' }} />
                : <Sparkles size={18} />}
              {isSignUp ? 'Create Account' : 'Sign In'}
              {!submitting && <ArrowRight size={16} style={{ marginLeft: '0.125rem' }} />}
            </button>
          </form>
        </div>

        {/* Footer toggle */}
        <p style={{
          textAlign: 'center',
          fontSize: '0.875rem',
          color: 'var(--color-text-muted)',
          marginTop: '1.5rem',
          animation: 'fade-in 0.5s ease-out 0.3s both',
        }}>
          {isSignUp ? 'Already have an account? ' : "Don't have an account? "}
          <button
            type="button"
            onClick={toggleMode}
            style={{
              color: 'oklch(0.72 0.16 275)',
              fontWeight: 600,
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              fontSize: 'inherit',
              fontFamily: 'inherit',
              transition: 'color 0.15s ease',
            }}
            onMouseEnter={e => e.currentTarget.style.color = 'oklch(0.82 0.12 275)'}
            onMouseLeave={e => e.currentTarget.style.color = 'oklch(0.72 0.16 275)'}
          >
            {isSignUp ? 'Sign in' : 'Sign up'}
          </button>
        </p>
      </div>
    </div>
  )
}

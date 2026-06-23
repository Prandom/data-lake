import { NavLink, Outlet } from 'react-router-dom'
import { MessageSquare, Plug, Database, LogOut, ChevronRight } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useAuth } from '@/hooks/useAuth'

const navItems = [
  { to: '/',           icon: MessageSquare, label: 'Chat',       desc: 'Ask your data lake' },
  { to: '/connectors', icon: Plug,          label: 'Connectors', desc: 'Manage data sources' },
]

export default function AppShell() {
  const { user, logout } = useAuth()

  const displayName = user?.displayName || user?.email?.split('@')[0] || 'User'
  const initials    = displayName.slice(0, 2).toUpperCase()
  const photoURL    = user?.photoURL

  return (
    <div style={{ display: 'flex', height: '100vh', overflow: 'hidden' }}>

      {/* ── Sidebar ── */}
      <aside style={{
        display: 'flex',
        flexDirection: 'column',
        width: '260px',
        flexShrink: 0,
        background: 'oklch(0.12 0.012 265)',
        borderRight: '1px solid var(--color-border)',
        position: 'relative',
      }}>
        {/* Sidebar glow */}
        <div style={{
          position: 'absolute', top: 0, left: 0, right: 0, height: '200px',
          background: 'radial-gradient(ellipse 120% 80% at 50% -10%, oklch(0.56 0.22 275 / 0.08), transparent)',
          pointerEvents: 'none',
        }} />

        {/* Logo */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '0.875rem',
          padding: '1.625rem 1.5rem 1.375rem',
          borderBottom: '1px solid var(--color-border)',
          position: 'relative',
        }}>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: '38px', height: '38px',
            borderRadius: '10px',
            background: 'linear-gradient(135deg, oklch(0.56 0.22 275 / 0.25), oklch(0.57 0.22 310 / 0.15))',
            border: '1px solid oklch(0.56 0.22 275 / 0.25)',
            flexShrink: 0,
          }}>
            <Database size={18} style={{ color: 'oklch(0.75 0.15 275)' }} />
          </div>
          <div>
            <h1 style={{
              fontFamily: "'Plus Jakarta Sans', sans-serif",
              fontSize: '0.9375rem',
              fontWeight: 700,
              letterSpacing: '-0.025em',
              color: 'var(--color-text-primary)',
              lineHeight: 1.2,
            }}>DataLake</h1>
            <p style={{
              fontSize: '0.6875rem',
              color: 'var(--color-text-muted)',
              fontWeight: 400,
              lineHeight: 1.3,
              marginTop: '1px',
            }}>Personal Knowledge Engine</p>
          </div>
        </div>

        {/* Navigation */}
        <nav style={{ flex: 1, padding: '1rem 0.875rem', position: 'relative' }}>
          <p style={{
            fontSize: '0.6875rem',
            fontWeight: 600,
            textTransform: 'uppercase',
            letterSpacing: '0.08em',
            color: 'var(--color-text-faint)',
            padding: '0 0.5rem',
            marginBottom: '0.5rem',
          }}>Menu</p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
            {navItems.map(({ to, icon: Icon, label, desc }) => (
              <NavLink
                key={to}
                to={to}
                end={to === '/'}
                style={({ isActive }) => ({
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.75rem',
                  padding: '0.6875rem 0.875rem',
                  borderRadius: '0.75rem',
                  textDecoration: 'none',
                  transition: 'all 0.15s ease',
                  background: isActive ? 'oklch(0.56 0.22 275 / 0.12)' : 'transparent',
                  border: isActive ? '1px solid oklch(0.56 0.22 275 / 0.2)' : '1px solid transparent',
                })}
                className={({ isActive }) => isActive ? 'nav-active' : 'nav-inactive'}
              >
                {({ isActive }) => (
                  <>
                    <div style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      width: '32px', height: '32px',
                      borderRadius: '8px',
                      background: isActive
                        ? 'oklch(0.56 0.22 275 / 0.2)'
                        : 'var(--color-surface-2)',
                      flexShrink: 0,
                      transition: 'all 0.15s ease',
                    }}>
                      <Icon size={16} style={{
                        color: isActive ? 'oklch(0.75 0.15 275)' : 'var(--color-text-muted)',
                        transition: 'color 0.15s ease',
                      }} />
                    </div>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <p style={{
                        fontSize: '0.875rem',
                        fontWeight: 500,
                        color: isActive ? 'var(--color-text-primary)' : 'var(--color-text-secondary)',
                        lineHeight: 1.2,
                        letterSpacing: '-0.01em',
                      }}>{label}</p>
                      <p style={{
                        fontSize: '0.6875rem',
                        color: isActive ? 'oklch(0.68 0.12 275)' : 'var(--color-text-faint)',
                        marginTop: '1px',
                        lineHeight: 1.2,
                      }}>{desc}</p>
                    </div>
                    {isActive && (
                      <ChevronRight size={14} style={{ color: 'oklch(0.65 0.16 275)', flexShrink: 0 }} />
                    )}
                  </>
                )}
              </NavLink>
            ))}
          </div>
        </nav>

        {/* User footer */}
        <div style={{
          padding: '0.875rem',
          borderTop: '1px solid var(--color-border)',
        }}>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.75rem',
            padding: '0.75rem 0.875rem',
            borderRadius: '0.875rem',
            background: 'var(--color-surface-2)',
            border: '1px solid var(--color-border)',
          }}>
            {photoURL ? (
              <img
                src={photoURL}
                alt={displayName}
                referrerPolicy="no-referrer"
                style={{
                  width: '34px', height: '34px',
                  borderRadius: '50%',
                  objectFit: 'cover',
                  flexShrink: 0,
                  border: '2px solid oklch(0.56 0.22 275 / 0.3)',
                }}
              />
            ) : (
              <div style={{
                width: '34px', height: '34px',
                borderRadius: '50%',
                background: 'linear-gradient(135deg, oklch(0.56 0.22 275 / 0.4), oklch(0.57 0.22 310 / 0.3))',
                border: '2px solid oklch(0.56 0.22 275 / 0.3)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0,
              }}>
                <span style={{
                  fontSize: '0.75rem',
                  fontWeight: 700,
                  color: 'oklch(0.80 0.12 275)',
                  fontFamily: "'Plus Jakarta Sans', sans-serif",
                }}>{initials}</span>
              </div>
            )}
            <div style={{ flex: 1, minWidth: 0 }}>
              <p style={{
                fontSize: '0.8125rem',
                fontWeight: 600,
                color: 'var(--color-text-primary)',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
                letterSpacing: '-0.01em',
                lineHeight: 1.3,
              }}>{displayName}</p>
              <p style={{
                fontSize: '0.6875rem',
                color: 'var(--color-text-muted)',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
                lineHeight: 1.3,
                marginTop: '1px',
              }}>{user?.email || 'Local Mode'}</p>
            </div>
            <button
              onClick={logout}
              title="Sign out"
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                width: '28px', height: '28px',
                borderRadius: '6px',
                background: 'transparent',
                border: 'none',
                cursor: 'pointer',
                color: 'var(--color-text-faint)',
                transition: 'all 0.15s ease',
                flexShrink: 0,
              }}
              onMouseEnter={e => {
                e.currentTarget.style.background = 'oklch(0.63 0.22 25 / 0.12)'
                e.currentTarget.style.color = 'oklch(0.72 0.20 25)'
              }}
              onMouseLeave={e => {
                e.currentTarget.style.background = 'transparent'
                e.currentTarget.style.color = 'var(--color-text-faint)'
              }}
            >
              <LogOut size={15} />
            </button>
          </div>
        </div>
      </aside>

      {/* ── Main content ── */}
      <main style={{ flex: 1, overflow: 'hidden' }}>
        <Outlet />
      </main>
    </div>
  )
}

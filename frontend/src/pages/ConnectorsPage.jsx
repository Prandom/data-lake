import { useState, useEffect } from 'react'
import {
  HardDrive, Upload, Cloud, BookOpen, Code2, Mail,
  CheckCircle2, XCircle, RefreshCw, ChevronRight, Plug,
  Zap, Lock,
} from 'lucide-react'
import { getStatus } from '@/lib/api'

const CONNECTOR_DEFS = [
  {
    id: 'filesystem',
    name: 'Local Files',
    description: 'Scan local directories and watch for changes automatically.',
    icon: HardDrive,
    gradient: 'linear-gradient(135deg, oklch(0.72 0.19 155 / 0.2), oklch(0.72 0.19 155 / 0.08))',
    border: 'oklch(0.72 0.19 155 / 0.25)',
    iconColor: 'oklch(0.72 0.19 155)',
    badge: { label: 'Local Only', color: 'oklch(0.72 0.19 155)', bg: 'oklch(0.72 0.19 155 / 0.12)' },
    available: true,
    localOnly: true,
  },
  {
    id: 'upload',
    name: 'File Upload',
    description: 'Drag & drop PDFs, text files, Markdown, and more.',
    icon: Upload,
    gradient: 'linear-gradient(135deg, oklch(0.56 0.22 275 / 0.2), oklch(0.56 0.22 275 / 0.08))',
    border: 'oklch(0.56 0.22 275 / 0.25)',
    iconColor: 'oklch(0.72 0.17 275)',
    badge: null,
    available: true,
  },
  {
    id: 'google_drive',
    name: 'Google Drive',
    description: 'Index your Drive files via OAuth 2.0 — no storage required.',
    icon: Cloud,
    gradient: 'linear-gradient(135deg, oklch(0.68 0.19 210 / 0.2), oklch(0.68 0.19 210 / 0.08))',
    border: 'oklch(0.68 0.19 210 / 0.25)',
    iconColor: 'oklch(0.68 0.19 210)',
    badge: { label: 'Week 7', color: 'oklch(0.68 0.19 210)', bg: 'oklch(0.68 0.19 210 / 0.12)' },
    available: false,
    comingSoon: true,
  },
  {
    id: 'notion',
    name: 'Notion',
    description: 'Sync pages, databases, and nested blocks from your workspace.',
    icon: BookOpen,
    gradient: 'linear-gradient(135deg, oklch(0.80 0.16 75 / 0.2), oklch(0.80 0.16 75 / 0.08))',
    border: 'oklch(0.80 0.16 75 / 0.25)',
    iconColor: 'oklch(0.80 0.16 75)',
    badge: { label: 'Week 10', color: 'oklch(0.80 0.16 75)', bg: 'oklch(0.80 0.16 75 / 0.12)' },
    available: false,
    comingSoon: true,
  },
  {
    id: 'github',
    name: 'GitHub',
    description: 'Index READMEs, issues, pull requests, and comments.',
    icon: Code2,
    gradient: 'linear-gradient(135deg, oklch(0.68 0.19 310 / 0.2), oklch(0.68 0.19 310 / 0.08))',
    border: 'oklch(0.68 0.19 310 / 0.25)',
    iconColor: 'oklch(0.72 0.17 310)',
    badge: { label: 'Week 10', color: 'oklch(0.72 0.17 310)', bg: 'oklch(0.68 0.19 310 / 0.12)' },
    available: false,
    comingSoon: true,
  },
  {
    id: 'email',
    name: 'Email',
    description: 'Connect Gmail or Outlook via IMAP. Indexes subjects and bodies.',
    icon: Mail,
    gradient: 'linear-gradient(135deg, oklch(0.63 0.22 25 / 0.2), oklch(0.63 0.22 25 / 0.08))',
    border: 'oklch(0.63 0.22 25 / 0.25)',
    iconColor: 'oklch(0.72 0.20 25)',
    badge: { label: 'Week 11', color: 'oklch(0.72 0.20 25)', bg: 'oklch(0.63 0.22 25 / 0.12)' },
    available: false,
    comingSoon: true,
  },
]

function ConnectorCard({ connector, status }) {
  const Icon = connector.icon
  const isConnected = status?.connected
  const [hovered, setHovered] = useState(false)

  return (
    <div
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        position: 'relative',
        padding: '1.5rem',
        borderRadius: '1.125rem',
        background: hovered && !connector.comingSoon
          ? 'var(--color-surface-2)'
          : 'var(--color-surface-1)',
        border: `1px solid ${isConnected ? connector.border : 'var(--color-border)'}`,
        transition: 'all 0.25s ease',
        transform: hovered && !connector.comingSoon ? 'translateY(-2px)' : 'none',
        boxShadow: hovered && !connector.comingSoon
          ? '0 12px 32px oklch(0 0 0 / 0.35)'
          : '0 2px 8px oklch(0 0 0 / 0.15)',
        opacity: connector.comingSoon ? 0.65 : 1,
        cursor: connector.comingSoon ? 'default' : 'pointer',
        overflow: 'hidden',
      }}
    >
      {/* Subtle gradient bg on hover */}
      {hovered && !connector.comingSoon && (
        <div style={{
          position: 'absolute', inset: 0,
          background: connector.gradient,
          opacity: 0.4,
          pointerEvents: 'none',
          borderRadius: 'inherit',
          transition: 'opacity 0.25s ease',
        }} />
      )}

      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '1.125rem', position: 'relative' }}>
        <div style={{
          width: '44px', height: '44px',
          borderRadius: '12px',
          background: connector.gradient,
          border: `1px solid ${connector.border}`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          flexShrink: 0,
        }}>
          <Icon size={20} style={{ color: connector.iconColor }} />
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          {connector.comingSoon ? (
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.375rem' }}>
              <Lock size={11} style={{ color: 'var(--color-text-faint)' }} />
              <span style={{
                padding: '0.25rem 0.625rem',
                borderRadius: '9999px',
                fontSize: '0.6875rem',
                fontWeight: 600,
                background: connector.badge?.bg,
                color: connector.badge?.color,
                border: `1px solid ${connector.border}`,
                letterSpacing: '0.02em',
              }}>{connector.badge?.label}</span>
            </div>
          ) : connector.localOnly ? (
            <span style={{
              padding: '0.25rem 0.625rem',
              borderRadius: '9999px',
              fontSize: '0.6875rem',
              fontWeight: 600,
              background: 'oklch(0.72 0.19 155 / 0.12)',
              color: 'oklch(0.72 0.19 155)',
              border: '1px solid oklch(0.72 0.19 155 / 0.25)',
            }}>Local Only</span>
          ) : isConnected ? (
            <CheckCircle2 size={18} style={{ color: 'var(--color-success)' }} />
          ) : (
            <XCircle size={18} style={{ color: 'var(--color-text-faint)' }} />
          )}
        </div>
      </div>

      {/* Body */}
      <div style={{ position: 'relative' }}>
        <h3 style={{
          fontFamily: "'Plus Jakarta Sans', sans-serif",
          fontSize: '0.9375rem',
          fontWeight: 700,
          color: 'var(--color-text-primary)',
          marginBottom: '0.4375rem',
          letterSpacing: '-0.02em',
        }}>{connector.name}</h3>
        <p style={{
          fontSize: '0.8125rem',
          color: 'var(--color-text-secondary)',
          lineHeight: 1.6,
          marginBottom: '1.125rem',
        }}>{connector.description}</p>

        {/* Action button */}
        {!connector.comingSoon && (
          <button style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            padding: '0.5625rem 1rem',
            borderRadius: '0.625rem',
            fontSize: '0.8125rem',
            fontWeight: 600,
            width: '100%',
            justifyContent: 'center',
            cursor: 'pointer',
            border: 'none',
            transition: 'all 0.15s ease',
            fontFamily: 'inherit',
            letterSpacing: '-0.01em',
            background: isConnected
              ? 'var(--color-surface-3)'
              : `linear-gradient(135deg, ${connector.iconColor}26, ${connector.iconColor}14)`,
            color: isConnected ? 'var(--color-text-secondary)' : connector.iconColor,
            boxShadow: isConnected ? 'none' : `0 2px 8px ${connector.iconColor}22`,
          }}>
            {isConnected
              ? <><RefreshCw size={13} /> Configure</>
              : <><ChevronRight size={13} /> Connect</>
            }
          </button>
        )}
      </div>
    </div>
  )
}

export default function ConnectorsPage() {
  const [sourceStatus, setSourceStatus] = useState({})
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function fetchStatus() {
      try {
        const data = await getStatus()
        setSourceStatus(data.sources || {})
      } catch (err) {
        console.error('Failed to load status:', err)
      } finally {
        setLoading(false)
      }
    }
    fetchStatus()
  }, [])

  const connectedCount = Object.values(sourceStatus).filter(s => s.connected).length
  const available = CONNECTOR_DEFS.filter(c => !c.comingSoon).length

  return (
    <div style={{ height: '100%', overflowY: 'auto', background: 'var(--color-surface-0)' }}>

      {/* Top gradient */}
      <div style={{
        position: 'sticky', top: 0, left: 0, right: 0, height: '1px',
        background: 'linear-gradient(90deg, transparent, oklch(0.56 0.22 275 / 0.4), transparent)',
      }} />

      <div style={{ maxWidth: '960px', margin: '0 auto', padding: '3rem 2.5rem' }}>

        {/* Header */}
        <div style={{ marginBottom: '2.5rem', animation: 'fade-in 0.4s ease-out forwards' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '1rem' }}>
            <div style={{
              width: '48px', height: '48px',
              borderRadius: '13px',
              background: 'linear-gradient(135deg, oklch(0.56 0.22 275 / 0.2), oklch(0.57 0.22 310 / 0.1))',
              border: '1px solid oklch(0.56 0.22 275 / 0.25)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}>
              <Plug size={22} style={{ color: 'oklch(0.72 0.17 275)' }} />
            </div>
            <div>
              <h1 style={{
                fontFamily: "'Plus Jakarta Sans', sans-serif",
                fontSize: '1.5rem',
                fontWeight: 800,
                color: 'var(--color-text-primary)',
                letterSpacing: '-0.03em',
                lineHeight: 1.2,
              }}>Data Sources</h1>
              <p style={{
                fontSize: '0.9rem',
                color: 'var(--color-text-secondary)',
                marginTop: '0.25rem',
              }}>Connect and manage your knowledge sources</p>
            </div>
          </div>

          {/* Stats bar */}
          <div style={{
            display: 'flex',
            gap: '1rem',
            flexWrap: 'wrap',
          }}>
            {[
              { label: 'Connected', value: connectedCount, color: 'oklch(0.72 0.19 155)' },
              { label: 'Available Now', value: available, color: 'oklch(0.72 0.17 275)' },
              { label: 'Coming Soon', value: CONNECTOR_DEFS.filter(c => c.comingSoon).length, color: 'var(--color-text-muted)' },
            ].map(stat => (
              <div key={stat.label} style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                padding: '0.5rem 0.875rem',
                borderRadius: '9999px',
                background: 'var(--color-surface-1)',
                border: '1px solid var(--color-border)',
                fontSize: '0.8125rem',
              }}>
                <Zap size={12} style={{ color: stat.color }} />
                <span style={{ fontWeight: 700, color: stat.color }}>{stat.value}</span>
                <span style={{ color: 'var(--color-text-muted)' }}>{stat.label}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Grid */}
        {loading ? (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '1.25rem' }}>
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} style={{
                height: '200px',
                borderRadius: '1.125rem',
                animation: 'shimmer 1.8s ease-in-out infinite',
                background: `linear-gradient(90deg, var(--color-surface-2) 25%, var(--color-surface-3) 50%, var(--color-surface-2) 75%)`,
                backgroundSize: '200% 100%',
              }} />
            ))}
          </div>
        ) : (
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
            gap: '1.25rem',
          }}>
            {CONNECTOR_DEFS.map((connector, i) => (
              <div key={connector.id} style={{
                animation: 'fade-in 0.4s ease-out both',
                animationDelay: `${i * 0.05}s`,
                opacity: 0,
              }}>
                <ConnectorCard connector={connector} status={sourceStatus[connector.id]} />
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

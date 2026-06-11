'use client'

interface Tab {
  id: string
  label: string
  icon: React.ReactNode
}

interface Props {
  activeTab: string
  onTabChange: (id: string) => void
}

const TabIcon = {
  overview: (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="3" width="7" height="7" /><rect x="14" y="3" width="7" height="7" />
      <rect x="3" y="14" width="7" height="7" /><rect x="14" y="14" width="7" height="7" />
    </svg>
  ),
  videos: (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <polygon points="23 7 16 12 23 17 23 7" /><rect x="1" y="5" width="15" height="14" rx="2" ry="2" />
    </svg>
  ),
  analytics: (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
    </svg>
  ),
  brands: (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z" />
      <line x1="7" y1="7" x2="7.01" y2="7" />
    </svg>
  ),
  body: (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="5" r="3" /><path d="M12 8v4m-4 0l-2 8m10-8l2 8m-10-8h8" />
    </svg>
  ),
}

const TABS: Tab[] = [
  { id: 'overview',  label: 'Overview',          icon: TabIcon.overview },
  { id: 'videos',    label: 'Match Videos',      icon: TabIcon.videos },
  { id: 'brands',    label: 'Brand Insights',    icon: TabIcon.brands },
  { id: 'analytics', label: 'Analytics Report',  icon: TabIcon.analytics },
  { id: 'body',      label: 'Body Segmentation', icon: TabIcon.body },
]

export default function MatchSelector({ activeTab, onTabChange }: Props) {
  return (
    <div style={{
      display: 'flex',
      gap: 2,
      background: 'var(--c-panel)',
      border: '1px solid var(--c-wire)',
      borderRadius: 10,
      padding: 4,
      marginBottom: 32,
    }}>
      {TABS.map(tab => {
        const isActive = tab.id === activeTab
        return (
          <button
            key={tab.id}
            onClick={() => onTabChange(tab.id)}
            style={{
              flex: 1,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 8,
              padding: '10px 16px',
              borderRadius: 8,
              border: 'none',
              background: isActive ? 'var(--c-spark)' : 'transparent',
              color: isActive ? '#000' : 'var(--c-dim)',
              fontSize: 12,
              fontWeight: isActive ? 700 : 500,
              letterSpacing: '0.02em',
              cursor: 'pointer',
              transition: 'all 0.2s ease',
              position: 'relative',
            }}
            onMouseEnter={e => {
              if (!isActive) {
                e.currentTarget.style.background = 'var(--c-hover)'
                e.currentTarget.style.color = 'var(--c-ink)'
              }
            }}
            onMouseLeave={e => {
              if (!isActive) {
                e.currentTarget.style.background = 'transparent'
                e.currentTarget.style.color = 'var(--c-dim)'
              }
            }}
          >
            <span style={{ display: 'flex', alignItems: 'center' }}>{tab.icon}</span>
            <span>{tab.label}</span>
          </button>
        )
      })}
    </div>
  )
}

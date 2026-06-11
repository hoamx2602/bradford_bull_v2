'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'

const LINKS = [
  { href: '/dashboard', label: 'Dashboard' },
  { href: '/', label: 'New Analysis' },
]

export default function Nav({ right }: { right?: React.ReactNode }) {
  const pathname = usePathname()

  return (
    <header className="no-print" style={{ borderBottom: '1px solid var(--c-wire)', background: 'var(--c-canvas)', position: 'sticky', top: 0, zIndex: 50 }}>
      <div style={{ maxWidth: 1280, margin: '0 auto', padding: '0 24px', height: 52, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 28 }}>
          <Link href="/dashboard" style={{ display: 'flex', alignItems: 'center', gap: 10, textDecoration: 'none', color: 'inherit' }}>
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
              <rect width="18" height="18" rx="4" fill="var(--c-spark)" />
              <path d="M4 9h4M10 6l4 3-4 3" stroke="#000" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            <span style={{ fontWeight: 700, fontSize: 12, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--c-ink)' }}>
              Sightline
            </span>
          </Link>

          <nav style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            {LINKS.map(l => {
              const active = pathname === l.href
              return (
                <Link
                  key={l.href}
                  href={l.href}
                  style={{
                    textDecoration: 'none',
                    fontSize: 12,
                    fontWeight: active ? 700 : 500,
                    color: active ? 'var(--c-ink)' : 'var(--c-dim)',
                    background: active ? 'var(--c-hover)' : 'transparent',
                    padding: '6px 12px',
                    borderRadius: 7,
                    transition: 'color 0.15s, background 0.15s',
                  }}
                >
                  {l.label}
                </Link>
              )
            })}
          </nav>
        </div>

        {right && <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>{right}</div>}
      </div>
    </header>
  )
}

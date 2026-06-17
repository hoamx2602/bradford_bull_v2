'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'

const LINKS = [
  { href: '/dashboard', label: 'Dashboard' },
  { href: '/', label: 'New Analysis' },
  { href: '/team-refs', label: 'Team Refs' },
]

export default function Nav({ right }: { right?: React.ReactNode }) {
  const pathname = usePathname()

  return (
    <header className="no-print" style={{ borderBottom: '1px solid var(--c-wire)', background: 'var(--c-canvas)', position: 'sticky', top: 0, zIndex: 50 }}>
      <div style={{ maxWidth: 1280, margin: '0 auto', padding: '0 24px', height: 52, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 28 }}>
          <Link href="/dashboard" style={{
            display: 'flex', alignItems: 'center', textDecoration: 'none', color: 'inherit',
            background: '#fff', borderRadius: 8, padding: '5px 10px',
          }}>
            {/* Logo artwork is dark text + red mark — needs a light backdrop to read on the dark nav. */}
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/logo/Group_34.svg" alt="LogoLens" style={{ height: 20, width: 'auto', display: 'block' }} />
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

import Link from 'next/link'

export default function Nav({ right }: { right?: React.ReactNode }) {
  return (
    <header style={{ borderBottom: '1px solid var(--c-wire)', background: 'var(--c-canvas)', position: 'sticky', top: 0, zIndex: 50 }}>
      <div style={{ maxWidth: 1280, margin: '0 auto', padding: '0 24px', height: 52, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <Link href="/" style={{ display: 'flex', alignItems: 'center', gap: 10, textDecoration: 'none', color: 'inherit' }}>
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
            <rect width="18" height="18" rx="4" fill="var(--c-spark)" />
            <path d="M4 9h4M10 6l4 3-4 3" stroke="#000" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          <span style={{ fontWeight: 700, fontSize: 12, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--c-ink)' }}>
            Sightline
          </span>
        </Link>
        {right && <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>{right}</div>}
      </div>
    </header>
  )
}

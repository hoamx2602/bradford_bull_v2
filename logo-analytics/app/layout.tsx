import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Sightline — Sponsor Visibility Analytics',
  description: 'Measure the real value of your sponsorships with AI-powered logo detection',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}

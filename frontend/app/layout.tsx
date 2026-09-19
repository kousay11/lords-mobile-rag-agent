import type { Metadata } from 'next'
import { Toaster } from 'sonner'
import './globals.css'

export const metadata: Metadata = {
  title: 'Kingdom Sage — Conseiller stratégique Lords Mobile',
  description: 'Conseiller documentaire Lords Mobile avec sources, versions et niveau de confiance.',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr" className="dark">
      <body className="min-h-screen bg-background text-text-main antialiased">
        {children}
        <Toaster position="bottom-right" theme="dark" richColors />
      </body>
    </html>
  )
}

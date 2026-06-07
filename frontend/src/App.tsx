import ChatInterface from './components/ChatInterface'
import AdminPanel from './components/AdminPanel'
import { useState } from 'react'

export default function App() {
  const [showAdmin, setShowAdmin] = useState(false)

  return (
    <div className="min-h-screen wedding-bg">
      {/* Header */}
      <header className="bg-brown text-cream-dark py-8 px-4 text-center shadow-lg">
        <div className="max-w-2xl mx-auto">
          <p className="font-serif text-gold text-sm tracking-[0.3em] uppercase mb-2">
            Together With Their Families
          </p>
          <h1 className="font-serif text-4xl md:text-5xl font-semibold italic mb-1">
            Sarah & James
          </h1>
          <div className="flex items-center justify-center gap-3 my-3">
            <div className="h-px bg-gold w-16 opacity-60" />
            <span className="text-gold text-lg">💍</span>
            <div className="h-px bg-gold w-16 opacity-60" />
          </div>
          <p className="font-sans text-sm tracking-widest text-cream-dark opacity-80">
            SEPTEMBER 20, 2025  •  THE ROSE GARDEN ESTATE
          </p>
        </div>
      </header>

      {/* Decorative band */}
      <div className="bg-gold h-1 opacity-70" />
      <div className="bg-rose h-0.5 opacity-50" />

      {/* Main content */}
      <main className="max-w-2xl mx-auto px-4 py-8">
        {!showAdmin ? (
          <>
            <div className="text-center mb-6">
              <p className="font-serif italic text-brown-light text-lg">
                We joyfully request the honour of your presence
              </p>
              <p className="font-sans text-sm text-brown-light opacity-70 mt-1">
                Chat with our wedding assistant to RSVP or ask any questions
              </p>
            </div>
            <ChatInterface />
          </>
        ) : (
          <AdminPanel />
        )}
      </main>

      {/* Footer */}
      <footer className="text-center py-6 mt-4">
        <div className="flex items-center justify-center gap-3 mb-3">
          <div className="h-px bg-gold w-12 opacity-40" />
          <span className="text-gold text-sm">🌸</span>
          <div className="h-px bg-gold w-12 opacity-40" />
        </div>
        <button
          onClick={() => setShowAdmin(!showAdmin)}
          className="text-xs text-brown-light opacity-40 hover:opacity-70 transition-opacity font-sans tracking-widest uppercase"
        >
          {showAdmin ? '← Back to Invitation' : 'Admin'}
        </button>
      </footer>

      {/* Toast container rendered by ChatInterface */}
    </div>
  )
}

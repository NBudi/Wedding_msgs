import { useState, useRef, useEffect } from 'react'
import { v4 as uuidv4 } from 'uuid'
import MessageBubble from './MessageBubble'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
}

const SESSION_KEY = 'wedding_session_id'

function getOrCreateSession(): string {
  let id = sessionStorage.getItem(SESSION_KEY)
  if (!id) {
    id = uuidv4()
    sessionStorage.setItem(SESSION_KEY, id)
  }
  return id
}

const WELCOME: Message = {
  id: '0',
  role: 'assistant',
  content:
    "Welcome! 💍🌸 I'm so happy you're here!\n\nI'm the wedding assistant for Sarah & James's special day. I can answer any questions about the celebration, and I'd love to help you RSVP.\n\nWhat can I help you with today?",
  timestamp: new Date(),
}

export default function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([WELCOME])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [toast, setToast] = useState<string | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const sessionId = useRef(getOrCreateSession())

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isLoading])

  useEffect(() => {
    if (toast) {
      const t = setTimeout(() => setToast(null), 4000)
      return () => clearTimeout(t)
    }
  }, [toast])

  const sendMessage = async () => {
    const text = input.trim()
    if (!text || isLoading) return

    const userMsg: Message = {
      id: uuidv4(),
      role: 'user',
      content: text,
      timestamp: new Date(),
    }

    setMessages(prev => [...prev, userMsg])
    setInput('')
    setIsLoading(true)

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, session_id: sessionId.current }),
      })

      if (!res.ok) throw new Error('Failed to get response')

      const data: { response: string; rsvp_saved: boolean } = await res.json()

      const botMsg: Message = {
        id: uuidv4(),
        role: 'assistant',
        content: data.response,
        timestamp: new Date(),
      }
      setMessages(prev => [...prev, botMsg])

      if (data.rsvp_saved) {
        setToast('🎊 RSVP saved! We can\'t wait to celebrate with you!')
      }
    } catch {
      setMessages(prev => [
        ...prev,
        {
          id: uuidv4(),
          role: 'assistant',
          content:
            "I'm so sorry, I'm having a little trouble connecting right now. Please try again in a moment, or reach out at hello@sarahandjames.com 💌",
          timestamp: new Date(),
        },
      ])
    } finally {
      setIsLoading(false)
      inputRef.current?.focus()
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  return (
    <div className="flex flex-col">
      {/* Chat window */}
      <div className="bg-white rounded-2xl shadow-lg border border-cream-dark overflow-hidden">
        {/* Messages */}
        <div className="h-[500px] overflow-y-auto p-4 space-y-4">
          {messages.map(msg => (
            <MessageBubble key={msg.id} message={msg} />
          ))}

          {isLoading && (
            <div className="flex items-end gap-2 animate-fade-in">
              <div className="w-8 h-8 rounded-full bg-gold flex items-center justify-center text-white text-xs flex-shrink-0">
                💍
              </div>
              <div className="bg-cream rounded-2xl rounded-bl-sm px-4 py-3 border border-cream-dark">
                <div className="flex items-center gap-0.5 h-5">
                  <span className="typing-dot" />
                  <span className="typing-dot" />
                  <span className="typing-dot" />
                </div>
              </div>
            </div>
          )}

          <div ref={bottomRef} />
        </div>

        {/* Input area */}
        <div className="border-t border-cream-dark bg-cream p-3 flex gap-2 items-end">
          <textarea
            ref={inputRef}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type a message..."
            rows={1}
            className="flex-1 resize-none bg-white border border-cream-dark rounded-xl px-4 py-2.5 text-sm text-brown font-sans placeholder-brown-light placeholder-opacity-50 focus:outline-none focus:ring-2 focus:ring-gold focus:ring-opacity-40 transition-all max-h-32"
            style={{ lineHeight: '1.5' }}
            disabled={isLoading}
          />
          <button
            onClick={sendMessage}
            disabled={!input.trim() || isLoading}
            className="flex-shrink-0 w-10 h-10 bg-gold hover:bg-gold-dark disabled:opacity-40 disabled:cursor-not-allowed rounded-xl flex items-center justify-center text-white transition-colors shadow-sm"
          >
            <svg className="w-4 h-4 rotate-90" fill="currentColor" viewBox="0 0 24 24">
              <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
            </svg>
          </button>
        </div>
      </div>

      {/* Quick reply suggestions */}
      <div className="flex flex-wrap gap-2 mt-3 justify-center">
        {[
          'I\'d like to RSVP',
          'What\'s the dress code?',
          'How do I get there?',
          'What time does it start?',
        ].map(suggestion => (
          <button
            key={suggestion}
            onClick={() => {
              setInput(suggestion)
              inputRef.current?.focus()
            }}
            className="text-xs bg-white border border-gold text-gold hover:bg-gold hover:text-white rounded-full px-3 py-1.5 transition-colors font-sans"
          >
            {suggestion}
          </button>
        ))}
      </div>

      {/* Toast notification */}
      {toast && (
        <div className="fixed bottom-8 left-1/2 -translate-x-1/2 bg-brown text-cream-dark px-6 py-3 rounded-full shadow-xl text-sm font-sans animate-slide-up z-50">
          {toast}
        </div>
      )}
    </div>
  )
}

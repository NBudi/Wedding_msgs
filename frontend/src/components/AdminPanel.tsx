import { useState, useEffect } from 'react'

interface RSVP {
  id: number
  guest_name: string
  email: string | null
  attending: number
  num_guests: number
  meal_preference: string | null
  dietary_restrictions: string | null
  message_to_couple: string | null
  created_at: string
}

export default function AdminPanel() {
  const [rsvps, setRsvps] = useState<RSVP[]>([])
  const [loading, setLoading] = useState(true)

  const fetchRsvps = async () => {
    setLoading(true)
    try {
      const res = await fetch('/api/rsvps')
      const data = await res.json()
      setRsvps(data)
    } catch {
      console.error('Failed to fetch RSVPs')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchRsvps()
  }, [])

  const attending = rsvps.filter(r => r.attending === 1)
  const notAttending = rsvps.filter(r => r.attending === 0)
  const totalGuests = attending.reduce((sum, r) => sum + (r.num_guests || 1), 0)

  return (
    <div className="animate-fade-in">
      <h2 className="font-serif text-2xl text-brown text-center mb-2">RSVP Dashboard</h2>
      <p className="text-center text-sm text-brown-light opacity-60 font-sans mb-6">
        Manage guest responses
      </p>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-3 mb-6">
        {[
          { label: 'Attending', value: attending.length, color: 'text-sage' },
          { label: 'Not Attending', value: notAttending.length, color: 'text-rose-dark' },
          { label: 'Total Guests', value: totalGuests, color: 'text-gold' },
        ].map(stat => (
          <div key={stat.label} className="bg-white rounded-xl border border-cream-dark p-4 text-center shadow-sm">
            <p className={`font-serif text-2xl font-semibold ${stat.color}`}>{stat.value}</p>
            <p className="text-xs text-brown-light opacity-60 font-sans mt-0.5">{stat.label}</p>
          </div>
        ))}
      </div>

      {/* Refresh button */}
      <div className="flex justify-end mb-3">
        <button
          onClick={fetchRsvps}
          className="text-xs text-gold border border-gold rounded-full px-4 py-1.5 hover:bg-gold hover:text-white transition-colors font-sans"
        >
          Refresh
        </button>
      </div>

      {loading ? (
        <div className="text-center py-12 text-brown-light opacity-50 font-sans text-sm">
          Loading...
        </div>
      ) : rsvps.length === 0 ? (
        <div className="text-center py-12 text-brown-light opacity-50 font-sans text-sm">
          No RSVPs yet
        </div>
      ) : (
        <div className="space-y-3">
          {rsvps.map(rsvp => (
            <div
              key={rsvp.id}
              className="bg-white rounded-xl border border-cream-dark p-4 shadow-sm"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <p className="font-serif text-brown font-medium">{rsvp.guest_name}</p>
                    <span
                      className={`text-xs px-2 py-0.5 rounded-full font-sans ${
                        rsvp.attending
                          ? 'bg-sage bg-opacity-20 text-sage'
                          : 'bg-rose bg-opacity-20 text-rose-dark'
                      }`}
                    >
                      {rsvp.attending ? `✓ Attending (${rsvp.num_guests || 1})` : '✗ Declining'}
                    </span>
                  </div>
                  {rsvp.email && (
                    <p className="text-xs text-brown-light opacity-60 font-sans">{rsvp.email}</p>
                  )}
                  {rsvp.meal_preference && (
                    <p className="text-xs text-brown-light font-sans mt-1">
                      🍽 {rsvp.meal_preference.charAt(0).toUpperCase() + rsvp.meal_preference.slice(1)}
                      {rsvp.dietary_restrictions && ` · ${rsvp.dietary_restrictions}`}
                    </p>
                  )}
                  {rsvp.message_to_couple && (
                    <p className="text-xs text-brown-light italic font-sans mt-1.5 border-l-2 border-gold pl-2">
                      "{rsvp.message_to_couple}"
                    </p>
                  )}
                </div>
                <p className="text-xs text-brown-light opacity-40 font-sans whitespace-nowrap">
                  {new Date(rsvp.created_at).toLocaleDateString()}
                </p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

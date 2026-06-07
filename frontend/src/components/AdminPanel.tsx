import { useState, useEffect, useRef } from 'react'

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

interface Guest {
  id: number
  name: string
  phone: string
  invitation_sent: number
  sent_at: string | null
  created_at: string
}

type Tab = 'rsvps' | 'guests'

export default function AdminPanel() {
  const [tab, setTab] = useState<Tab>('guests')
  const [rsvps, setRsvps] = useState<RSVP[]>([])
  const [guests, setGuests] = useState<Guest[]>([])
  const [loading, setLoading] = useState(false)
  const [sending, setSending] = useState(false)
  const [uploadStatus, setUploadStatus] = useState<string | null>(null)
  const [sendStatus, setSendStatus] = useState<string | null>(null)
  const fileRef = useRef<HTMLInputElement>(null)

  const fetchRsvps = async () => {
    setLoading(true)
    try {
      const res = await fetch('/api/rsvps')
      setRsvps(await res.json())
    } finally {
      setLoading(false)
    }
  }

  const fetchGuests = async () => {
    setLoading(true)
    try {
      const res = await fetch('/api/guests')
      setGuests(await res.json())
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (tab === 'rsvps') fetchRsvps()
    else fetchGuests()
  }, [tab])

  const handleCsvUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setUploadStatus('מעלה...')
    const form = new FormData()
    form.append('file', file)
    try {
      const res = await fetch('/api/guests/upload', { method: 'POST', body: form })
      const data = await res.json()
      setUploadStatus(`✓ יובאו ${data.imported} אורחים${data.errors.length ? ` (${data.errors.length} שגיאות)` : ''}`)
      fetchGuests()
    } catch {
      setUploadStatus('שגיאה בהעלאה')
    }
    if (fileRef.current) fileRef.current.value = ''
  }

  const handleSendInvitations = async () => {
    const unsent = guests.filter(g => !g.invitation_sent).length
    if (!unsent) return
    setSending(true)
    setSendStatus(null)
    try {
      const res = await fetch('/api/guests/send-invitations', { method: 'POST' })
      const data = await res.json()
      setSendStatus(`✓ נשלח ל-${data.sent} אורחים${data.failed ? ` · נכשל: ${data.failed}` : ''}`)
      fetchGuests()
    } catch {
      setSendStatus('שגיאה בשליחה')
    } finally {
      setSending(false)
    }
  }

  const deleteGuest = async (id: number) => {
    await fetch(`/api/guests/${id}`, { method: 'DELETE' })
    setGuests(prev => prev.filter(g => g.id !== id))
  }

  // ── RSVP stats ──
  const attending = rsvps.filter(r => r.attending === 1)
  const notAttending = rsvps.filter(r => r.attending === 0)
  const totalGuests = attending.reduce((s, r) => s + (r.num_guests || 1), 0)

  // ── Guest stats ──
  const sentCount = guests.filter(g => g.invitation_sent).length
  const unsentCount = guests.filter(g => !g.invitation_sent).length

  return (
    <div className="animate-fade-in">
      <h2 className="font-serif text-2xl text-brown text-center mb-1">לוח ניהול</h2>
      <p className="text-center text-xs text-brown-light opacity-50 font-sans mb-5 tracking-widest uppercase">Admin Dashboard</p>

      {/* Tabs */}
      <div className="flex bg-cream-dark rounded-xl p-1 mb-6">
        {([['guests', 'אורחים'], ['rsvps', 'אישורי הגעה']] as [Tab, string][]).map(([key, label]) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={`flex-1 py-2 rounded-lg text-sm font-sans transition-all ${
              tab === key
                ? 'bg-white text-brown shadow-sm font-medium'
                : 'text-brown-light opacity-60 hover:opacity-80'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* ── GUESTS TAB ── */}
      {tab === 'guests' && (
        <div>
          {/* Stats */}
          <div className="grid grid-cols-3 gap-3 mb-5">
            {[
              { label: 'סה"כ', value: guests.length, color: 'text-brown' },
              { label: 'נשלחו', value: sentCount, color: 'text-sage' },
              { label: 'ממתינים', value: unsentCount, color: 'text-gold' },
            ].map(s => (
              <div key={s.label} className="bg-white rounded-xl border border-cream-dark p-3 text-center shadow-sm">
                <p className={`font-serif text-2xl font-semibold ${s.color}`}>{s.value}</p>
                <p className="text-xs text-brown-light opacity-60 font-sans mt-0.5">{s.label}</p>
              </div>
            ))}
          </div>

          {/* CSV Upload */}
          <div className="bg-white rounded-xl border border-cream-dark p-4 mb-4 shadow-sm">
            <p className="text-sm font-sans text-brown font-medium mb-1">ייבוא רשימת אורחים מ-CSV</p>
            <p className="text-xs text-brown-light opacity-60 font-sans mb-3">
              עמודות נדרשות: <code className="bg-cream px-1 rounded">שם</code> ו-<code className="bg-cream px-1 rounded">טלפון</code> (או <code className="bg-cream px-1 rounded">name</code> ו-<code className="bg-cream px-1 rounded">phone</code>)
            </p>
            <input
              ref={fileRef}
              type="file"
              accept=".csv"
              onChange={handleCsvUpload}
              className="hidden"
              id="csv-upload"
            />
            <label
              htmlFor="csv-upload"
              className="inline-block cursor-pointer bg-cream border border-gold text-gold text-sm font-sans px-4 py-2 rounded-lg hover:bg-gold hover:text-white transition-colors"
            >
              בחר קובץ CSV
            </label>
            {uploadStatus && (
              <p className="text-xs text-brown-light font-sans mt-2">{uploadStatus}</p>
            )}
          </div>

          {/* Send invitations */}
          <div className="flex items-center gap-3 mb-4">
            <button
              onClick={handleSendInvitations}
              disabled={sending || unsentCount === 0}
              className="flex-1 bg-gold hover:bg-gold-dark disabled:opacity-40 disabled:cursor-not-allowed text-white font-sans text-sm py-2.5 rounded-xl transition-colors shadow-sm"
            >
              {sending ? 'שולח...' : `שלח הזמנות ל-${unsentCount} אורחים`}
            </button>
            <button
              onClick={fetchGuests}
              className="text-xs text-gold border border-gold rounded-xl px-3 py-2.5 hover:bg-gold hover:text-white transition-colors font-sans"
            >
              רענן
            </button>
          </div>
          {sendStatus && (
            <p className="text-xs text-brown-light font-sans text-center mb-3">{sendStatus}</p>
          )}

          {/* Guest list */}
          {loading ? (
            <p className="text-center py-8 text-brown-light opacity-40 text-sm font-sans">טוען...</p>
          ) : guests.length === 0 ? (
            <p className="text-center py-8 text-brown-light opacity-40 text-sm font-sans">אין אורחים עדיין — ייבא קובץ CSV</p>
          ) : (
            <div className="space-y-2">
              {guests.map(guest => (
                <div key={guest.id} className="bg-white rounded-xl border border-cream-dark px-4 py-3 shadow-sm flex items-center gap-3">
                  <div className="flex-1 min-w-0">
                    <p className="font-sans text-sm font-medium text-brown">{guest.name}</p>
                    <p className="text-xs text-brown-light opacity-50 font-sans" dir="ltr">+{guest.phone}</p>
                  </div>
                  <span className={`text-xs px-2 py-0.5 rounded-full font-sans whitespace-nowrap ${
                    guest.invitation_sent
                      ? 'bg-sage bg-opacity-20 text-sage'
                      : 'bg-cream-dark text-brown-light'
                  }`}>
                    {guest.invitation_sent ? '✓ נשלח' : 'ממתין'}
                  </span>
                  <button
                    onClick={() => deleteGuest(guest.id)}
                    className="text-brown-light opacity-30 hover:opacity-70 hover:text-rose-dark transition-opacity text-sm"
                  >
                    ✕
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── RSVPs TAB ── */}
      {tab === 'rsvps' && (
        <div>
          {/* Stats */}
          <div className="grid grid-cols-3 gap-3 mb-5">
            {[
              { label: 'מגיעים', value: attending.length, color: 'text-sage' },
              { label: 'לא מגיעים', value: notAttending.length, color: 'text-rose-dark' },
              { label: "סה\"כ אורחים", value: totalGuests, color: 'text-gold' },
            ].map(s => (
              <div key={s.label} className="bg-white rounded-xl border border-cream-dark p-3 text-center shadow-sm">
                <p className={`font-serif text-2xl font-semibold ${s.color}`}>{s.value}</p>
                <p className="text-xs text-brown-light opacity-60 font-sans mt-0.5">{s.label}</p>
              </div>
            ))}
          </div>

          <div className="flex justify-end gap-2 mb-3">
            <a
              href="/api/export/csv"
              download="rsvp_summary.csv"
              className="text-xs bg-sage text-white border border-sage rounded-full px-4 py-1.5 hover:opacity-80 transition-opacity font-sans"
            >
              ⬇ הורד CSV
            </a>
            <button onClick={fetchRsvps} className="text-xs text-gold border border-gold rounded-full px-4 py-1.5 hover:bg-gold hover:text-white transition-colors font-sans">
              רענן
            </button>
          </div>

          {loading ? (
            <p className="text-center py-8 text-brown-light opacity-40 text-sm font-sans">טוען...</p>
          ) : rsvps.length === 0 ? (
            <p className="text-center py-8 text-brown-light opacity-40 text-sm font-sans">אין אישורי הגעה עדיין</p>
          ) : (
            <div className="space-y-3">
              {rsvps.map(rsvp => (
                <div key={rsvp.id} className="bg-white rounded-xl border border-cream-dark p-4 shadow-sm">
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <p className="font-serif text-brown font-medium">{rsvp.guest_name}</p>
                        <span className={`text-xs px-2 py-0.5 rounded-full font-sans ${
                          rsvp.attending
                            ? 'bg-sage bg-opacity-20 text-sage'
                            : 'bg-rose bg-opacity-20 text-rose-dark'
                        }`}>
                          {rsvp.attending ? `✓ מגיע (${rsvp.num_guests || 1})` : '✗ לא מגיע'}
                        </span>
                      </div>
                      {rsvp.meal_preference && (
                        <p className="text-xs text-brown-light font-sans">
                          🍽 {{chicken:'עוף', fish:'דג', vegetarian:'צמחוני', vegan:'טבעוני'}[rsvp.meal_preference] ?? rsvp.meal_preference}
                          {rsvp.dietary_restrictions && ` · ${rsvp.dietary_restrictions}`}
                        </p>
                      )}
                      {rsvp.message_to_couple && (
                        <p className="text-xs text-brown-light italic font-sans mt-1.5 border-r-2 border-gold pr-2">
                          "{rsvp.message_to_couple}"
                        </p>
                      )}
                    </div>
                    <p className="text-xs text-brown-light opacity-40 font-sans whitespace-nowrap">
                      {new Date(rsvp.created_at).toLocaleDateString('he-IL')}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

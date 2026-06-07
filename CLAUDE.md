# Wedding App — CLAUDE.md

Hebrew AI chatbot for wedding RSVPs, with WhatsApp integration and an admin dashboard.

## Architecture

```
wedding_app/
├── backend/        # FastAPI + Python — runs on :8000
│   ├── main.py     # All backend logic (single file)
│   ├── .env        # Secrets — NEVER commit this
│   └── .env.example
├── frontend/       # React + Vite — runs on :5173
│   └── src/
│       ├── App.tsx
│       └── components/AdminPanel.tsx
└── ngrok.exe       # Tunnel for local webhook development
```

## Running the App

**Backend** (from `backend/`):
```powershell
cd backend
uvicorn main:app --reload
```

**Frontend** (from `frontend/`):
```powershell
cd frontend
npm run dev
```

Vite proxies `/api/*` → `http://localhost:8000`, so the frontend and backend both work on `:5173` in dev.

**ngrok** (for WhatsApp webhook — run from project root):
```powershell
.\ngrok.exe http 8000
```
Copy the `https://` URL into Meta Developer Console → WhatsApp → Configuration → Webhook URL (append `/webhook/whatsapp`).

## Required Environment Variables

Copy `.env.example` to `.env` and fill in:

```
ANTHROPIC_API_KEY=       # console.anthropic.com
WHATSAPP_ACCESS_TOKEN=   # Meta Developer Dashboard → WhatsApp → API Setup
WHATSAPP_PHONE_NUMBER_ID=
WHATSAPP_VERIFY_TOKEN=wedding_verify_token   # any secret string, must match Meta webhook settings
```

**Security:** `.env` is gitignored. Never commit real credentials. `.env.example` must contain only placeholder values.

## Key Technical Notes

### WhatsApp 24-Hour Window
Meta blocks free-form text/interactive messages for cold outreach. First contact MUST use an approved template (`wedding_invitation`). After a guest replies, free-form text works for 24 hours.

### Webhook Verification Bug
Starlette's `request.query_params` fails to parse parameter names containing dots (e.g. `hub.verify_token`). Fixed by using `urllib.parse.parse_qs(str(request.url.query))` with fallback for both dot and underscore variants.

### WhatsApp Phone Number
`WHATSAPP_PHONE_NUMBER_ID=1107180839150320` is Meta's test number (+1 555-676-7951). For production, you need a real business number.

### Template: `wedding_invitation`
Registered in Meta Business Manager (Hebrew). Status: under review when session ended. Body: `שלום {{1}}, חילה ונועם שמחים להזמינך לחתונתם! לפרטים ואישור הגעה שלח/י הודעה כאן 💍`

## Database

SQLite at `backend/wedding_data.db` (gitignored). Two tables:

- **`guests`** — imported from CSV (name, phone normalized to international format, invitation_sent flag)
- **`rsvps`** — collected by the Hebrew AI chatbot (guest_name, attending, num_guests, meal_preference, dietary_restrictions, message_to_couple)

Phone normalization: Israeli `05X-XXXXXXX` → `9725XXXXXXXX` (strip non-digits, replace leading `0` with `972`).

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/chat` | Web chat (session_id + message) |
| GET | `/api/rsvps` | List all RSVPs |
| DELETE | `/api/rsvps/:id` | Delete RSVP |
| GET | `/api/export/csv` | Download RSVP summary as UTF-8 BOM CSV |
| GET | `/api/guests` | List all guests |
| POST | `/api/guests/upload` | Upload guest CSV (columns: שם/name, טלפון/phone) |
| DELETE | `/api/guests/:id` | Delete guest |
| POST | `/api/guests/send-invitations` | Send WhatsApp template to all unsent guests |
| GET | `/webhook/whatsapp` | Meta webhook verification |
| POST | `/webhook/whatsapp` | Incoming WhatsApp messages → Hebrew AI response |

## AI Chatbot

Uses `claude-haiku-4-5` via Anthropic SDK. Runs in Hebrew only. Has a `save_rsvp` tool that triggers when all RSVP details are collected. Conversation history is stored in memory (per session_id, max 40 messages).

The WhatsApp webhook uses the sender's phone number as session_id, so each guest maintains their own conversation state.

## CSV Export

`rsvp_summary.csv` (UTF-8 BOM for Excel compatibility) auto-updates on every RSVP save. Also available on-demand via `GET /api/export/csv` or the "הורד CSV" button in the admin dashboard.

## Wedding Details

Couple: חילה ונועם | Date: 20 בנובמבר 2026 | Venue: The Rose Garden Estate, Beverly Hills

# Wedding App — Instructions

## Before You Start (One-Time)

### 1. Check the template is approved
1. Go to [business.facebook.com](https://business.facebook.com)
2. Left menu → **WhatsApp Manager** → **Message Templates**
3. Find `wedding_invitation` — status must be **Approved** (green)
4. If still "In Review" — wait. Usually 5–30 minutes, sometimes a few hours.
5. If **Rejected** — see [Changing the invitation text](#changing-the-invitation-text) below

---

## Every Time You Want to Use the App

You need **3 terminals open** at once. Run each in a separate PowerShell window.

### Terminal 1 — Backend
```
cd "e:\python projects\wedding_app\backend"
uvicorn main:app --reload
```
Leave it running. You should see: `Uvicorn running on http://127.0.0.1:8000`

### Terminal 2 — Frontend
```
cd "e:\python projects\wedding_app\frontend"
npm run dev
```
Leave it running. You should see: `Local: http://localhost:5173/`

### Terminal 3 — ngrok (needed for WhatsApp replies to work)
```
cd "e:\python projects\wedding_app"
.\ngrok.exe http 8000
```
Leave it running. You'll see a line like:
```
https://xxxx-xxxx.ngrok-free.app -> http://localhost:8000
```
**Copy that `https://` URL** — you'll need it for the Meta webhook.

> **Important:** ngrok gives a new URL every time you restart it. When the URL changes, you must update it in Meta (step below).

### Update the webhook URL in Meta (after ngrok restarts)
1. Go to [developers.facebook.com](https://developers.facebook.com) → your app
2. Left menu → **WhatsApp** → **Configuration**
3. Under **Webhook**, click **Edit**
4. Paste your new ngrok URL + `/webhook/whatsapp`
   - Example: `https://xxxx.ngrok-free.app/webhook/whatsapp`
5. Verify Token: `wedding_verify_token`
6. Click **Verify and Save**

### Open the app
Go to [http://localhost:5173](http://localhost:5173) in your browser.
- To access the Admin Dashboard — click **ניהול** (management) and enter the password.

---

## Sending Invitations to Guests

### Step 1 — Prepare your CSV file
Create a CSV file with two columns:

```
שם,טלפון
דנה כהן,0521234567
יוסי לוי,0537654321
```

- Column headers can be Hebrew (`שם`, `טלפון`) or English (`name`, `phone`)
- Phone numbers: Israeli format (05X...) is fine — the app converts automatically
- Save with UTF-8 encoding (if using Excel: **Save As** → choose **CSV UTF-8**)

### Step 2 — Import the CSV
1. Open the Admin Dashboard → **אורחים** tab
2. Click **בחר קובץ CSV**
3. Select your file
4. You should see: `✓ יובאו X אורחים`

### Step 3 — Send invitations
1. Click the **שלח הזמנות** button
2. Wait — it sends one by one (a few seconds per guest)
3. You'll see: `✓ נשלח ל-X אורחים`
4. Each guest row will change from "ממתין" to "✓ נשלח"

> Guests who were already sent an invitation are skipped automatically.

### What the guest receives
The approved `wedding_invitation` template message in Hebrew.
After they reply — the Hebrew AI chatbot takes over and collects the RSVP.

---

## Viewing RSVPs

1. Admin Dashboard → **אישורי הגעה** tab
2. Stats at the top: מגיעים / לא מגיעים / סה"כ אורחים
3. Click **הורד CSV** to download a spreadsheet with all RSVP details

The CSV updates automatically every time someone RSVPs.

---

## Changing Text

### Wedding details (date, venue, time, names)
File: `backend/main.py` — around **line 69**

```python
WEDDING = {
    "couple_he": "חילה ונועם",
    "date_he": "20 בנובמבר 2026",
    "time_he": "18:00",
    "venue": "The Rose Garden Estate",
    "address": "123 Garden Lane, Beverly Hills, CA 90210",
    "dress_code_he": "לבוש חגיגי",
    "rsvp_deadline_he": "1 באוגוסט 2025",
    "contact_email": "HilaandNoam@wedding.com",
}
```

Change whatever you need, save the file. The backend reloads automatically (--reload mode).

### The chatbot's personality / instructions
File: `backend/main.py` — around **line 80** (`SYSTEM_PROMPT`)

This is what tells the AI how to behave. You can adjust the tone, what questions to ask, etc.

### The invitation template text
The template text lives in **Meta Business Manager**, not in the code.
1. Go to [business.facebook.com](https://business.facebook.com) → **WhatsApp Manager** → **Message Templates**
2. Find `wedding_invitation` → click **Edit**
3. Change the text, save, and **resubmit for approval**
4. Wait for approval before sending (status must be green / Approved)

---

## Troubleshooting

### Guests aren't receiving messages
- Check the template is **Approved** in Meta Business Manager
- Check Terminal 1 (backend) for errors — look for lines starting with `ERROR`
- Make sure you're using the correct WhatsApp access token in `backend/.env`
  - Tokens expire. Go to [developers.facebook.com](https://developers.facebook.com) → your app → WhatsApp → API Setup → copy fresh token → paste into `.env`

### Guests reply but the chatbot doesn't respond
- ngrok must be running (Terminal 3)
- The webhook URL in Meta must match your current ngrok URL
- Check Terminal 1 for incoming webhook logs — you should see `POST /webhook/whatsapp`

### "Failed to send" for some guests
- The number may not have WhatsApp
- The number format may be wrong — check the CSV for typos

### Backend won't start
- Make sure you're in the `backend/` folder
- Make sure `.env` exists with all three WhatsApp values filled in
- Run: `pip install -r requirements.txt` if packages are missing

### App won't open in browser
- Make sure both Terminal 1 and Terminal 2 are running
- Go to exactly: `http://localhost:5173`

---

## Files to Know

| File | What it is |
|------|-----------|
| `backend/.env` | Your secret keys — never share or commit this |
| `backend/main.py` | All backend logic, wedding details, AI instructions |
| `backend/wedding_data.db` | The database (guests + RSVPs) — auto-created |
| `rsvp_summary.csv` | Auto-updated RSVP export |
| `frontend/src/components/AdminPanel.tsx` | Admin dashboard UI |

---

## Security Reminders

- Never share the `backend/.env` file
- Never commit `.env` to git (it's already in `.gitignore` — don't change that)
- The WhatsApp access token expires periodically — regenerate it at [developers.facebook.com](https://developers.facebook.com) when messages stop sending
- Regenerate your Anthropic API key at [console.anthropic.com](https://console.anthropic.com) if you think it was exposed

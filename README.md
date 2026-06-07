# Wedding Chatbot Invitation

An AI-powered wedding invitation chatbot for guests to get information and RSVP through a chat interface.

**Stack:** React + Vite + Tailwind CSS (frontend) · Python FastAPI (backend) · Claude AI (claude-haiku-4-5) · SQLite (RSVPs)

## Features

- Beautiful wedding-themed chat UI
- AI chatbot that answers guest questions about the wedding
- Guided RSVP collection via natural conversation
- SQLite storage for all RSVPs
- Admin dashboard to view all responses

## Setup

### Prerequisites

- Python 3.9+
- Node.js 18+
- Anthropic API key

### Backend

```bash
cd backend
pip install -r requirements.txt
set ANTHROPIC_API_KEY=your_api_key_here   # Windows
# export ANTHROPIC_API_KEY=your_api_key_here  # Mac/Linux
uvicorn main:app --reload
```

Backend runs at `http://localhost:8000`

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at `http://localhost:5173`

## Customize

Edit the `WEDDING` dict in `backend/main.py` to change:
- Couple names
- Date, time, and venue
- Dress code
- RSVP deadline
- Contact email

## Admin Panel

Click the tiny "Admin" link in the footer to see all RSVPs with stats.

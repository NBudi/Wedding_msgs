import os
import sqlite3

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel
import anthropic

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = anthropic.Anthropic()

conversations: dict[str, list] = {}

DB_PATH = "wedding_data.db"

# WhatsApp Cloud API credentials (set in .env)
WHATSAPP_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "wedding_verify_token")


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS rsvps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guest_name TEXT NOT NULL,
            email TEXT,
            attending INTEGER NOT NULL,
            num_guests INTEGER DEFAULT 1,
            meal_preference TEXT,
            dietary_restrictions TEXT,
            message_to_couple TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


init_db()

WEDDING = {
    "couple": "Hila & Noam",
    "date": "November 20, 2026",
    "time": "6:00 PM",
    "venue": "The Rose Garden Estate",
    "address": "123 Garden Lane, Beverly Hills, CA 90210",
    "reception_time": "6:00 PM",
    "dress_code": "Black Tie Optional",
    "rsvp_deadline": "August 1, 2025",
    "contact_email": "HilaandNoam@wedding.com",
}

SYSTEM_PROMPT = f"""You are the wedding invitation chatbot for {WEDDING["couple"]}'s wedding. Be warm, joyful, and celebratory.

Wedding Details:
- Couple: {WEDDING["couple"]}
- Date: {WEDDING["date"]} at {WEDDING["time"]}
- Venue: {WEDDING["venue"]}, {WEDDING["address"]}
- Reception: {WEDDING["reception_time"]}
- Dress Code: {WEDDING["dress_code"]}
- RSVP Deadline: {WEDDING["rsvp_deadline"]}

Your job:
1. Welcome guests warmly and answer questions about the wedding
2. Collect RSVPs - ask for: guest name, whether attending, number in their party, meal choice (chicken/fish/vegetarian/vegan), any dietary restrictions, and an optional message for the couple
3. Once you have all RSVP details from an attending guest, call save_rsvp to record them
4. If guests cannot attend, still call save_rsvp with attending=false
5. For questions you cannot answer, direct them to {WEDDING["contact_email"]}

Keep responses warm but concise. Use occasional celebratory emojis"""

TOOLS = [
    {
        "name": "save_rsvp",
        "description": "Save a guest RSVP once all details are collected",
        "input_schema": {
            "type": "object",
            "properties": {
                "guest_name": {"type": "string", "description": "Full name of the guest"},
                "email": {"type": "string", "description": "Email address (optional)"},
                "attending": {"type": "boolean", "description": "Whether the guest is attending"},
                "num_guests": {"type": "integer", "description": "Total people attending including this guest"},
                "meal_preference": {
                    "type": "string",
                    "enum": ["chicken", "fish", "vegetarian", "vegan"],
                    "description": "Meal choice",
                },
                "dietary_restrictions": {"type": "string", "description": "Allergies or dietary needs"},
                "message_to_couple": {"type": "string", "description": "A message or wish for the couple"},
            },
            "required": ["guest_name", "attending"],
        },
    }
]


# -- Helpers ------------------------------------------------------------------

def serialize_content(content):
    if isinstance(content, str):
        return content
    result = []
    for block in content:
        if block.type == "text":
            result.append({"type": "text", "text": block.text})
        elif block.type == "tool_use":
            result.append({
                "type": "tool_use",
                "id": block.id,
                "name": block.name,
                "input": dict(block.input),
            })
    return result


def save_rsvp_to_db(data: dict):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        INSERT INTO rsvps (guest_name, email, attending, num_guests, meal_preference, dietary_restrictions, message_to_couple)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            data.get("guest_name"),
            data.get("email"),
            1 if data.get("attending") else 0,
            data.get("num_guests", 1),
            data.get("meal_preference"),
            data.get("dietary_restrictions"),
            data.get("message_to_couple"),
        ),
    )
    conn.commit()
    conn.close()


async def process_message(message: str, session_id: str) -> tuple[str, bool]:
    """Core chat logic shared by the web API and the WhatsApp webhook."""
    if session_id not in conversations:
        conversations[session_id] = []

    conversations[session_id].append({"role": "user", "content": message})

    if len(conversations[session_id]) > 40:
        conversations[session_id] = conversations[session_id][-40:]

    rsvp_saved = False
    response = None

    for _ in range(5):
        response = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=conversations[session_id],
        )

        if response.stop_reason != "tool_use":
            conversations[session_id].append({
                "role": "assistant",
                "content": serialize_content(response.content),
            })
            break

        conversations[session_id].append({
            "role": "assistant",
            "content": serialize_content(response.content),
        })

        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                if block.name == "save_rsvp":
                    save_rsvp_to_db(block.input)
                    rsvp_saved = True
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": "RSVP saved successfully!",
                })

        conversations[session_id].append({"role": "user", "content": tool_results})

    assistant_message = ""
    if response:
        for block in response.content:
            if hasattr(block, "text"):
                assistant_message = block.text
                break

    return assistant_message, rsvp_saved


# -- Web API ------------------------------------------------------------------

class ChatRequest(BaseModel):
    message: str
    session_id: str


class ChatResponse(BaseModel):
    response: str
    rsvp_saved: bool = False


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    response_text, rsvp_saved = await process_message(request.message, request.session_id)
    return ChatResponse(response=response_text, rsvp_saved=rsvp_saved)


@app.get("/api/rsvps")
async def get_rsvps():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM rsvps ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(row) for row in rows]


@app.delete("/api/rsvps/{rsvp_id}")
async def delete_rsvp(rsvp_id: int):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM rsvps WHERE id = ?", (rsvp_id,))
    conn.commit()
    conn.close()
    return {"deleted": rsvp_id}


# -- WhatsApp webhook (Meta Cloud API - FREE) ---------------------------------

@app.get("/webhook/whatsapp")
async def verify_whatsapp_webhook(request: Request):
    """
    Meta calls this GET once when you register the webhook URL.
    It sends hub.challenge and expects it echoed back.
    """
    params = request.query_params
    if (
        params.get("hub.mode") == "subscribe"
        and params.get("hub.verify.token") == WHATSAPP_VERIFY_TOKEN
    ):
        return Response(content=params.get("hub.challenge", ""), media_type="text/plain")
    return Response(status_code=403)


@app.post("/webhook/whatsapp")
async def whatsapp_webhook(request: Request):
    """
    Meta calls this POST every time a guest sends a WhatsApp message.
    We parse the message, run it through Claude, and reply via the Cloud API.
    """
    body = await request.json()

    try:
        change_value = body["entry"][0]["changes"][0]["value"]

        # Ignore delivery receipts and status updates
        if "messages" not in change_value:
            return {"status": "ignored"}

        message = change_value["messages"][0]

        # Only handle text messages
        if message.get("type") != "text":
            return {"status": "non-text ignored"}

        from_number = message["from"]          # e.g. "972501234567"
        text = message["text"]["body"]
        phone_number_id = change_value["metadata"]["phone_number_id"]

    except (KeyError, IndexError):
        return {"status": "invalid payload"}

    response_text, _ = await process_message(text, session_id=from_number)

    # Send reply via Meta WhatsApp Cloud API
    async with httpx.AsyncClient() as http:
        await http.post(
            f"https://graph.facebook.com/v21.0/{phone_number_id}/messages",
            headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}"},
            json={
                "messaging_product": "whatsapp",
                "to": from_number,
                "type": "text",
                "text": {"body": response_text},
            },
            timeout=10,
        )

    return {"status": "ok"}

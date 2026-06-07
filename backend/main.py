from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import anthropic
import sqlite3
import os

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
    "couple": "Sarah & James",
    "date": "September 20, 2025",
    "time": "4:00 PM",
    "venue": "The Rose Garden Estate",
    "address": "123 Garden Lane, Beverly Hills, CA 90210",
    "reception_time": "6:00 PM",
    "dress_code": "Black Tie Optional",
    "rsvp_deadline": "August 1, 2025",
    "contact_email": "hello@sarahandjames.com",
}

SYSTEM_PROMPT = f"""You are the wedding invitation chatbot for {WEDDING['couple']}'s wedding. Be warm, joyful, and celebratory.

Wedding Details:
- Couple: {WEDDING['couple']}
- Date: {WEDDING['date']} at {WEDDING['time']}
- Venue: {WEDDING['venue']}, {WEDDING['address']}
- Reception: {WEDDING['reception_time']}
- Dress Code: {WEDDING['dress_code']}
- RSVP Deadline: {WEDDING['rsvp_deadline']}

Your job:
1. Welcome guests warmly and answer questions about the wedding
2. Collect RSVPs — ask for: guest name, whether attending, number in their party, meal choice (chicken/fish/vegetarian/vegan), any dietary restrictions, and an optional message for the couple
3. Once you have all RSVP details from an attending guest, call save_rsvp to record them
4. If guests can't attend, still call save_rsvp with attending=false
5. For questions you can't answer, direct them to {WEDDING['contact_email']}

Keep responses warm but concise. Use occasional celebratory emojis 💍🌸🎊"""

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
                    "description": "Meal choice"
                },
                "dietary_restrictions": {"type": "string", "description": "Allergies or dietary needs"},
                "message_to_couple": {"type": "string", "description": "A message or wish for the couple"},
            },
            "required": ["guest_name", "attending"],
        },
    }
]


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


class ChatRequest(BaseModel):
    message: str
    session_id: str


class ChatResponse(BaseModel):
    response: str
    rsvp_saved: bool = False


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    session_id = request.session_id

    if session_id not in conversations:
        conversations[session_id] = []

    conversations[session_id].append({"role": "user", "content": request.message})

    # Keep history bounded to last 40 messages
    if len(conversations[session_id]) > 40:
        conversations[session_id] = conversations[session_id][-40:]

    rsvp_saved = False
    response = None

    for _ in range(5):  # max 5 tool-use loops
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

        # Handle tool calls
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

    return ChatResponse(response=assistant_message, rsvp_saved=rsvp_saved)


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

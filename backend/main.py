import csv
import io
import os
import re
import sqlite3

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, File, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
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

WHATSAPP_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
WHATSAPP_PHONE_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
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
    conn.execute("""
        CREATE TABLE IF NOT EXISTS guests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT NOT NULL UNIQUE,
            invitation_sent INTEGER DEFAULT 0,
            sent_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


init_db()

WEDDING = {
    "couple_he": "הילה ונועם",
    "date_he": "20 בנובמבר 2026",
    "time_he": "18:00",
    "venue": "The Rose Garden Estate",
    "address": "123 Garden Lane, Beverly Hills, CA 90210",
    "dress_code_he": "לבוש חגיגי",
    "rsvp_deadline_he": "1 באוגוסט 2025",
    "contact_email": "HilaandNoam@wedding.com",
}

SYSTEM_PROMPT = f"""אתה עוזר ההזמנות לחתונה של {WEDDING['couple_he']}. דבר בעברית בלבד. היה חמים, שמחים ומסביר פנים.

פרטי החתונה:
- בני הזוג: {WEDDING['couple_he']}
- תאריך: {WEDDING['date_he']} בשעה {WEDDING['time_he']}
- מקום: {WEDDING['venue']}, {WEDDING['address']}
- קוד לבוש: {WEDDING['dress_code_he']}
- מועד אחרון לאישור הגעה: {WEDDING['rsvp_deadline_he']}

תפקידך:
1. קבל אורחים בחמימות וענה על שאלות על החתונה
2. אסוף אישורי הגעה - שאל: שם האורח, האם יגיע, כמה אנשים, העדפת ארוחה (עוף/דג/צמחוני/טבעוני), הגבלות תזונה, ומסר לבני הזוג
3. כשיש לך את כל הפרטים מאורח שמגיע, קרא ל-save_rsvp לשמירה
4. אם אורח לא יכול להגיע, עדיין קרא ל-save_rsvp עם attending=false
5. לשאלות שאינך יכול לענות עליהן, הפנה ל-{WEDDING['contact_email']}

שמור על תגובות חמות אך קצרות. השתמש לפעמים באימוג\'ים חגיגיים 💍🌸🎊"""

TOOLS = [
    {
        "name": "save_rsvp",
        "description": "שמור אישור הגעה של אורח לאחר שנאספו כל הפרטים",
        "input_schema": {
            "type": "object",
            "properties": {
                "guest_name": {"type": "string", "description": "שם מלא של האורח"},
                "email": {"type": "string", "description": "כתובת אימייל (אופציונלי)"},
                "attending": {"type": "boolean", "description": "האם האורח מגיע"},
                "num_guests": {"type": "integer", "description": "סך הכל אנשים כולל האורח"},
                "meal_preference": {
                    "type": "string",
                    "enum": ["chicken", "fish", "vegetarian", "vegan"],
                    "description": "העדפת ארוחה",
                },
                "dietary_restrictions": {"type": "string", "description": "הגבלות תזונה או אלרגיות"},
                "message_to_couple": {"type": "string", "description": "מסר לבני הזוג"},
            },
            "required": ["guest_name", "attending"],
        },
    }
]


# -- Helpers ------------------------------------------------------------------

def normalize_phone(phone: str) -> str:
    """Convert phone to international format digits only (no + prefix)."""
    digits = re.sub(r"[^\d]", "", phone)
    # Israeli mobile starting with 0: 05X-XXXXXXX -> 9725XXXXXXXXX
    if len(digits) == 10 and digits.startswith("0"):
        digits = "972" + digits[1:]
    return digits


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


SUMMARY_CSV = "rsvp_summary.csv"

def export_summary_csv():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    # Join guests (phone) with rsvps (attendance info) by name
    rows = conn.execute("""
        SELECT
            r.guest_name        AS שם,
            g.phone             AS טלפון,
            CASE r.attending WHEN 1 THEN 'כן' ELSE 'לא' END AS מגיע,
            r.num_guests        AS מספר_אורחים,
            CASE r.meal_preference
                WHEN 'chicken'    THEN 'עוף'
                WHEN 'fish'       THEN 'דג'
                WHEN 'vegetarian' THEN 'צמחוני'
                WHEN 'vegan'      THEN 'טבעוני'
                ELSE COALESCE(r.meal_preference, '')
            END                 AS העדפת_ארוחה,
            COALESCE(r.message_to_couple, '') AS הודעה,
            r.created_at        AS תאריך
        FROM rsvps r
        LEFT JOIN guests g ON g.name = r.guest_name
        ORDER BY r.created_at DESC
    """).fetchall()
    conn.close()

    with open(SUMMARY_CSV, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["שם", "טלפון", "מגיע", "מספר_אורחים", "העדפת_ארוחה", "הודעה", "תאריך"])
        writer.writeheader()
        writer.writerows([dict(r) for r in rows])


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
    export_summary_csv()


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


async def _wa_post(payload: dict) -> bool:
    async with httpx.AsyncClient() as http:
        resp = await http.post(
            f"https://graph.facebook.com/v21.0/{WHATSAPP_PHONE_ID}/messages",
            headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}"},
            json=payload,
            timeout=10,
        )
        return resp.status_code == 200


async def send_whatsapp_text(phone: str, text: str) -> bool:
    return await _wa_post({
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "text",
        "text": {"body": text},
    })


async def send_invitation_buttons(phone: str, guest_name: str) -> bool:
    """
    Send the invitation as an interactive message with quick-reply buttons.
    NOTE: For first contact (business-initiated), Meta requires an approved template.
    This works immediately for guests who have already messaged the business,
    or when using Meta's test phone numbers.
    To send to any number for the first time, register a 'wedding_invitation'
    template in Meta Business Manager and switch to send_whatsapp_template() below.
    """
    return await _wa_post({
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {
                "text": (
                    f"שלום {guest_name}! 💍\n\n"
                    f"הילה ונועם שמחים להזמין אתכם לחתונתם!\n\n"
                    f"📅 {WEDDING['date_he']} | 🕕 {WEDDING['time_he']}\n"
                    f"📍 {WEDDING['venue']}\n\n"
                    "האם תוכלו להגיע?"
                )
            },
            "action": {
                "buttons": [
                    {"type": "reply", "reply": {"id": "rsvp_yes", "title": "כן, אגיע! 🎊"}},
                    {"type": "reply", "reply": {"id": "rsvp_no",  "title": "לצערי, לא אוכל"}},
                    {"type": "reply", "reply": {"id": "rsvp_q",   "title": "יש לי שאלה 💬"}},
                ]
            },
        },
    })


async def send_whatsapp_template(phone: str, guest_name: str) -> bool:
    """
    Alternative: send via an approved Meta template named 'wedding_invitation'.
    Use this for first-contact outreach to any number.
    Create the template at: Meta Business Manager -> WhatsApp -> Message Templates
    Template body example (Hebrew, 1 variable):
      שלום {{1}}, הילה ונועם שמחים להזמינך לחתונתם! לפרטים ואישור הגעה שלח/י הודעה כאן 💍
    """
    return await _wa_post({
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "template",
        "template": {
            "name": "wedding_invitation",
            "language": {"code": "he"},
            "components": [
                {
                    "type": "body",
                    "parameters": [{"type": "text", "text": guest_name}],
                }
            ],
        },
    })


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


@app.get("/api/export/csv")
async def export_csv():
    export_summary_csv()
    return FileResponse(
        SUMMARY_CSV,
        media_type="text/csv",
        filename="rsvp_summary.csv",
    )


@app.delete("/api/rsvps/{rsvp_id}")
async def delete_rsvp(rsvp_id: int):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM rsvps WHERE id = ?", (rsvp_id,))
    conn.commit()
    conn.close()
    return {"deleted": rsvp_id}


# -- Guest list (CSV import + invitation sending) -----------------------------

@app.post("/api/guests/upload")
async def upload_guests(file: UploadFile = File(...)):
    content = await file.read()
    text = content.decode("utf-8-sig")  # Handle Excel BOM
    reader = csv.DictReader(io.StringIO(text))

    imported = 0
    errors = []
    conn = sqlite3.connect(DB_PATH)

    for i, row in enumerate(reader, 1):
        # Accept Hebrew or English column headers
        name = (row.get("name") or row.get("שם") or "").strip()
        phone = (row.get("phone") or row.get("טלפון") or row.get("מספר") or "").strip()

        if not name or not phone:
            errors.append(f"שורה {i}: חסר שם או טלפון")
            continue

        phone_norm = normalize_phone(phone)
        if len(phone_norm) < 10:
            errors.append(f"שורה {i}: מספר טלפון לא תקין '{phone}'")
            continue

        try:
            conn.execute(
                "INSERT OR IGNORE INTO guests (name, phone) VALUES (?, ?)",
                (name, phone_norm),
            )
            imported += 1
        except Exception as e:
            errors.append(f"שורה {i}: {e}")

    conn.commit()
    conn.close()
    return {"imported": imported, "errors": errors}


@app.get("/api/guests")
async def get_guests():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM guests ORDER BY name ASC").fetchall()
    conn.close()
    return [dict(row) for row in rows]


@app.delete("/api/guests/{guest_id}")
async def delete_guest(guest_id: int):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM guests WHERE id = ?", (guest_id,))
    conn.commit()
    conn.close()
    return {"deleted": guest_id}


@app.post("/api/guests/send-invitations")
async def send_invitations():
    """Send invitation with RSVP buttons to all guests who haven't received one yet."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    guests = conn.execute(
        "SELECT * FROM guests WHERE invitation_sent = 0"
    ).fetchall()

    sent = 0
    failed = 0

    for guest in guests:
        success = await send_whatsapp_template(guest["phone"], guest["name"])
        if success:
            conn.execute(
                "UPDATE guests SET invitation_sent = 1, sent_at = CURRENT_TIMESTAMP WHERE id = ?",
                (guest["id"],),
            )
            sent += 1
        else:
            failed += 1

    conn.commit()
    conn.close()
    return {"sent": sent, "failed": failed}


# -- WhatsApp webhook (Meta Cloud API) ----------------------------------------

@app.get("/webhook/whatsapp")
async def verify_whatsapp_webhook(request: Request):
    from urllib.parse import parse_qs
    qs = parse_qs(str(request.url.query))
    mode    = (qs.get("hub.mode")         or qs.get("hub_mode")         or [""])[0]
    token   = (qs.get("hub.verify_token") or qs.get("hub_verify_token") or [""])[0]
    challenge = (qs.get("hub.challenge")  or qs.get("hub_challenge")    or [""])[0]
    if mode == "subscribe" and token == WHATSAPP_VERIFY_TOKEN:
        return Response(content=challenge, media_type="text/plain")
    return Response(status_code=403)


@app.post("/webhook/whatsapp")
async def whatsapp_webhook(request: Request):
    body = await request.json()

    try:
        change_value = body["entry"][0]["changes"][0]["value"]
        if "messages" not in change_value:
            return {"status": "ignored"}

        message = change_value["messages"][0]
        from_number = message["from"]
        msg_type = message.get("type")

        # Handle both plain text and quick-reply button taps
        if msg_type == "text":
            text = message["text"]["body"]
        elif msg_type == "interactive":
            interactive = message.get("interactive", {})
            if interactive.get("type") == "button_reply":
                text = interactive["button_reply"]["title"]
            else:
                return {"status": "interactive type not handled"}
        else:
            return {"status": "non-text ignored"}

    except (KeyError, IndexError):
        return {"status": "invalid payload"}

    response_text, _ = await process_message(text, session_id=from_number)
    await send_whatsapp_text(from_number, response_text)

    return {"status": "ok"}

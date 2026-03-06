from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from mcp.server.fastmcp import FastMCP
import sqlite3
import os
import json
import requests
from whatsapp import (
    search_contacts as whatsapp_search_contacts,
    list_messages as whatsapp_list_messages,
    list_chats as whatsapp_list_chats,
    get_chat as whatsapp_get_chat,
    get_direct_chat_by_contact as whatsapp_get_direct_chat_by_contact,
    get_contact_chats as whatsapp_get_contact_chats,
    get_last_interaction as whatsapp_get_last_interaction,
    get_message_context as whatsapp_get_message_context,
    send_message as whatsapp_send_message,
    send_file as whatsapp_send_file,
    send_audio_message as whatsapp_audio_voice_message,
    download_media as whatsapp_download_media
)

MESSAGES_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'whatsapp-bridge', 'store', 'messages.db')
WHATSAPP_API_BASE_URL = "http://localhost:8080/api"
LEADS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'leads.json')

def _load_leads() -> dict:
    if os.path.exists(LEADS_FILE):
        with open(LEADS_FILE) as f:
            return json.load(f)
    return {}

def _save_leads(leads: dict):
    with open(LEADS_FILE, 'w') as f:
        json.dump(leads, f, indent=2)

mcp = FastMCP("whatsapp")

def _serialize(obj):
    """Recursively serialize dataclass/datetime objects to plain dicts."""
    if obj is None:
        return None
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, bool):
        return obj
    if isinstance(obj, (int, float, str)):
        return obj
    if isinstance(obj, list):
        return [_serialize(i) for i in obj]
    if hasattr(obj, '__dict__'):
        return {k: _serialize(v) for k, v in obj.__dict__.items()}
    return obj

def _format_ng_number(phone: str) -> str:
    """Convert Nigerian local number to international format for WhatsApp.
    Examples: 08033001234 -> 2348033001234, +2348033001234 -> 2348033001234
    """
    phone = phone.strip().replace(" ", "").replace("-", "").replace("+", "")
    if phone.startswith("0") and len(phone) == 11:
        phone = "234" + phone[1:]
    elif phone.startswith("234") and len(phone) == 13:
        pass  # already correct
    return phone


# ── CORE TOOLS ────────────────────────────────────────────────────────────────

@mcp.tool()
def search_contacts(query: str) -> List[Dict[str, Any]]:
    """Search WhatsApp contacts by name or phone number.

    Args:
        query: Search term to match against contact names or phone numbers
    """
    return [_serialize(c) for c in whatsapp_search_contacts(query)]

@mcp.tool()
def list_messages(
    after: Optional[str] = None,
    before: Optional[str] = None,
    sender_phone_number: Optional[str] = None,
    chat_jid: Optional[str] = None,
    query: Optional[str] = None,
    limit: int = 20,
    page: int = 0,
    include_context: bool = True,
    context_before: int = 1,
    context_after: int = 1
) -> List[Dict[str, Any]]:
    """Get WhatsApp messages matching specified criteria with optional context.

    Args:
        after: ISO-8601 datetime to only return messages after this date
        before: ISO-8601 datetime to only return messages before this date
        sender_phone_number: Filter by sender phone number
        chat_jid: Filter by chat JID
        query: Search term to filter by message content
        limit: Max messages to return (default 20)
        page: Page number (default 0)
        include_context: Include surrounding messages (default True)
        context_before: Messages before each match (default 1)
        context_after: Messages after each match (default 1)
    """
    messages = whatsapp_list_messages(
        after=after, before=before, sender_phone_number=sender_phone_number,
        chat_jid=chat_jid, query=query, limit=limit, page=page,
        include_context=include_context, context_before=context_before,
        context_after=context_after
    )
    return [_serialize(m) for m in messages]

@mcp.tool()
def list_chats(
    query: Optional[str] = None,
    limit: int = 20,
    page: int = 0,
    include_last_message: bool = True,
    sort_by: str = "last_active"
) -> List[Dict[str, Any]]:
    """Get WhatsApp chats matching specified criteria.

    Args:
        query: Filter chats by name or JID
        limit: Max chats to return (default 20)
        page: Page number (default 0)
        include_last_message: Include last message preview (default True)
        sort_by: 'last_active' or 'name' (default 'last_active')
    """
    chats = whatsapp_list_chats(query=query, limit=limit, page=page,
                                include_last_message=include_last_message, sort_by=sort_by)
    return [_serialize(c) for c in chats]

@mcp.tool()
def get_chat(chat_jid: str, include_last_message: bool = True) -> Dict[str, Any]:
    """Get WhatsApp chat metadata by JID."""
    return _serialize(whatsapp_get_chat(chat_jid, include_last_message))

@mcp.tool()
def get_direct_chat_by_contact(sender_phone_number: str) -> Dict[str, Any]:
    """Get WhatsApp chat metadata by sender phone number."""
    return _serialize(whatsapp_get_direct_chat_by_contact(sender_phone_number))

@mcp.tool()
def get_contact_chats(jid: str, limit: int = 20, page: int = 0) -> List[Dict[str, Any]]:
    """Get all WhatsApp chats involving a contact.

    Args:
        jid: The contact's JID
        limit: Max chats to return (default 20)
        page: Page number (default 0)
    """
    return [_serialize(c) for c in whatsapp_get_contact_chats(jid, limit, page)]

@mcp.tool()
def get_last_interaction(jid: str) -> str:
    """Get most recent WhatsApp message involving a contact.

    Args:
        jid: The JID of the contact
    """
    return whatsapp_get_last_interaction(jid)

@mcp.tool()
def get_message_context(message_id: str, before: int = 5, after: int = 5) -> Dict[str, Any]:
    """Get context around a specific WhatsApp message.

    Args:
        message_id: The ID of the message
        before: Messages to include before (default 5)
        after: Messages to include after (default 5)
    """
    return _serialize(whatsapp_get_message_context(message_id, before, after))

@mcp.tool()
def send_message(recipient: str, message: str) -> Dict[str, Any]:
    """Send a WhatsApp message to a person or group.

    Args:
        recipient: Phone number with country code (no +) or JID
        message: The message text to send
    """
    if not recipient:
        return {"success": False, "message": "Recipient must be provided"}
    success, status_message = whatsapp_send_message(recipient, message)
    return {"success": success, "message": status_message}

@mcp.tool()
def send_file(recipient: str, media_path: str) -> Dict[str, Any]:
    """Send a file (image, video, document) via WhatsApp.

    Args:
        recipient: Phone number with country code (no +) or JID
        media_path: Absolute path to the media file
    """
    success, status_message = whatsapp_send_file(recipient, media_path)
    return {"success": success, "message": status_message}

@mcp.tool()
def send_audio_message(recipient: str, media_path: str) -> Dict[str, Any]:
    """Send an audio file as a WhatsApp voice message.

    Args:
        recipient: Phone number with country code (no +) or JID
        media_path: Absolute path to the audio file
    """
    success, status_message = whatsapp_audio_voice_message(recipient, media_path)
    return {"success": success, "message": status_message}

@mcp.tool()
def download_media(message_id: str, chat_jid: str) -> Dict[str, Any]:
    """Download media from a WhatsApp message.

    Args:
        message_id: The ID of the message containing media
        chat_jid: The JID of the chat
    """
    file_path = whatsapp_download_media(message_id, chat_jid)
    if file_path:
        return {"success": True, "message": "Media downloaded successfully", "file_path": file_path}
    return {"success": False, "message": "Failed to download media"}


# ── MARKETING / PROSPECTING TOOLS ─────────────────────────────────────────────

@mcp.tool()
def verify_whatsapp_number(phone: str) -> Dict[str, Any]:
    """Check if a phone number is registered on WhatsApp before sending a message.
    Automatically converts Nigerian local numbers (08033...) to international format (2348033...).

    Args:
        phone: Nigerian phone number in any format (e.g. 08033001234, +2348033001234, 2348033001234)

    Returns:
        Dictionary with 'on_whatsapp' (bool), 'formatted_number', and 'jid' if found
    """
    formatted = _format_ng_number(phone)
    try:
        response = requests.get(f"{WHATSAPP_API_BASE_URL}/check/{formatted}", timeout=10)
        if response.status_code == 200:
            data = response.json()
            return {
                "on_whatsapp": data.get("exists", False),
                "formatted_number": formatted,
                "jid": data.get("jid", f"{formatted}@s.whatsapp.net"),
                "raw_response": data
            }
        # If API doesn't support check endpoint, fall back to DB lookup
    except Exception:
        pass

    # Fallback: check messages DB for any prior interaction
    try:
        conn = sqlite3.connect(MESSAGES_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT jid FROM chats WHERE jid LIKE ? LIMIT 1", (f"%{formatted}%",))
        row = cursor.fetchone()
        conn.close()
        if row:
            return {"on_whatsapp": True, "formatted_number": formatted, "jid": row[0], "note": "Found in local DB"}
    except Exception:
        pass

    return {
        "on_whatsapp": "unknown",
        "formatted_number": formatted,
        "jid": f"{formatted}@s.whatsapp.net",
        "note": "Could not verify — try sending directly"
    }

@mcp.tool()
def send_outreach(phone: str, message: str) -> Dict[str, Any]:
    """Send a cold outreach WhatsApp message to a Nigerian phone number.
    Automatically converts local Nigerian numbers (08033...) to international format.
    Use this for all prospecting messages.

    Args:
        phone: Nigerian phone number in any format (08033001234, +2348033001234, etc.)
        message: The outreach message to send
    """
    formatted = _format_ng_number(phone)
    success, status = whatsapp_send_message(formatted, message)
    return {
        "success": success,
        "message": status,
        "sent_to": formatted,
        "original_number": phone
    }

@mcp.tool()
def get_prospect_replies(hours_back: int = 48) -> List[Dict[str, Any]]:
    """Get replies received from unsaved contacts (prospects) in the last N hours.
    Use this to monitor your outreach pipeline — these are people who responded to your messages.

    Args:
        hours_back: How many hours back to scan for replies (default 48)
    """
    try:
        conn = sqlite3.connect(MESSAGES_DB_PATH)
        cursor = conn.cursor()

        # Get messages from contacts (not me) where the chat name is just a number (unsaved contacts)
        # and where I have also sent a message to that chat (i.e., I initiated contact)
        cursor.execute("""
            SELECT DISTINCT
                m.chat_jid,
                c.name,
                m.content,
                m.timestamp,
                m.sender,
                m.is_from_me
            FROM messages m
            JOIN chats c ON m.chat_jid = c.jid
            WHERE
                m.is_from_me = 0
                AND m.timestamp >= datetime('now', ? || ' hours')
                AND m.chat_jid NOT LIKE '%@g.us'
                AND m.chat_jid NOT LIKE '%@broadcast'
                AND m.chat_jid NOT LIKE 'status%'
                AND m.content != ''
                AND m.chat_jid IN (
                    SELECT DISTINCT chat_jid FROM messages WHERE is_from_me = 1
                )
            ORDER BY m.timestamp DESC
            LIMIT 50
        """, (f"-{hours_back}",))

        rows = cursor.fetchall()
        conn.close()

        results = []
        for row in rows:
            results.append({
                "chat_jid": row[0],
                "contact_name": row[1] if row[1] else row[0].split("@")[0],
                "message": row[2],
                "timestamp": row[3],
                "sender": row[4],
                "is_from_me": bool(row[5])
            })

        return results if results else [{"info": f"No prospect replies in the last {hours_back} hours"}]

    except sqlite3.Error as e:
        return [{"error": str(e)}]

@mcp.tool()
def get_unread_messages(limit: int = 20) -> List[Dict[str, Any]]:
    """Get the most recent incoming messages from contacts (not sent by you).
    Use this to monitor your inbox for new leads or replies.

    Args:
        limit: Max messages to return (default 20)
    """
    try:
        conn = sqlite3.connect(MESSAGES_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT m.chat_jid, c.name, m.content, m.timestamp, m.sender, m.id
            FROM messages m
            JOIN chats c ON m.chat_jid = c.jid
            WHERE m.is_from_me = 0
                AND m.chat_jid NOT LIKE '%@broadcast'
                AND m.chat_jid NOT LIKE 'status%'
                AND m.content != ''
            ORDER BY m.timestamp DESC LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        conn.close()
        return [{"chat_jid": r[0], "contact_name": r[1] if r[1] else r[0].split("@")[0],
                 "message": r[2], "timestamp": r[3], "sender": r[4], "message_id": r[5]} for r in rows]
    except sqlite3.Error as e:
        return [{"error": str(e)}]

@mcp.tool()
def get_outreach_summary() -> Dict[str, Any]:
    """Get a full pipeline summary: messages sent, replies, follow-ups due, lead stages.
    Run this at the start of any session to know exactly where things stand.
    """
    try:
        conn = sqlite3.connect(MESSAGES_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM messages WHERE is_from_me = 1 AND chat_jid NOT LIKE '%@g.us'")
        total_sent = cursor.fetchone()[0]
        cursor.execute("""SELECT COUNT(DISTINCT chat_jid) FROM messages
            WHERE is_from_me = 0 AND chat_jid IN (SELECT DISTINCT chat_jid FROM messages WHERE is_from_me = 1)
            AND chat_jid NOT LIKE '%@g.us'""")
        chats_with_replies = cursor.fetchone()[0]
        cursor.execute("""SELECT COUNT(*) FROM messages
            WHERE is_from_me = 0 AND timestamp >= datetime('now', '-48 hours')
            AND chat_jid NOT LIKE '%@g.us'
            AND chat_jid IN (SELECT DISTINCT chat_jid FROM messages WHERE is_from_me = 1)""")
        recent_replies = cursor.fetchone()[0]
        cursor.execute("""SELECT COUNT(DISTINCT chat_jid) FROM messages
            WHERE is_from_me = 1 AND timestamp >= datetime('now', '-7 days') AND chat_jid NOT LIKE '%@g.us'""")
        contacted_this_week = cursor.fetchone()[0]
        conn.close()

        # Pipeline state from leads file
        leads = _load_leads()
        stages = {"cold": 0, "contacted": 0, "replied": 0, "call_booked": 0, "closed": 0}
        followups_due = []
        now = datetime.now()
        for phone, lead in leads.items():
            stage = lead.get("stage", "cold")
            stages[stage] = stages.get(stage, 0) + 1
            if stage == "contacted" and lead.get("contacted_at"):
                try:
                    days = (now - datetime.fromisoformat(lead["contacted_at"])).days
                    if days >= 3:
                        followups_due.append({
                            "phone": phone,
                            "name": lead.get("name", phone),
                            "business": lead.get("business", ""),
                            "days_since_contact": days,
                            "status": "overdue" if days >= 7 else "due"
                        })
                except: pass

        return {
            "whatsapp_messages_sent_total": total_sent,
            "prospects_who_replied": chats_with_replies,
            "replies_last_48hrs": recent_replies,
            "contacts_this_week": contacted_this_week,
            "pipeline": stages,
            "total_leads_tracked": len(leads),
            "followups_due": followups_due
        }
    except sqlite3.Error as e:
        return {"error": str(e)}

@mcp.tool()
def add_lead(phone: str, name: str, business: str = "", notes: str = "", stage: str = "cold") -> Dict[str, Any]:
    """Add a new prospect to the pipeline. Use this after finding a lead.

    Args:
        phone: Nigerian phone number (any format: 08033001234 or 2348033001234)
        name: Contact name
        business: Business or company name
        notes: Where you found them, what the angle is
        stage: cold | contacted | replied | call_booked | closed (default: cold)
    """
    leads = _load_leads()
    phone = _format_ng_number(phone)
    leads[phone] = {
        "name": name,
        "business": business,
        "notes": notes,
        "stage": stage,
        "contacted_at": datetime.now().isoformat() if stage == "contacted" else None,
        "replied_at": None,
        "added_at": datetime.now().isoformat()
    }
    _save_leads(leads)
    return {"success": True, "message": f"{name} added to pipeline as '{stage}'", "phone": phone}

@mcp.tool()
def update_lead_stage(phone: str, stage: str, notes: str = "") -> Dict[str, Any]:
    """Update a lead's pipeline stage. Call this after sending a message, getting a reply, or booking a call.

    Args:
        phone: Lead's phone number (as stored)
        stage: cold | contacted | replied | call_booked | closed
        notes: Optional note to append
    """
    leads = _load_leads()
    if phone not in leads:
        return {"success": False, "message": f"Lead {phone} not found"}
    leads[phone]["stage"] = stage
    if stage == "contacted" and not leads[phone].get("contacted_at"):
        leads[phone]["contacted_at"] = datetime.now().isoformat()
    if stage == "replied":
        leads[phone]["replied_at"] = datetime.now().isoformat()
    if notes:
        existing = leads[phone].get("notes", "")
        leads[phone]["notes"] = f"{existing}\n[{datetime.now().strftime('%d %b')}] {notes}".strip()
    _save_leads(leads)
    return {"success": True, "message": f"Stage updated to '{stage}' for {leads[phone].get('name', phone)}"}

@mcp.tool()
def get_pipeline() -> List[Dict[str, Any]]:
    """Get all leads in the pipeline with their current stage, follow-up status, and last message.
    Use this to see the full picture before deciding what to do next.
    """
    leads = _load_leads()
    now = datetime.now()
    result = []
    for phone, lead in leads.items():
        days_since = None
        followup_status = "ok"
        if lead.get("contacted_at"):
            try:
                days_since = (now - datetime.fromisoformat(lead["contacted_at"])).days
                if lead.get("stage") == "contacted":
                    if days_since >= 7:
                        followup_status = "cold"
                    elif days_since >= 3:
                        followup_status = "overdue"
                    elif days_since >= 1:
                        followup_status = "due"
            except: pass

        # Get last WhatsApp message
        last_msg = None
        try:
            conn = sqlite3.connect(MESSAGES_DB_PATH)
            c = conn.cursor()
            c.execute("""SELECT content, timestamp, is_from_me FROM messages
                WHERE chat_jid LIKE ? ORDER BY timestamp DESC LIMIT 1""", (f"%{phone}%",))
            row = c.fetchone()
            conn.close()
            if row:
                last_msg = {"content": row[0][:80], "timestamp": row[1], "from_me": bool(row[2])}
        except: pass

        result.append({
            "phone": phone,
            "name": lead.get("name"),
            "business": lead.get("business"),
            "stage": lead.get("stage", "cold"),
            "followup_status": followup_status,
            "days_since_contact": days_since,
            "notes": lead.get("notes"),
            "last_whatsapp_message": last_msg
        })

    result.sort(key=lambda x: ["cold","contacted","replied","call_booked","closed"].index(x.get("stage","cold")))
    return result


if __name__ == "__main__":
    mcp.run(transport='stdio')

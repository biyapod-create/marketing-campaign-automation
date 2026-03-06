"""
Allennetic Campaign MCP Server
================================
Exposes campaign tools to Claude Desktop:
  - send_email          : Send a single email
  - send_batch_emails   : Batch send from campaign_ready.csv
  - test_smtp           : Verify SMTP credentials
  - get_campaign_status : Stats from leads + sent log
  - validate_email      : Check if an email is deliverable
  - get_sent_log        : View recent sends
"""

import sys
import os
import csv
import json
import smtplib
import ssl
from pathlib import Path
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# ── Paths ──────────────────────────────────────────────────────────────────
CAMPAIGN_DIR = Path(__file__).parent.parent
load_dotenv(CAMPAIGN_DIR / ".env")

SMTP_HOST    = os.getenv("SMTP_HOST", "allennetic.com")
SMTP_PORT    = int(os.getenv("SMTP_PORT", "465"))
SMTP_USER    = os.getenv("SMTP_USER", "info@allennetic.com")
SMTP_PASS    = os.getenv("SMTP_PASS", "")
SENDER_NAME  = "Allennetic"

SENT_LOG     = CAMPAIGN_DIR / "emails" / "sent_log.csv"
LEADS_DB     = CAMPAIGN_DIR / "leads_database.csv"
RESPONSES_CSV= CAMPAIGN_DIR / "responses" / "response_tracking.csv"

# ── MCP App ────────────────────────────────────────────────────────────────
mcp = FastMCP("allennetic-campaign")


# ── Helpers ────────────────────────────────────────────────────────────────
def _smtp_send(to_email: str, subject: str, body: str, to_name: str = "") -> dict:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = f"{SENDER_NAME} <{SMTP_USER}>"
    msg["To"]      = f"{to_name} <{to_email}>" if to_name else to_email
    msg["Reply-To"]= SMTP_USER
    msg.attach(MIMEText(body, "plain", "utf-8"))
    ctx = ssl.create_default_context()
    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=ctx) as s:
        s.login(SMTP_USER, SMTP_PASS)
        s.sendmail(SMTP_USER, to_email, msg.as_string())


def _log_send(to_email, to_name, company, subject, status, error=""):
    SENT_LOG.parent.mkdir(parents=True, exist_ok=True)
    write_header = not SENT_LOG.exists() or SENT_LOG.stat().st_size == 0
    with open(SENT_LOG, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if write_header:
            w.writerow(["timestamp","to_email","to_name","company","subject","status","error"])
        w.writerow([datetime.now().isoformat(), to_email, to_name, company, subject, status, error])


def _already_sent() -> set:
    if not SENT_LOG.exists():
        return set()
    with open(SENT_LOG, newline="", encoding="utf-8") as f:
        return {r["to_email"] for r in csv.DictReader(f) if r.get("status") == "sent"}


def _find_latest_campaign_csv() -> str | None:
    import glob
    csvs = sorted(
        glob.glob(str(CAMPAIGN_DIR / "**" / "campaign_ready.csv"), recursive=True),
        key=os.path.getmtime, reverse=True
    )
    return csvs[0] if csvs else None


# ── Tools ──────────────────────────────────────────────────────────────────

@mcp.tool()
def test_smtp() -> dict:
    """Test the SMTP connection and verify credentials are working."""
    try:
        ctx = ssl.create_default_context()
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=ctx) as s:
            s.login(SMTP_USER, SMTP_PASS)
        return {"status": "ok", "host": SMTP_HOST, "port": SMTP_PORT, "user": SMTP_USER}
    except Exception as e:
        return {"status": "failed", "error": str(e)}


@mcp.tool()
def send_email(to_email: str, subject: str, body: str, to_name: str = "", company: str = "") -> dict:
    """
    Send a single plain-text email to a prospect.

    Args:
        to_email: Recipient email address
        subject:  Email subject line
        body:     Plain-text email body
        to_name:  Recipient display name (optional)
        company:  Recipient company (for logging, optional)
    """
    try:
        _smtp_send(to_email, subject, body, to_name)
        _log_send(to_email, to_name, company, subject, "sent")
        return {"status": "sent", "to": to_email, "subject": subject, "timestamp": datetime.now().isoformat()}
    except smtplib.SMTPAuthenticationError as e:
        _log_send(to_email, to_name, company, subject, "failed", str(e))
        return {"status": "failed", "error": f"Auth error: {e}"}
    except smtplib.SMTPRecipientsRefused as e:
        _log_send(to_email, to_name, company, subject, "bounced", str(e))
        return {"status": "bounced", "error": f"Recipient refused: {e}"}
    except Exception as e:
        _log_send(to_email, to_name, company, subject, "failed", str(e))
        return {"status": "failed", "error": str(e)}


@mcp.tool()
def send_batch_emails(limit: int = 10, dry_run: bool = True, delay_seconds: float = 3.0) -> dict:
    """
    Send a batch of emails from the latest campaign_ready.csv.
    Automatically skips addresses already sent to.

    Args:
        limit:          Max number of emails to send in this batch (default 10)
        dry_run:        If True, log only — don't actually send (default True, set False to go live)
        delay_seconds:  Seconds between sends to avoid spam flags (default 3.0)
    """
    csv_path = _find_latest_campaign_csv()
    if not csv_path:
        return {"status": "error", "message": "No campaign_ready.csv found. Run the campaign pipeline first."}

    already_sent = _already_sent()
    with open(csv_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    batch = [r for r in rows if r.get("email", "").strip() and r["email"].strip() not in already_sent][:limit]

    results = {"dry_run": dry_run, "csv": csv_path, "batch_size": len(batch), "sent": 0, "failed": 0, "skipped": 0, "details": []}

    import time
    for row in batch:
        to_email = row.get("email", "").strip()
        to_name  = row.get("name", "").strip()
        company  = row.get("company", "").strip()
        subject  = row.get("subject_line", "").strip()
        body     = row.get("body", "").strip()

        if not (to_email and subject and body):
            results["skipped"] += 1
            results["details"].append({"email": to_email, "status": "skipped"})
            continue

        if dry_run:
            _log_send(to_email, to_name, company, subject, "dry_run")
            results["sent"] += 1
            results["details"].append({"email": to_email, "status": "dry_run", "subject": subject})
        else:
            try:
                _smtp_send(to_email, subject, body, to_name)
                _log_send(to_email, to_name, company, subject, "sent")
                results["sent"] += 1
                results["details"].append({"email": to_email, "status": "sent"})
                time.sleep(delay_seconds)
            except Exception as e:
                _log_send(to_email, to_name, company, subject, "failed", str(e))
                results["failed"] += 1
                results["details"].append({"email": to_email, "status": "failed", "error": str(e)})

    return results


@mcp.tool()
def get_campaign_status() -> dict:
    """Get overall campaign statistics: total leads, emails sent, bounce rate, responses."""
    stats = {"timestamp": datetime.now().isoformat()}

    # Leads count
    if LEADS_DB.exists():
        with open(LEADS_DB, newline="", encoding="utf-8") as f:
            stats["total_leads"] = sum(1 for _ in csv.DictReader(f))
    else:
        stats["total_leads"] = 0

    # Sent log stats
    if SENT_LOG.exists():
        with open(SENT_LOG, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        stats["total_sent"]    = sum(1 for r in rows if r.get("status") == "sent")
        stats["total_bounced"] = sum(1 for r in rows if r.get("status") == "bounced")
        stats["total_failed"]  = sum(1 for r in rows if r.get("status") == "failed")
        stats["dry_runs"]      = sum(1 for r in rows if r.get("status") == "dry_run")
        if stats["total_sent"] > 0:
            stats["bounce_rate"] = f"{(stats['total_bounced'] / stats['total_sent']) * 100:.1f}%"
        else:
            stats["bounce_rate"] = "N/A"
    else:
        stats.update({"total_sent": 0, "total_bounced": 0, "total_failed": 0, "bounce_rate": "N/A"})

    # Responses
    if RESPONSES_CSV.exists():
        with open(RESPONSES_CSV, newline="", encoding="utf-8") as f:
            stats["total_responses"] = sum(1 for _ in csv.DictReader(f))
    else:
        stats["total_responses"] = 0

    return stats


@mcp.tool()
def get_sent_log(limit: int = 20) -> dict:
    """
    View the most recent email send activity.

    Args:
        limit: Number of recent entries to return (default 20)
    """
    if not SENT_LOG.exists():
        return {"status": "empty", "entries": []}

    with open(SENT_LOG, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    recent = rows[-limit:][::-1]  # most recent first
    return {"total_entries": len(rows), "showing": len(recent), "entries": recent}


@mcp.tool()
def validate_email(email: str) -> dict:
    """
    Validate an email address — check syntax and MX records.

    Args:
        email: Email address to validate
    """
    import re
    import dns.resolver

    result = {"email": email, "valid": False, "syntax_valid": False, "mx_found": False, "confidence": "low"}

    # Syntax check
    pattern = r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        result["details"] = "Invalid syntax"
        return result
    result["syntax_valid"] = True

    # MX check
    domain = email.split("@")[1]
    try:
        answers = dns.resolver.resolve(domain, "MX")
        result["mx_found"] = True
        result["mx_records"] = [str(r.exchange) for r in answers]
        result["valid"] = True
        result["confidence"] = "medium"
        result["details"] = "Syntax valid, MX records found"
    except Exception as e:
        result["details"] = f"No MX records: {e}"

    return result


# ── Entry point ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    mcp.run()

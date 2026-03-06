"""
Email Sender
============
SMTP email sending module for Allennetic campaign system.
Handles single sends, batch CSV sends, logging, and rate limiting.
"""

import smtplib
import ssl
import csv
import os
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from datetime import datetime
from typing import Dict
from dotenv import load_dotenv

_campaign_dir = Path(__file__).parent.parent
load_dotenv(_campaign_dir / ".env")

SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
SENDER_NAME = os.getenv("SENDER_NAME", "Campaign")
SENT_LOG_PATH = _campaign_dir / "emails" / "sent_log.csv"


class EmailSender:

    def __init__(self):
        self.smtp_host = SMTP_HOST
        self.smtp_port = SMTP_PORT
        self.smtp_user = SMTP_USER
        self.smtp_pass = SMTP_PASS
        self.sent_log = SENT_LOG_PATH
        self._ensure_log_file()

    def _ensure_log_file(self):
        self.sent_log.parent.mkdir(parents=True, exist_ok=True)
        if not self.sent_log.exists() or self.sent_log.stat().st_size == 0:
            with open(self.sent_log, "w", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow(["timestamp","to_email","to_name","company","subject","status","error"])

    def _log(self, to_email, to_name, company, subject, status, error=""):
        with open(self.sent_log, "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow([datetime.now().isoformat(), to_email, to_name, company, subject, status, error])

    def send_email(self, to_email: str, subject: str, body: str, to_name: str = "", company: str = "") -> Dict:
        """Send a single plain-text email via SSL SMTP."""
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{SENDER_NAME} <{self.smtp_user}>"
        msg["To"] = f"{to_name} <{to_email}>" if to_name else to_email
        msg["Reply-To"] = self.smtp_user
        msg.attach(MIMEText(body, "plain", "utf-8"))

        try:
            ctx = ssl.create_default_context()
            with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, context=ctx) as s:
                s.login(self.smtp_user, self.smtp_pass)
                s.sendmail(self.smtp_user, to_email, msg.as_string())
            self._log(to_email, to_name, company, subject, "sent")
            return {"status": "sent", "to_email": to_email, "to_name": to_name, "subject": subject, "timestamp": datetime.now().isoformat()}

        except smtplib.SMTPAuthenticationError as e:
            err = f"Auth failed: {e}"
            self._log(to_email, to_name, company, subject, "failed", err)
            return {"status": "failed", "to_email": to_email, "error": err}

        except smtplib.SMTPRecipientsRefused as e:
            err = f"Recipient refused: {e}"
            self._log(to_email, to_name, company, subject, "bounced", err)
            return {"status": "bounced", "to_email": to_email, "error": err}

        except Exception as e:
            err = str(e)
            self._log(to_email, to_name, company, subject, "failed", err)
            return {"status": "failed", "to_email": to_email, "error": err}

    def send_batch_from_csv(self, csv_path: str, limit: int = 10, delay_seconds: float = 3.0, dry_run: bool = True) -> Dict:
        """Send emails from a campaign_ready.csv. Skips already-sent addresses."""
        results = {"sent": 0, "failed": 0, "skipped": 0, "dry_run": dry_run, "details": []}
        already_sent = self._get_already_sent()

        with open(csv_path, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))

        batch = [r for r in rows if r.get("email") and r["email"].strip() not in already_sent][:limit]

        for row in batch:
            to_email = row["email"].strip()
            to_name  = row.get("name", "").strip()
            company  = row.get("company", "").strip()
            subject  = row.get("subject_line", "").strip()
            body     = row.get("body", "").strip()

            if not (to_email and subject and body):
                results["skipped"] += 1
                results["details"].append({"email": to_email, "status": "skipped", "reason": "missing fields"})
                continue

            if dry_run:
                self._log(to_email, to_name, company, subject, "dry_run")
                results["sent"] += 1
                results["details"].append({"email": to_email, "status": "dry_run", "subject": subject})
            else:
                res = self.send_email(to_email, subject, body, to_name, company)
                results["sent" if res["status"] == "sent" else "failed"] += 1
                results["details"].append(res)
                time.sleep(delay_seconds)

        results["total_processed"] = len(batch)
        return results

    def _get_already_sent(self) -> set:
        if not self.sent_log.exists():
            return set()
        with open(self.sent_log, newline="", encoding="utf-8") as f:
            return {r["to_email"] for r in csv.DictReader(f) if r.get("status") == "sent"}

    def test_connection(self) -> Dict:
        """Verify SMTP credentials without sending."""
        try:
            ctx = ssl.create_default_context()
            with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, context=ctx) as s:
                s.login(self.smtp_user, self.smtp_pass)
            return {"status": "ok", "host": self.smtp_host, "port": self.smtp_port, "user": self.smtp_user}
        except Exception as e:
            return {"status": "failed", "error": str(e)}

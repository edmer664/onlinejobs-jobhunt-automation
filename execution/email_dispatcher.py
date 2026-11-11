"""
OnlineJobs.ph Email Application Dispatcher & Logger (Route A).
Used when an employer explicitly requests application via email:
- Formats email with mandatory subject line and screening codes
- Attaches the candidate PDF resume (from config/resume.pdf or RESUME_PDF_PATH)
- Connect points spent = 0 (100% connect points conserved)
- STRICT RULE: Do NOT apply on the OnlineJobs.ph platform when this route is used
- Updates SQLite jobs.db with status 'Applied' and route 'Email'
- Saves .eml audit message file
"""

import argparse
import json
import os
import smtplib
import sqlite3
import sys
from datetime import datetime, timezone
from email.message import EmailMessage
from typing import Any, Dict, Optional

# Add src and repo root to sys.path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
SRC_DIR = os.path.join(PROJECT_ROOT, "src")

for p in (PROJECT_ROOT, SRC_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    from src.db import DB_PATH, get_connection, update_job_status_and_notes
    from src.config_loader import get_candidate_profile
except ImportError:
    from db import DB_PATH, get_connection, update_job_status_and_notes
    from config_loader import get_candidate_profile

DEFAULT_RESUME_PDF = os.environ.get(
    "RESUME_PDF_PATH",
    os.path.join(PROJECT_ROOT, "config", "resume.pdf"),
)


def dispatch_email_application(
    job_id: str,
    to_email: str,
    subject: str,
    body: str,
    resume_path: Optional[str] = None,
    from_email: Optional[str] = None,
    from_name: Optional[str] = None,
    smtp_host: str = "",
    smtp_port: int = 587,
    smtp_user: str = "",
    smtp_pass: str = "",
    draft_dir: Optional[str] = None,
    db_path: str = DB_PATH,
) -> Dict[str, Any]:
    """
    Creates and dispatches (or drafts) an email application with attached resume PDF.
    """
    profile = get_candidate_profile()
    candidate = profile.get("candidate", {})

    sender_name = from_name or candidate.get("display_name") or candidate.get("name") or "Candidate"
    sender_email = (
        from_email
        or os.environ.get("FROM_EMAIL")
        or candidate.get("email")
        or "candidate@example.com"
    )

    resume_file = resume_path or DEFAULT_RESUME_PDF

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = f"{sender_name} <{sender_email}>"
    msg["To"] = to_email
    msg.set_content(body)

    # Attach PDF resume if file exists
    has_attachment = False
    if resume_file and os.path.exists(resume_file):
        with open(resume_file, "rb") as f:
            pdf_data = f.read()
        msg.add_attachment(
            pdf_data,
            maintype="application",
            subtype="pdf",
            filename=os.path.basename(resume_file),
        )
        has_attachment = True
    else:
        print(f"[Email Dispatcher] Notice: Resume PDF not found at {resume_file} (sending without attachment)")

    # Check for SMTP credentials
    smtp_host = smtp_host or os.environ.get("SMTP_HOST", "")
    smtp_user = smtp_user or os.environ.get("SMTP_USER", "")
    smtp_pass = smtp_pass or os.environ.get("SMTP_PASSWORD") or os.environ.get("SMTP_PASS", "")
    if not smtp_port:
        smtp_port = int(os.environ.get("SMTP_PORT", 587))

    # Determine artifact directory
    target_draft_dir = draft_dir or os.path.join(PROJECT_ROOT, "execution", "artifacts")
    os.makedirs(target_draft_dir, exist_ok=True)

    safe_recipient = to_email.replace("@", "_at_").replace(".", "_")
    eml_filename = f"application_{job_id}_{safe_recipient}.eml"
    eml_path = os.path.join(target_draft_dir, eml_filename)

    with open(eml_path, "wb") as f:
        f.write(msg.as_bytes())
    print(f"[Email Dispatcher] Saved email message artifact: {eml_path}")

    is_sent = False
    if smtp_host and smtp_user and smtp_pass:
        try:
            print(f"[Email Dispatcher] Connecting to SMTP server {smtp_host}:{smtp_port}...")
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.starttls()
                server.login(smtp_user, smtp_pass)
                server.send_message(msg)
            is_sent = True
            print(f"[Email Dispatcher] Email successfully sent to {to_email}!")
        except Exception as exc:
            print(f"[Email Dispatcher] SMTP dispatch failed: {exc}. Retaining .eml artifact.")
    else:
        print("[Email Dispatcher] No live SMTP credentials configured; email artifact is generated & ready for dispatch.")

    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    resume_note = os.path.basename(resume_file) if has_attachment else "None"
    notes = (
        f"Applied via Email (Route A) to {to_email} on {now_iso}. "
        f"Subject: '{subject}'. Attached: {resume_note}. "
        f"Connect points spent on OnlineJobs.ph: 0 (points conserved). "
        f"Artifact: {eml_filename}."
    )

    update_job_status_and_notes(job_id, status="Applied", notes=notes, db_path=db_path)

    return {
        "status": "sent" if is_sent else "drafted_ready",
        "job_id": job_id,
        "recipient": to_email,
        "sender": f"{sender_name} <{sender_email}>",
        "route": "Route A (Direct Email Outreach)",
        "connect_points_spent": 0,
        "has_attachment": has_attachment,
        "eml_artifact": eml_path,
        "notes": notes,
    }


def main():
    parser = argparse.ArgumentParser(description="Dispatch job application via email (Route A)")
    parser.add_argument("--job-id", required=True, help="Job ID")
    parser.add_argument("--to", required=True, help="Recipient email address")
    parser.add_argument("--subject", required=True, help="Email subject line")
    parser.add_argument("--body", help="Email body text")
    parser.add_argument("--body-file", help="Path to text file containing email body")
    parser.add_argument("--resume-path", help="Path to resume PDF")
    parser.add_argument("--draft-dir", help="Directory to save .eml artifact")
    args = parser.parse_args()

    content = args.body
    if not content and args.body_file and os.path.exists(args.body_file):
        with open(args.body_file, "r", encoding="utf-8") as f:
            content = f.read()

    if not content:
        print("Error: Either --body or --body-file must be provided.", file=sys.stderr)
        sys.exit(1)

    result = dispatch_email_application(
        job_id=args.job_id,
        to_email=args.to,
        subject=args.subject,
        body=content,
        resume_path=args.resume_path,
        draft_dir=args.draft_dir,
    )
    print("\nResult:", json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

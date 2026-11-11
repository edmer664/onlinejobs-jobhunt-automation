"""
Reference Playwright Recipe: ClickUp Forms Automation (Route C).
Automates filling ClickUp Forms with candidate details and file attachments.
"""

import argparse
import os
import sys
from playwright.sync_api import sync_playwright

# Add src to sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
for p in (PROJECT_ROOT, SRC_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.config_loader import get_candidate_profile


def fill_quill_editor(page, editor, text: str):
    """Types text cleanly into rich-text Quill editors used by ClickUp."""
    editor.click()
    page.wait_for_timeout(200)
    page.keyboard.insert_text(text)
    page.wait_for_timeout(200)


def apply_clickup_form(form_url: str, resume_path: str = "", submit: bool = False, headless: bool = True):
    profile = get_candidate_profile()
    candidate = profile.get("candidate", {})

    full_name = candidate.get("display_name") or candidate.get("name") or "Candidate Name"
    email = candidate.get("email", "candidate@example.com")
    phone = candidate.get("phone", "+1-555-0199")
    linkedin = candidate.get("linkedin", "https://linkedin.com")
    portfolio = candidate.get("portfolio_url", "https://example.com")

    resume_file = resume_path or os.environ.get("RESUME_PDF_PATH") or os.path.join(PROJECT_ROOT, "config", "resume.pdf")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page(viewport={"width": 1280, "height": 1400})

        print(f"[ClickUpForm] Navigating to: {form_url}...")
        page.goto(form_url, wait_until="networkidle")
        page.wait_for_timeout(3000)

        # Name
        name_inp = page.locator("input[placeholder*='name'], input[aria-label*='Name']")
        if name_inp.count() > 0:
            name_inp.first.fill(full_name)

        # Email
        email_inp = page.locator("input[type='email']")
        if email_inp.count() > 0:
            email_inp.first.fill(email)

        # Phone
        phone_inp = page.locator("input[type='tel']")
        if phone_inp.count() > 0:
            phone_inp.first.fill(phone)

        # Resume upload if file input exists and file is present
        file_inp = page.locator("input[type='file']")
        if file_inp.count() > 0 and os.path.exists(resume_file):
            print(f"[ClickUpForm] Uploading resume from {resume_file}...")
            file_inp.first.set_input_files(resume_file)
            page.wait_for_timeout(2000)

        # Rich text / Quill editors
        editors = page.locator(".ql-editor").all()
        if editors:
            fill_quill_editor(
                page,
                editors[0],
                f"I am applying with full availability and strong alignment with your team requirements. "
                f"Portfolio: {portfolio} | LinkedIn: {linkedin}",
            )

        # Submit button
        submit_btn = page.locator("button[type='submit'], .cu-form__submit-btn")
        if submit_btn.count() > 0:
            if submit:
                print("[ClickUpForm] Submitting application...")
                submit_btn.first.click()
                page.wait_for_timeout(3000)
                print("[ClickUpForm] Form submitted successfully!")
            else:
                print("[ClickUpForm] Dry-run complete. Form populated without final submission.")

        browser.close()


def main():
    parser = argparse.ArgumentParser(description="Submit ClickUp Form application")
    parser.add_argument("--url", required=True, help="ClickUp Form URL")
    parser.add_argument("--resume", help="Path to resume PDF")
    parser.add_argument("--submit", action="store_true", help="Submit the form (default is dry-run)")
    parser.add_argument("--headed", action="store_true", help="Run in visible browser mode")
    args = parser.parse_args()

    apply_clickup_form(args.url, resume_path=args.resume, submit=args.submit, headless=not args.headed)


if __name__ == "__main__":
    main()

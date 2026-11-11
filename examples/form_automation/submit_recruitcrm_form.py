"""
Reference Playwright Recipe: RecruitCRM ATS Forms Automation (Route C).
Automates submitting job applications through RecruitCRM ATS portals.
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


def apply_recruitcrm(form_url: str, resume_path: str = "", submit: bool = False, headless: bool = True):
    profile = get_candidate_profile()
    candidate = profile.get("candidate", {})

    full_name = candidate.get("display_name") or candidate.get("name") or "Candidate Name"
    name_parts = full_name.split()
    first_name = name_parts[0] if name_parts else "Candidate"
    last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else "Applicant"

    email = candidate.get("email", "candidate@example.com")
    phone = candidate.get("phone", "+1-555-0199")
    linkedin = candidate.get("linkedin", "https://linkedin.com")

    resume_file = resume_path or os.environ.get("RESUME_PDF_PATH") or os.path.join(PROJECT_ROOT, "config", "resume.pdf")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page(viewport={"width": 1280, "height": 1200})

        print(f"[RecruitCRM] Navigating to: {form_url}...")
        page.goto(form_url, wait_until="networkidle")
        page.wait_for_timeout(2500)

        # Name fields
        first_inp = page.locator("input[name='firstname'], input[placeholder*='First']")
        if first_inp.count() > 0:
            first_inp.first.fill(first_name)

        last_inp = page.locator("input[name='lastname'], input[placeholder*='Last']")
        if last_inp.count() > 0:
            last_inp.first.fill(last_name)

        # Email & Contact
        email_inp = page.locator("input[name='emailid'], input[type='email']")
        if email_inp.count() > 0:
            email_inp.first.fill(email)

        phone_inp = page.locator("input[name='contactnumber'], input[type='tel']")
        if phone_inp.count() > 0:
            phone_inp.first.fill(phone)

        # Resume attachment
        file_inp = page.locator("input[type='file']")
        if file_inp.count() > 0 and os.path.exists(resume_file):
            print(f"[RecruitCRM] Attaching resume: {resume_file}...")
            file_inp.first.set_input_files(resume_file)
            page.wait_for_timeout(2000)

        # LinkedIn
        li_inp = page.locator("input[name*='linkedin'], input[placeholder*='linkedin']")
        if li_inp.count() > 0:
            li_inp.first.fill(linkedin)

        # Submit button
        submit_btn = page.locator("button[type='submit'], .submit-btn")
        if submit_btn.count() > 0:
            if submit:
                print("[RecruitCRM] Submitting application...")
                submit_btn.first.click()
                page.wait_for_timeout(3000)
                print("[RecruitCRM] Submitted successfully!")
            else:
                print("[RecruitCRM] Dry-run complete. Form fields populated without submission.")

        browser.close()


def main():
    parser = argparse.ArgumentParser(description="Submit RecruitCRM application")
    parser.add_argument("--url", required=True, help="RecruitCRM Application URL")
    parser.add_argument("--resume", help="Path to resume PDF")
    parser.add_argument("--submit", action="store_true", help="Submit the form (default is dry-run)")
    parser.add_argument("--headed", action="store_true", help="Run in visible browser mode")
    args = parser.parse_args()

    apply_recruitcrm(args.url, resume_path=args.resume, submit=args.submit, headless=not args.headed)


if __name__ == "__main__":
    main()

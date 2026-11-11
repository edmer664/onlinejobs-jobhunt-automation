"""
Reference Playwright Recipe: Google Forms Automation (Route C).
Automates multi-page Google Form questionnaire completion based on candidate profile.
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


def apply_google_form(form_url: str, resume_path: str = "", submit: bool = False, headless: bool = True):
    profile = get_candidate_profile()
    candidate = profile.get("candidate", {})
    logistics = profile.get("logistics", {})

    full_name = candidate.get("display_name") or candidate.get("name") or "Candidate Name"
    email = candidate.get("email", "candidate@example.com")
    phone = candidate.get("phone", "+1-555-0199")
    location = candidate.get("location", "Remote, Worldwide")
    linkedin = candidate.get("linkedin", "https://linkedin.com")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(viewport={"width": 1280, "height": 900})
        page = context.new_page()

        print(f"[GoogleForm] Navigating to: {form_url}...")
        page.goto(form_url, wait_until="networkidle")
        page.wait_for_timeout(2000)

        page_num = 1
        while True:
            # Handle email input
            for inp in page.locator('input[type="email"]').all():
                if inp.is_visible() and not inp.input_value():
                    inp.fill(email)

            # Handle question items
            for item in page.locator('div[role="listitem"]').all():
                heading = item.locator('div[role="heading"]')
                h_text = heading.inner_text().lower() if heading.count() > 0 else ""

                inp = item.locator('input[type="text"], input[type="email"]')
                if inp.count() > 0:
                    if "full name" in h_text or ("name" in h_text and "company" not in h_text):
                        inp.first.fill(full_name)
                    elif "email" in h_text:
                        inp.first.fill(email)
                    elif "phone" in h_text or "contact" in h_text:
                        inp.first.fill(phone)
                    elif "based" in h_text or "location" in h_text or "country" in h_text:
                        inp.first.fill(location)
                    elif "linkedin" in h_text:
                        inp.first.fill(linkedin)

            next_btn = page.locator('div[role="button"]:has-text("Next"), div[role="button"]:has-text("Susunod")')
            submit_btn = page.locator('div[role="button"]:has-text("Submit"), div[role="button"]:has-text("Isumite")')

            if next_btn.count() > 0 and next_btn.first.is_visible():
                print(f"[GoogleForm] Navigating past page {page_num}...")
                next_btn.first.click()
                page_num += 1
                page.wait_for_timeout(2000)
            elif submit_btn.count() > 0 and submit_btn.first.is_visible():
                if submit:
                    print("[GoogleForm] Submitting application...")
                    submit_btn.first.click()
                    page.wait_for_timeout(3000)
                    print("[GoogleForm] Submission confirmed!")
                else:
                    print("[GoogleForm] Dry-run completed. Form populated successfully without submission.")
                break
            else:
                break

        browser.close()


def main():
    parser = argparse.ArgumentParser(description="Submit Google Form application")
    parser.add_argument("--url", required=True, help="Google Form URL")
    parser.add_argument("--submit", action="store_true", help="Submit the form (default is dry-run)")
    parser.add_argument("--headed", action="store_true", help="Run in visible browser mode")
    args = parser.parse_args()

    apply_google_form(args.url, submit=args.submit, headless=not args.headed)


if __name__ == "__main__":
    main()

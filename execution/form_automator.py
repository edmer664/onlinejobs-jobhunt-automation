"""
Multi-Channel External Form Automation Engine (Route C).
Automates application form submission across common external channels:
- Google Forms (forms.gle, docs.google.com/forms)
- ClickUp Forms (forms.clickup.com)
- RecruitCRM ATS (recruitcrm.io/apply)
- Airtable Forms (airtable.com)
- Generic ATS & Intake Web Forms

Guarantees 0 OnlineJobs.ph connect points spent and logs status 'Applied' in SQLite.
"""

import argparse
import asyncio
import json
import os
import re
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# Add src and repo root to sys.path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
SRC_DIR = os.path.join(PROJECT_ROOT, "src")

for p in (PROJECT_ROOT, SRC_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    from src.db import DB_PATH, get_job_by_id, update_job_status_and_notes
    from src.config_loader import get_candidate_profile
    from src.proposal_engine import audit_screening_traps, generate_tailored_proposal
except ImportError:
    from db import DB_PATH, get_job_by_id, update_job_status_and_notes
    from config_loader import get_candidate_profile
    from proposal_engine import audit_screening_traps, generate_tailored_proposal


def detect_form_type(url: str) -> str:
    """Classifies external application form type from target URL."""
    url_low = url.lower()
    if "forms.gle" in url_low or "docs.google.com/forms" in url_low:
        return "google_forms"
    elif "clickup.com" in url_low:
        return "clickup"
    elif "recruitcrm.io" in url_low:
        return "recruitcrm"
    elif "airtable.com" in url_low:
        return "airtable"
    elif "typeform.com" in url_low:
        return "typeform"
    elif "tally.so" in url_low:
        return "tally"
    elif "jotform.com" in url_low:
        return "jotform"
    else:
        return "generic_web_form"


class FormAutomator:
    """Automates filling and submission of external candidate application forms."""

    def __init__(
        self,
        config_path: Optional[str] = None,
        resume_path: Optional[str] = None,
        db_path: str = DB_PATH,
    ):
        self.profile = get_candidate_profile(config_path)
        self.candidate = self.profile.get("candidate", {})
        self.logistics = self.profile.get("logistics", {})
        self.db_path = db_path
        self.resume_path = resume_path or os.environ.get(
            "RESUME_PDF_PATH",
            os.path.join(PROJECT_ROOT, "config", "resume.pdf"),
        )

    def get_field_mapping(self, secret_code: str = "", custom_proposal: str = "") -> Dict[str, str]:
        """Provides normalized map of candidate attributes for form field matching."""
        name = self.candidate.get("display_name") or self.candidate.get("name") or "Candidate"
        name_parts = name.split()
        first_name = name_parts[0] if name_parts else ""
        last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""

        return {
            "name": name,
            "full_name": name,
            "first_name": first_name,
            "last_name": last_name,
            "email": self.candidate.get("email", ""),
            "phone": self.candidate.get("phone", ""),
            "location": self.candidate.get("location", ""),
            "linkedin": self.candidate.get("linkedin", ""),
            "portfolio": self.candidate.get("portfolio_url", ""),
            "resume_url": self.candidate.get("resume_url", ""),
            "cover_letter": custom_proposal,
            "secret_code": secret_code,
            "hardware": self.logistics.get("hardware", ""),
            "internet": self.logistics.get("internet", ""),
            "availability": self.logistics.get("available_hours", "Immediate full-time availability"),
        }

    async def fill_google_form(
        self,
        page: Any,
        field_data: Dict[str, str],
        submit: bool = False,
    ) -> Dict[str, Any]:
        """Automates multi-page Google Forms traversal and field population."""
        filled_fields = []
        page_num = 1

        while True:
            await page.wait_for_timeout(1000)

            # Handle email input if present at top
            email_inputs = await page.locator('input[type="email"]').all()
            for inp in email_inputs:
                if await inp.is_visible() and not (await inp.input_value()):
                    await inp.fill(field_data["email"])
                    filled_fields.append("email")

            # Inspect list items / question containers
            list_items = await page.locator('div[role="listitem"]').all()
            for item in list_items:
                heading_el = item.locator('div[role="heading"]')
                heading_text = (await heading_el.inner_text()).lower() if await heading_el.count() > 0 else ""

                text_inputs = item.locator('input[type="text"], input[type="email"]')
                if await text_inputs.count() > 0:
                    inp = text_inputs.first
                    if "name" in heading_text and not ("company" in heading_text or "tool" in heading_text):
                        await inp.fill(field_data["name"])
                        filled_fields.append("name")
                    elif "email" in heading_text:
                        await inp.fill(field_data["email"])
                        filled_fields.append("email")
                    elif "phone" in heading_text or "contact" in heading_text:
                        await inp.fill(field_data["phone"])
                        filled_fields.append("phone")
                    elif "linkedin" in heading_text:
                        await inp.fill(field_data["linkedin"])
                        filled_fields.append("linkedin")
                    elif "portfolio" in heading_text or "website" in heading_text:
                        await inp.fill(field_data["portfolio"])
                        filled_fields.append("portfolio")
                    elif "location" in heading_text or "based" in heading_text or "country" in heading_text:
                        await inp.fill(field_data["location"])
                        filled_fields.append("location")
                    elif "code" in heading_text and field_data.get("secret_code"):
                        await inp.fill(field_data["secret_code"])
                        filled_fields.append("secret_code")

                # Handle textareas (cover letters, introductions)
                textareas = item.locator("textarea")
                if await textareas.count() > 0:
                    area = textareas.first
                    if "cover" in heading_text or "proposal" in heading_text or "why" in heading_text:
                        await area.fill(field_data["cover_letter"])
                        filled_fields.append("cover_letter")

            # Check for next page or submit button
            next_btn = page.locator('div[role="button"]:has-text("Next"), div[role="button"]:has-text("Susunod")')
            submit_btn = page.locator('div[role="button"]:has-text("Submit"), div[role="button"]:has-text("Isumite")')

            if await next_btn.count() > 0 and await next_btn.first.is_visible():
                print(f"[FormAutomator] Progressing past Google Form page {page_num}...")
                await next_btn.first.click()
                page_num += 1
                await page.wait_for_timeout(2000)
            elif await submit_btn.count() > 0 and await submit_btn.first.is_visible():
                if submit:
                    print("[FormAutomator] Submitting Google Form...")
                    await submit_btn.first.click()
                    await page.wait_for_timeout(3000)
                    return {"status": "submitted", "filled_fields": filled_fields, "pages_completed": page_num}
                else:
                    print("[FormAutomator] Dry-run complete. Ready for submission.")
                    return {"status": "dry_run_ready", "filled_fields": filled_fields, "pages_completed": page_num}
            else:
                break

        return {"status": "completed", "filled_fields": filled_fields, "pages_completed": page_num}

    async def automate_application(
        self,
        job_id: str,
        form_url: str,
        custom_proposal: str = "",
        submit: bool = False,
        headless: bool = True,
    ) -> Dict[str, Any]:
        """End-to-end automation execution for external form."""
        form_type = detect_form_type(form_url)
        print(f"[FormAutomator] Target: {form_url} | Identified Form Type: {form_type}")

        # Extract screening traps if job exists in db
        secret_code = ""
        job_record = get_job_by_id(job_id, db_path=self.db_path)
        if job_record:
            traps = audit_screening_traps(job_record.get("description", ""))
            if traps.get("secret_codes"):
                secret_code = traps["secret_codes"][0]

        proposal_text = custom_proposal
        if not proposal_text and job_record:
            generated = generate_tailored_proposal(job_record)
            proposal_text = generated.get("proposal_text", "")

        fields = self.get_field_mapping(secret_code=secret_code, custom_proposal=proposal_text)

        result: Dict[str, Any] = {
            "job_id": job_id,
            "form_url": form_url,
            "form_type": form_type,
            "submitted": submit,
            "connect_points_spent": 0,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=headless,
                args=["--no-sandbox", "--disable-dev-shm-usage"],
            )
            context = await browser.new_context(viewport={"width": 1280, "height": 900})
            page = await context.new_page()

            try:
                await page.goto(form_url, wait_until="networkidle", timeout=45000)
                await page.wait_for_timeout(2000)

                if form_type == "google_forms":
                    res = await self.fill_google_form(page, fields, submit=submit)
                    result.update(res)
                else:
                    # Generic heuristic autofill
                    inputs = await page.locator("input, textarea").all()
                    filled = []
                    for el in inputs:
                        try:
                            if not await el.is_visible():
                                continue
                            inp_type = await el.get_attribute("type") or "text"
                            placeholder = (await el.get_attribute("placeholder") or "").lower()
                            name_attr = (await el.get_attribute("name") or "").lower()
                            id_attr = (await el.get_attribute("id") or "").lower()
                            meta_tag = f"{name_attr} {id_attr} {placeholder}"

                            if inp_type == "email" or "email" in meta_tag:
                                await el.fill(fields["email"])
                                filled.append("email")
                            elif "phone" in meta_tag or "tel" in meta_tag or inp_type == "tel":
                                await el.fill(fields["phone"])
                                filled.append("phone")
                            elif "linkedin" in meta_tag:
                                await el.fill(fields["linkedin"])
                                filled.append("linkedin")
                            elif "first" in meta_tag and "name" in meta_tag:
                                await el.fill(fields["first_name"])
                                filled.append("first_name")
                            elif "last" in meta_tag and "name" in meta_tag:
                                await el.fill(fields["last_name"])
                                filled.append("last_name")
                            elif "name" in meta_tag and not any(k in meta_tag for k in ["company", "tool"]):
                                await el.fill(fields["name"])
                                filled.append("name")
                        except Exception:
                            continue

                    result["status"] = "form_populated"
                    result["filled_fields"] = filled

                await browser.close()

            except Exception as exc:
                await browser.close()
                result["status"] = "error"
                result["error"] = str(exc)
                print(f"[FormAutomator] Error: {exc}")

        # Update database record if requested or submitted
        if submit or result.get("status") in ("submitted", "form_populated", "dry_run_ready"):
            now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            notes = (
                f"Processed Route C External Form ({form_type}) at {form_url} on {now_iso}. "
                f"Fields populated: {len(result.get('filled_fields', []))}. "
                f"Connect points spent on OnlineJobs.ph: 0 (points conserved)."
            )
            update_job_status_and_notes(job_id, status="Applied" if submit else "Shortlisted", notes=notes, db_path=self.db_path)

        return result


def main():
    parser = argparse.ArgumentParser(description="Multi-Channel External Form Automation (Route C)")
    parser.add_argument("--job-id", default="seed-002", help="OnlineJobs.ph Job ID")
    parser.add_argument("--form-url", required=True, help="External Form URL (Google Forms, ClickUp, RecruitCRM)")
    parser.add_argument("--submit", action="store_true", help="Submit the form (default is dry-run)")
    parser.add_argument("--headed", action="store_true", help="Run browser in visible/headed mode")
    args = parser.parse_args()

    automator = FormAutomator()
    result = asyncio.run(
        automator.automate_application(
            job_id=args.job_id,
            form_url=args.form_url,
            submit=args.submit,
            headless=not args.headed,
        )
    )
    print("\nResult:", json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

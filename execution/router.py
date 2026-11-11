"""
OnlineJobs.ph Application Router & Connect Points Decision Engine.
Evaluates a job posting, detects application channels, and calculates connect points:
- High Match (>=80%) -> 20 connects
- Moderate Match (60-79%) -> 10 to 8 connects
- Low Match (<60%) -> 0 connects (Skip application)

Decides Route:
- If external form specified -> Route EXTERNAL_FORM (0 OLJ connects spent)
- If direct email specified -> Route EMAIL (0 OLJ connects spent)
- If on-platform -> Route PLATFORM (spend 20 or 10-8 connects)
- STRICT RULE: Apply via one route, NEVER both.
"""

import argparse
import json
import os
import re
import sys
from typing import Any, Dict, List, Optional

# Add src and repo root to sys.path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
SRC_DIR = os.path.join(PROJECT_ROOT, "src")

for p in (PROJECT_ROOT, SRC_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    from src.evaluator import evaluate_job
    from src.db import DB_PATH, get_job_by_id
except ImportError:
    from evaluator import evaluate_job
    from db import DB_PATH, get_job_by_id


def extract_emails(text: str) -> List[str]:
    """Extract valid email addresses while ignoring image/file extensions and common test domains."""
    raw_emails = re.findall(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', text)
    valid_emails = []
    ignored_domains = {"example.com", "onlinejobs.ph", "domain.com", "test.com"}
    for email in raw_emails:
        email = email.rstrip(".,;)>]")
        domain = email.split("@")[-1].lower()
        if domain not in ignored_domains and not email.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp")):
            valid_emails.append(email)
    return list(dict.fromkeys(valid_emails))


def extract_external_forms(text: str) -> List[str]:
    """Extract Google Forms, Typeform, Airtable, ClickUp, RecruitCRM, Workable, Tally, Jotform, or ATS links."""
    patterns = [
        # Google Forms
        r'https?://forms\.gle/[a-zA-Z0-9_\-\?&=]+',
        r'https?://docs\.google\.com/forms/[^\s"\'<>]+',
        # Typeform
        r'https?://[a-zA-Z0-9_-]+\.typeform\.com/[^\s"\'<>]+',
        # Airtable
        r'https?://airtable\.com/[^\s"\'<>]+',
        # ClickUp Forms
        r'https?://forms\.clickup\.com/[^\s"\'<>]+',
        r'https?://(?:[a-zA-Z0-9_-]+\.)?clickup\.com/f/[^\s"\'<>]+',
        # Recruit CRM ATS
        r'https?://recruitcrm\.io/apply/[^\s"\'<>]+',
        r'https?://[a-zA-Z0-9_-]+\.recruitcrm\.io/[^\s"\'<>]+',
        # Workable ATS
        r'https?://apply\.workable\.com/[^\s"\'<>]+',
        r'https?://[a-zA-Z0-9_-]+\.workable\.com/j/[^\s"\'<>]+',
        # Tally Forms
        r'https?://tally\.so/r/[^\s"\'<>]+',
        r'https?://tally\.so/[a-zA-Z0-9_-]+',
        # JotForm
        r'https?://(?:form\.)?jotform\.com/[^\s"\'<>]+',
        r'https?://[a-zA-Z0-9_-]+\.jotform\.com/[^\s"\'<>]+',
        # Monday.com WorkForms
        r'https?://wkf\.ms/[a-zA-Z0-9_-]+',
        # Greenhouse & Lever ATS
        r'https?://boards\.greenhouse\.io/[^\s"\'<>]+',
        r'https?://jobs\.lever\.co/[^\s"\'<>]+',
    ]
    forms = []
    for pat in patterns:
        for f in re.findall(pat, text):
            f_clean = f.rstrip(".,;:)>]")
            forms.append(f_clean)
    return list(dict.fromkeys(forms))


def detect_masked_emails(text: str) -> bool:
    """Detect if employer provided an email that was masked/redacted by OnlineJobs.ph."""
    masked_patterns = [
        r'(?:email|send|forward|submit)\s*(?:your\s+application|your\s+resume|your\s+cv|to|at)?\s*[:\s]*[-*•_]{3,}',
        r'email\s*:\s*[-*•_]{3,}',
        r'<ojfilter[^>]*>\s*[-*•_]{3,}\s*</ojfilter>',
        r'\[email\s+protected\]',
        r'\bemail\b.*[-*•_]{5,}',
    ]
    return any(re.search(pat, text, re.IGNORECASE) for pat in masked_patterns)


def extract_screening_traps(text: str) -> Dict[str, Any]:
    """Detect secret words, code phrases, and mandatory questions."""
    traps = {
        "secret_codes": [],
        "mandatory_questions": [],
        "required_links": [],
    }

    # Secret code patterns
    code_patterns = [
        r'(?:subject|headline|title)\s*(?:line)?\s*(?:must|should|please)?\s*(?:include|contain|start with|have)\s*[:"\'“]([^"\'”\n\r]{2,40})["\'”]',
        r'(?:start|begin)\s*(?:your)?\s*(?:proposal|application|cover letter|message)\s*(?:with|by writing)\s*[:"\'“]([^"\'”\n\r]{2,40})["\'”]',
        r'(?:write|put|type)\s*["\'“]([^"\'”\n\r]{2,40})["\'”]\s*(?:in|at)\s*(?:the\s*)?(?:subject|first line|beginning|top)',
        r'(?:use|put|write|enter|include)\s*["\'“]([^"\'”\n\r]{2,40})["\'”]\s*as\s*(?:your)?\s*(?:email\s*)?(?:subject|headline|title)',
    ]
    for pat in code_patterns:
        matches = re.findall(pat, text, re.IGNORECASE)
        for m in matches:
            clean = m.strip().strip('"\'')
            if clean and clean not in traps["secret_codes"]:
                traps["secret_codes"].append(clean)

    # Specific mandatory requests
    if re.search(r'\btyping\s*speed\b|\bwpm\b', text, re.IGNORECASE):
        traps["mandatory_questions"].append("Typing speed (WPM) requested")
    if re.search(r'\bspeedtest\b|\binternet\s*speed\b', text, re.IGNORECASE):
        traps["required_links"].append("Speedtest screenshot/link requested")
    if re.search(r'\bportfolio\b|\bsamples\b', text, re.IGNORECASE):
        traps["required_links"].append("Portfolio / work samples requested")
    if re.search(r'\bloom\b|\bvideo\s*intro(?:duction)?\b', text, re.IGNORECASE):
        traps["required_links"].append("Loom / video introduction requested")

    return traps


def evaluate_job_route_and_points(job_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main evaluation and decision function.
    Returns:
    - match_score (0-100)
    - suitability_tier (Tier 1: High Fit, Tier 2: Good Fit, Tier 3: Low Fit)
    - route ("EMAIL", "PLATFORM", "EXTERNAL_FORM", "MASKED_EMAIL")
    - connect_points (20, 10, 8, or 0)
    - should_apply (bool)
    - target_email (str or None)
    - target_form_url (str or None)
    - screening_traps (dict)
    - routing_reason (str)
    """
    desc = job_data.get("description", "") or job_data.get("description_snippet", "")
    title = job_data.get("title", "")
    full_text = f"{title}\n{desc}"

    # Step 1: Match Score Evaluation
    if evaluate_job:
        eval_result = evaluate_job(job_data)
        match_score = eval_result.get("match_score", 0)
        suitability_tier = eval_result.get("suitability_tier", "Low Fit")
        role_category = eval_result.get("role_category", "Other")
        matched_skills = eval_result.get("matched_skills", [])
        missing_skills = eval_result.get("missing_skills", [])
    else:
        # Fallback simple scoring
        match_score = 70
        suitability_tier = "Good Fit"
        role_category = "Virtual Assistant"
        matched_skills = []
        missing_skills = []

    # Step 2: Route Selection Matrix (Strictly Mutually Exclusive)
    emails = extract_emails(full_text)
    external_forms = extract_external_forms(full_text)
    screening_traps = extract_screening_traps(full_text)
    has_masked_email = detect_masked_emails(full_text) and not bool(emails)

    # Check explicit employer instructions
    has_email_instruction = bool(re.search(
        r'(?:send|email|submit|forward)\s*(?:your)?\s*(?:resume|cv|application|details)?\s*(?:to|at)\s*[:\s]*([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)',
        full_text,
        re.IGNORECASE,
    )) or bool(emails)

    target_email = emails[0] if emails else None
    target_form = external_forms[0] if external_forms else None

    if target_form and not has_email_instruction:
        route = "EXTERNAL_FORM"
        routing_reason = f"Employer provided dedicated external application form ({target_form}). Apply via form only; do not double-apply on OLJ."
    elif target_email and (has_email_instruction or "email" in full_text.lower()):
        route = "EMAIL"
        routing_reason = f"Employer specified direct application email ({target_email}). Apply via email with attached PDF resume; DO NOT spend connects on OLJ."
    elif has_masked_email:
        route = "PLATFORM"
        target_email = None
        routing_reason = "Employer requested direct email application, but email address is masked by OnlineJobs.ph ('Email: ----------'). Target email is None; routed to PLATFORM with 0 connects allocated."
    else:
        route = "PLATFORM"
        routing_reason = "Standard OnlineJobs.ph listing with no external email/form. Apply via on-platform application modal."

    # Step 3: Connect Points Judgement
    # High match = 20 connects; Else moderate = 10-8 connects; Low match = 0 / Skip
    if match_score < 60:
        should_apply = False
        connect_points = 0
        point_reasoning = f"Match score {match_score}% is below threshold (<60%). Application withheld to conserve points."
    else:
        if route in ("EMAIL", "EXTERNAL_FORM"):
            should_apply = True
            connect_points = 0
            point_reasoning = f"Route is {route}. Connect points spent on OnlineJobs.ph = 0 (points conserved)."
        elif route == "MASKED_EMAIL" or (route == "PLATFORM" and has_masked_email):
            should_apply = False
            connect_points = 0
            point_reasoning = "Masked email listing ('Email: ----------'). Connect points spent = 0. Automated application withheld until address is unmasked via authenticated login."
        else:  # PLATFORM
            should_apply = True
            if match_score >= 80:
                connect_points = 20
                point_reasoning = f"High Match ({match_score}% >= 80%, {suitability_tier}). Maximum priority bid: 20 connects allocated for top inbox visibility."
            elif match_score >= 70:
                connect_points = 10
                point_reasoning = f"Good Match ({match_score}%, 70-79%). Standard priority bid: 10 connects allocated."
            else:  # 60 to 69
                connect_points = 8
                point_reasoning = f"Transferable Match ({match_score}%, 60-69%). Moderate priority bid: 8 connects allocated."

    return {
        "job_id": job_data.get("job_id", ""),
        "title": title,
        "employer": job_data.get("employer", "Undisclosed"),
        "match_score": match_score,
        "suitability_tier": suitability_tier,
        "role_category": role_category,
        "route": route,
        "should_apply": should_apply,
        "connect_points": connect_points,
        "point_reasoning": point_reasoning,
        "routing_reason": routing_reason,
        "target_email": target_email,
        "target_form_url": target_form,
        "screening_traps": screening_traps,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
    }


def main():
    parser = argparse.ArgumentParser(description="Evaluate job application route and connect points")
    parser.add_argument("--job-id", help="Database Job ID to evaluate")
    parser.add_argument("--title", default="", help="Job title")
    parser.add_argument("--description", default="", help="Job description text")
    args = parser.parse_args()

    if args.job_id:
        job = get_job_by_id(args.job_id)
        if not job:
            print(f"Error: Job ID {args.job_id} not found in database", file=sys.stderr)
            sys.exit(1)
        job_data = job
    else:
        job_data = {
            "job_id": "cli_eval",
            "title": args.title,
            "description": args.description,
        }

    decision = evaluate_job_route_and_points(job_data)
    print(json.dumps(decision, indent=2))


if __name__ == "__main__":
    main()

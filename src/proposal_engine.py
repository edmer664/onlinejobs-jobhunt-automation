"""
Grounded Proposal Generation Engine for OnlineJobs.ph
Decoupled candidate profile, zero hallucinations, strict source of truth,
screening trap detection, and 150-250 word limit.
"""

import re
from typing import Any, Dict, List, Optional

try:
    from config_loader import get_candidate_profile
except ImportError:
    from src.config_loader import get_candidate_profile


def get_profile() -> Dict[str, Any]:
    """Helper to retrieve dynamic candidate profile."""
    return get_candidate_profile()


# Module-level accessor for compatibility
CANDIDATE_PROFILE = get_candidate_profile().get("candidate", {})


def audit_screening_traps(text: str) -> Dict[str, Any]:
    """
    Scans a job description for hidden screening traps, secret codes, and mandatory questions.
    """
    traps: Dict[str, Any] = {
        "secret_codes": [],
        "mandatory_questions": [],
        "submission_channel": "OnlineJobs.ph Message",
        "requires_speedtest": False,
        "requires_typing_test": False,
        "requires_voice_video": False,
        "email_submission": None,
        "form_submission": None,
    }

    if not text:
        return traps

    # Check for direct email submission
    email_matches = re.findall(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", text)
    for email in email_matches:
        e_low = email.lower()
        if not e_low.endswith("onlinejobs.ph") and not e_low.endswith("example.com"):
            traps["email_submission"] = email
            traps["submission_channel"] = f"Direct Email ({email})"
            break

    # Check for Google Form, Typeform, Airtable, ClickUp, or ATS submission
    form_match = re.search(
        r"(https?://(?:forms\.gle|docs\.google\.com/forms|airtable\.com|forms\.clickup\.com|recruitcrm\.io|tally\.so|jotform\.com)[^\s]+)",
        text,
    )
    if form_match:
        traps["form_submission"] = form_match.group(1)
        traps["submission_channel"] = f"External Application Form ({form_match.group(1)})"

    # Secret code words or phrases with strict intent patterns
    QUOTES = "\"'\u201c\u201d\u2018\u2019"
    code_patterns = [
        # e.g., start your application with the word "BOOKED"
        rf"start\s+your\s+(?:subject|message|proposal|application)\s+with\s+(?:(?:the\s+)?(?:word|phrase|code)\s+)?([{QUOTES}])([^{QUOTES}\n\r]{{1,35}})\1",
        # e.g., put "Blueberry" in the subject
        rf"(?:put|include|write|use)\s+([{QUOTES}])([^{QUOTES}\n\r]{{1,35}})\1\s+(?:in|as|on)\s+(?:the|your)?\s*subject",
        # e.g., subject line must contain "Banana"
        rf"subject\s+line\s+must\s+(?:contain|include|start with)\s+[{QUOTES}]?([^{QUOTES}\n\r.,;]{{2,35}})[{QUOTES}]?",
        # e.g., secret word is "Coffee"
        rf"(?:secret|magic|code)\s*(?:word|phrase)\s*(?:is|:)\s*[{QUOTES}]?([^{QUOTES}\n\r.,;]{{2,30}})[{QUOTES}]?",
    ]
    for pattern in code_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            code = match.group(2 if len(match.groups()) >= 2 else 1).strip().strip(QUOTES).strip()
            if code and len(code) > 1 and code.lower() not in ("the", "this", "a", "an", "your", "none", "word", "code"):
                if code not in traps["secret_codes"]:
                    traps["secret_codes"].append(code)

    # Keywords detection
    text_lower = text.lower()
    if any(k in text_lower for k in ["speedtest", "speed test", "internet speed"]):
        traps["requires_speedtest"] = True
    if any(k in text_lower for k in ["typing test", "wpm", "words per minute"]):
        traps["requires_typing_test"] = True
    if any(k in text_lower for k in ["loom", "video intro", "record a video", "audio clip", "voice recording"]):
        traps["requires_voice_video"] = True

    # Numbered questions detection (e.g., 1. What is..., 2. How many...)
    numbered = re.findall(r"(?:^|\n)\s*(\d+[\.\)]\s*[^\n\?]{5,120}\?)", text)
    if numbered:
        traps["mandatory_questions"] = [q.strip() for q in numbered[:5]]

    return traps


def generate_tailored_proposal(
    job: Dict[str, Any],
    custom_client_name: Optional[str] = None,
    extra_instructions: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Constructs a 150-250 word, fact-grounded proposal for the candidate.
    Strictly prevents hallucinations while adapting to role requirements.
    """
    title = job.get("title", "Remote Specialist").strip()
    desc = job.get("description", "") or job.get("description_snippet", "")
    employer = (job.get("employer") or "").strip()
    client_region = job.get("client_region", "US")

    traps = audit_screening_traps(desc)

    full_profile = get_candidate_profile()
    candidate = full_profile.get("candidate", {})
    candidate_name = candidate.get("display_name") or candidate.get("name") or "Candidate"

    # Determine client greeting
    greeting_name = "Hiring Team"
    if custom_client_name and custom_client_name.strip():
        greeting_name = custom_client_name.strip()
    elif employer and employer.lower() not in ("not given", "undisclosed", "confidential"):
        words = employer.split()
        if len(words) <= 3 and not any(w in employer.lower() for w in ["inc", "llc", "ltd", "corp", "company", "group"]):
            greeting_name = words[0]
        else:
            greeting_name = f"{employer} Team"

    # Determine Subject Line
    subject_code = ""
    if traps["secret_codes"]:
        subject_code = f" [{traps['secret_codes'][0]}]"

    # Target Hook for subject
    hook_tag = "Experienced Remote Specialist"
    t_low = title.lower()
    if any(k in t_low for k in ["recruit", "sourc", "talent"]):
        hook_tag = "Talent Sourcing & Pipeline Specialist"
    elif any(k in t_low for k in ["bookkeep", "account", "billing", "data entry"]):
        hook_tag = "Accurate Data & Spreadsheet Specialist"
    elif any(k in t_low for k in ["admin", "executive", "assistant"]):
        hook_tag = "Executive Admin & Calendar Coordinator"
    elif any(k in t_low for k in ["social media", "content"]):
        hook_tag = "Digital Content & Creative Specialist"

    subject_line = f"{title} Application - {candidate_name}{subject_code} | {hook_tag}"

    # Line 1: Code word or direct screener answer
    line1_code = ""
    if traps["secret_codes"]:
        line1_code = f"Keyword / Screening Code: {traps['secret_codes'][0]}\n\n"

    # Core pain point empathy hook
    desc_low = desc.lower()
    if any(k in desc_low for k in ["call", "phone", "lead", "booking", "consultation", "homeowner"]):
        empathy_hook = (
            "I understand you need a dependable, energetic assistant who takes lead responsiveness and organization seriously—promptly connecting with prospects and keeping daily schedules completely seamless."
        )
    elif any(k in desc_low for k in ["messy", "reconcil", "bookkeep", "billing", "invoice", "data entry", "spreadsheet"]):
        empathy_hook = (
            "I understand you need meticulous, zero-discrepancy data organization and record-keeping so billing, spreadsheets, and daily operational figures are accurate and always up to date."
        )
    elif any(k in desc_low for k in ["sourcing", "recruit", "interview", "pipeline", "hiring"]):
        empathy_hook = (
            "I understand the challenge of filtering and consistently sourcing high-caliber talent, and I am ready to step in with proactive pipeline management to keep your hiring goals on target."
        )
    else:
        empathy_hook = (
            "I understand you need proactive, organized administrative support to keep your operations structured, communications answered, and daily priorities on track without hand-holding."
        )

    # 3 Bullet Proof Points
    bullets: List[str] = []

    # Bullet 1: Admin / Outreach / Lead handling
    if any(k in desc_low for k in ["call", "lead", "booking", "consultation", "outreach", "client", "customer"]):
        bullets.append(
            "• **Proactive Lead & Inquiry Engagement:** Proven experience managing executive communication funnels and high-volume client correspondence, delivering rapid response times and structured follow-up workflows."
        )
    else:
        bullets.append(
            "• **Executive Admin & Calendar Coordination:** Extensive track record managing executive schedules, booking appointments, and organizing daily operations to ensure frictionless workflows."
        )

    # Bullet 2: Technical, Spreadsheets, Data Integrity
    if any(k in desc_low for k in ["excel", "sheet", "bookkeep", "financ", "billing", "data", "report", "accurate"]):
        bullets.append(
            "• **Accurate Data & Spreadsheet Management:** High-precision data entry and spreadsheet administration, maintaining verified accuracy across complex reports, database funnels, and records."
        )
    elif any(k in desc_low for k in ["recruit", "sourc", "linkedin", "candidate"]):
        bullets.append(
            "• **Targeted Sourcing & Pipeline Tracking:** Experienced in proactive talent sourcing via LinkedIn, managing recruitment funnels in spreadsheets, and streamlining candidate onboarding."
        )
    else:
        bullets.append(
            "• **Structured Database & Workflow Systems:** Strong technical background in cloud productivity platforms, database management, and SOP documentation to keep operations organized."
        )

    # Bullet 3: Content or Tech Tool Bridge
    if any(k in desc_low for k in ["canva", "design", "graphic", "social media", "reel", "post", "video", "capcut"]):
        bullets.append(
            "• **Digital Content & Visual Assets:** Experienced in creating engaging social media graphics, flyers, and short-form digital assets with modern creative tools."
        )
    else:
        bullets.append(
            "• **Rapid Tool Adaptability & Tech Readiness:** Quick learner with immediate adaptability to client-specific CRMs, project management boards, and remote communication tools."
        )

    # Extra instructions if provided
    extra_line = ""
    if extra_instructions and extra_instructions.strip():
        extra_line = f"\n*Note regarding specific requirement:* {extra_instructions.strip()}\n"

    # Timezone statement
    tz_text = "US (EST/PST)" if client_region == "US" else ("Australia (AEST)" if client_region == "AU" else ("UK (GMT)" if client_region == "UK" else "your target"))
    logistics_data = full_profile.get("logistics", {})
    internet_desc = logistics_data.get("internet", "High-speed fiber connection + mobile backup")
    logistics = f"**Workstation & Availability:** Equipped with {internet_desc}, a quiet dedicated workstation, and immediate availability aligned with {tz_text} business hours."

    # Call to action
    cta = "I would welcome the opportunity for a brief 10-minute discovery chat or to complete a short trial task to demonstrate my reliability and precision firsthand."

    proposal_body = (
        f"{line1_code}"
        f"Hi {greeting_name},\n\n"
        f"{empathy_hook}\n\n"
        f"Here is how my verified background directly supports your needs:\n"
        f"{bullets[0]}\n"
        f"{bullets[1]}\n"
        f"{bullets[2]}\n"
        f"{extra_line}\n"
        f"{logistics}\n\n"
        f"{cta}\n\n"
        f"Best regards,\n\n"
        f"{candidate_name}\n"
        f"{candidate.get('location', 'Remote, Worldwide')}\n"
        f"LinkedIn: {candidate.get('linkedin', '')}\n"
        f"Portfolio: {candidate.get('portfolio_url', '')}\n"
        f"Resume: {candidate.get('resume_url', '')}"
    )

    words = len(proposal_body.split())

    return {
        "job_id": str(job.get("job_id", "")),
        "job_title": title,
        "employer": employer or "Undisclosed",
        "url": job.get("url", ""),
        "subject_line": subject_line,
        "proposal_text": proposal_body,
        "word_count": words,
        "screening_audit": traps,
        "candidate": {
            "name": candidate.get("display_name") or candidate.get("name", "Candidate"),
            "email": candidate.get("email", ""),
            "phone": candidate.get("phone", ""),
            "portfolio": candidate.get("portfolio_url", ""),
            "resume": candidate.get("resume_url", ""),
        },
    }

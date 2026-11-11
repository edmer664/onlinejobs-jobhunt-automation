import re
from typing import Any, Dict, List, Tuple

try:
    from config_loader import (
        get_role_categories,
        get_candidate_skills,
        get_potential_gaps,
        get_hard_mismatches,
        get_red_flags,
    )
except ImportError:
    from src.config_loader import (
        get_role_categories,
        get_candidate_skills,
        get_potential_gaps,
        get_hard_mismatches,
        get_red_flags,
    )

# ============================================================================
# DYNAMIC SUITABILITY & MATCHING MATRIX
# Loaded dynamically from config/profile.yaml or config/profile.json
# ============================================================================

ROLE_CATEGORIES = get_role_categories()
CANDIDATE_SKILLS = get_candidate_skills()
POTENTIAL_GAPS = get_potential_gaps()
HARD_MISMATCH_TITLE_PATTERNS = get_hard_mismatches()
RED_FLAG_PATTERNS = get_red_flags()


def reload_evaluation_rules() -> None:
    """Reloads evaluation rules dynamically when configuration changes."""
    global ROLE_CATEGORIES, CANDIDATE_SKILLS, POTENTIAL_GAPS, HARD_MISMATCH_TITLE_PATTERNS, RED_FLAG_PATTERNS
    ROLE_CATEGORIES = get_role_categories()
    CANDIDATE_SKILLS = get_candidate_skills()
    POTENTIAL_GAPS = get_potential_gaps()
    HARD_MISMATCH_TITLE_PATTERNS = get_hard_mismatches()
    RED_FLAG_PATTERNS = get_red_flags()


def detect_client_region(title: str, description: str, salary: str, posted_at: str) -> Tuple[str, str]:
    """
    Detects whether a job post targets AU, UK, US, or Global clients,
    plus identifies the posting peak window in Philippine Time (PHT).
    """
    combined = f"{title}\n{salary}\n{description}"
    combined_lower = combined.lower()

    au_score = 0
    uk_score = 0
    us_score = 0

    # Currency signals
    if re.search(r"\baud\b|a\$|\baus\s*\$", salary.lower()) or re.search(r"\baud\b", combined_lower):
        au_score += 5
    if re.search(r"\bgbp\b|£|\bpounds?\s*sterling\b", salary.lower()) or "£" in combined:
        uk_score += 5
    if re.search(r"\busd\b|\bus\s*\$", salary.lower()):
        us_score += 3

    # Location & Timezone signals - Australia
    au_patterns = [
        r"\baustralia(?:n)?\b", r"\bsydney\b", r"\bmelbourne\b", r"\bbrisbane\b",
        r"\bperth\b", r"\badelaide\b", r"\bcanberra\b", r"\bgold\s*coast\b",
        r"\baest\b", r"\baedt\b", r"\bawst\b", r"\bacst\b", r"\.com\.au\b",
        r"\bnew\s*south\s*wales\b", r"\bqueensland\b", r"\bvictoria\b"
    ]
    for pat in au_patterns:
        if re.search(pat, combined_lower):
            au_score += 3

    # Location & Timezone signals - UK
    uk_patterns = [
        r"\bunited\s*kingdom\b", r"\buk\s*(?:based|client|company|agency|time|hours|market)\b",
        r"\bbritish\b", r"\blondon\b", r"\bmanchester\b", r"\bbirmingham\b",
        r"\bedinburgh\b", r"\bglasgow\b", r"\bleeds\b", r"\bbristol\b",
        r"\bgmt\b", r"\bbst\b", r"\.co\.uk\b", r"\bhmrc\b", r"\bcompanies\s*house\b"
    ]
    for pat in uk_patterns:
        if re.search(pat, combined_lower):
            uk_score += 3

    # Location & Timezone signals - US
    us_patterns = [
        r"\bunited\s*states\b", r"\busa\b", r"\bu\.s\.a\.?\b",
        r"\bus\s*(?:based|client|company|agency|time|hours|market|real\s*estate|tax)\b",
        r"\best\b", r"\bedt\b", r"\bpst\b", r"\bpdt\b", r"\bcst\b", r"\bcdt\b", r"\bmst\b",
        r"\beastern\s*(?:time|standard|daylight)\b", r"\bpacific\s*(?:time|standard|daylight)\b",
        r"\bcentral\s*(?:time|standard)\b", r"\bnew\s*york\b", r"\bcalifornia\b",
        r"\btexas\b", r"\bflorida\b", r"\bchicago\b", r"\blos\s*angeles\b", r"\bmiami\b",
        r"\batlanta\b", r"\bseattle\b", r"\bboston\b", r"\bdenver\b"
    ]
    for pat in us_patterns:
        if re.search(pat, combined_lower):
            us_score += 3

    # Determine peak window from posted_at (PHT = UTC+8)
    peak_window = "General"
    m = re.search(r"(\d{4}-\d{2}-\d{2})\s+(\d{2}):(\d{2})", posted_at or "")
    if m:
        hour_pht = int(m.group(2))
        if 6 <= hour_pht <= 13:
            peak_window = "AU Peak (06:00-13:59 PHT)"
            if au_score == 0 and uk_score == 0 and us_score == 0 and "$" in salary and "sgd" not in salary.lower():
                au_score += 1
        elif 15 <= hour_pht <= 20:
            peak_window = "UK/EU Peak (15:00-20:59 PHT)"
        elif hour_pht >= 21 or hour_pht <= 5:
            peak_window = "US Peak (21:00-05:59 PHT)"
            if us_score == 0 and au_score == 0 and uk_score == 0 and "$" in salary:
                us_score += 1

    # Pick region
    max_score = max(au_score, uk_score, us_score)
    if max_score >= 2:
        if au_score == max_score:
            region = "AU"
        elif uk_score == max_score:
            region = "UK"
        else:
            region = "US"
    elif "$" in salary and not any(c in salary.lower() for c in ["sgd", "hkd", "cad", "nzd", "php"]):
        region = "US" if peak_window.startswith("US") else ("AU" if "aud" in salary.lower() else "US")
    else:
        region = "Global"

    return region, peak_window


def estimate_monthly_usd(salary_str: str) -> float:
    """
    Parses OnlineJobs.ph salary strings into an approximate monthly USD float for sorting.
    """
    if not salary_str:
        return 0.0
    s = salary_str.lower().replace(",", "")

    fx = 1.0
    if "aud" in s or "a$" in s:
        fx = 0.66
    elif "gbp" in s or "£" in s:
        fx = 1.28
    elif "eur" in s or "€" in s:
        fx = 1.08
    elif "cad" in s:
        fx = 0.73
    elif "sgd" in s:
        fx = 0.75
    elif "php" in s or "₱" in s or "peso" in s:
        fx = 0.0175

    nums = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", s)]
    nums = [n for n in nums if n != 2026 and n > 0]
    if not nums:
        return 0.0

    val = nums[0]
    if len(nums) >= 2 and nums[1] > nums[0] and nums[1] <= nums[0] * 4:
        val = (nums[0] + nums[1]) / 2.0

    if fx == 1.0 and val >= 12000:
        fx = 0.0175

    if any(p in s for p in ["/hr", "/hour", "per hour", "hourly", "hr"]):
        if val < 150:
            return round(val * 160.0 * fx, 2)
    if any(p in s for p in ["/wk", "/week", "per week", "weekly"]):
        if val < 2000:
            return round(val * 4.33 * fx, 2)

    if val <= 25 and fx >= 0.6:
        return round(val * 160.0 * fx, 2)

    return round(val * fx, 2)


def evaluate_job(job_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluates a scraped job against candidate profile and skills.
    Returns enrichment dict to merge into job_data.
    """
    title = (job_data.get("title") or "").strip()
    description = (job_data.get("description") or job_data.get("description_snippet") or "").strip()
    salary = (job_data.get("salary") or "Not specified").strip()
    arrangement = (job_data.get("arrangement") or "Any").strip()
    posted_at = (job_data.get("posted_at") or "").strip()
    tags = job_data.get("skills_tags") or []
    tags_str = " ".join(tags) if isinstance(tags, list) else str(tags)

    full_text = f"{title}\n{tags_str}\n{description}"
    full_lower = full_text.lower()
    title_lower = title.lower()

    # 1. Detect Client Region & Peak Window
    client_region, peak_window = detect_client_region(title, description, salary, posted_at)
    salary_usd_est = estimate_monthly_usd(salary)

    # 2. Check Hard Mismatches / Seniority Dealbreakers first
    hard_mismatch = any(re.search(pat, title_lower) for pat in HARD_MISMATCH_TITLE_PATTERNS)

    # 3. Classify Role Category & Base Fit Score
    best_category = "Other"
    category_score = 18
    selling_points: List[str] = []

    for cat_name, cat_info in ROLE_CATEGORIES.items():
        matched_in_title = any(re.search(pat, title_lower) for pat in cat_info["title_keywords"])
        if matched_in_title:
            if cat_info["base_fit"] > category_score:
                category_score = cat_info["base_fit"]
                best_category = cat_name
            selling_points.append(cat_info["selling_point"])

    # If title didn't directly match a category, check skill tags only
    if best_category == "Other" and not hard_mismatch:
        lead_text = f"{title_lower} {tags_str.lower()}"
        for cat_name, cat_info in ROLE_CATEGORIES.items():
            if any(re.search(pat, lead_text) for pat in cat_info["title_keywords"]):
                category_score = max(category_score, int(cat_info["base_fit"] * 0.78))
                best_category = cat_name
                selling_points.append(cat_info["selling_point"])
                break

    # 4. Check Candidate Skill Matches
    matched_skills: List[str] = []
    skill_points = 0
    for skill_label, patterns, weight in CANDIDATE_SKILLS:
        if any(re.search(pat, full_lower) for pat in patterns):
            matched_skills.append(skill_label)
            if any(re.search(pat, title_lower) for pat in patterns):
                skill_points += weight + 2
            else:
                skill_points += weight

    skill_points = min(40, skill_points)

    # 5. Identify Missing Skills / Gaps
    missing_skills: List[str] = []
    gap_penalty = 0
    for gap_label, patterns in POTENTIAL_GAPS:
        if any(re.search(pat, full_lower) for pat in patterns):
            missing_skills.append(gap_label)
            if any(re.search(pat, title_lower) for pat in patterns):
                gap_penalty += 18
            else:
                gap_penalty += 4

    gap_penalty = min(38, gap_penalty)

    # Experience requirement check (e.g. "5+ years required" or "Senior" in title)
    exp_penalty = 0
    if re.search(r"\b([5-9]|1\d)\+?\s*years?\s+(?:of\s+)?experience\b", full_lower):
        exp_penalty += 12
    if re.search(r"\bsenior\b", title_lower):
        exp_penalty += 12

    # 6. Arrangement & Client Region Alignment Bonus
    arrangement_bonus = 6 if ("full" in arrangement.lower() or "any" in arrangement.lower()) else 5
    region_bonus = 4 if client_region in ("US", "UK", "AU") else 2

    # 7. Red Flags Detection
    red_flags: List[str] = []
    for flag_label, patterns in RED_FLAG_PATTERNS:
        if any(re.search(pat, full_lower) for pat in patterns):
            red_flags.append(flag_label)

    red_flag_penalty = min(12, len(red_flags) * 4)

    # 8. Compute Final Match Score (0 - 100)
    raw_score = category_score + skill_points + arrangement_bonus + region_bonus - gap_penalty - exp_penalty - red_flag_penalty
    if hard_mismatch:
        raw_score = min(raw_score, 38)
    if best_category == "Other" and len(matched_skills) <= 2:
        raw_score = min(raw_score, 45)

    match_score = max(12, min(98, int(round(raw_score))))

    # 9. Suitability Tier (aligned with job-description-analyzer)
    if match_score >= 80:
        suitability_tier = "Excellent Fit"
        recommendation = "STRONG FIT — Apply immediately with tailored resume"
    elif match_score >= 65:
        suitability_tier = "Good Fit"
        recommendation = "GOOD FIT — Apply and emphasize transferable strengths in cover letter"
    elif match_score >= 50:
        suitability_tier = "Moderate Fit"
        recommendation = "STRETCH ROLE — Apply if interested; address tool/skill gaps proactively"
    else:
        suitability_tier = "Low Fit"
        recommendation = "LOW FIT — Outside core target roles or requires specialized stack"

    if not selling_points:
        if any("Sheet" in s or "Excel" in s for s in matched_skills):
            selling_points.append("Advanced spreadsheet, data management, and cloud database administration experience.")
        if any("Design" in s or "Video" in s or "Content" in s for s in matched_skills):
            selling_points.append("Experienced creating visual assets, branded content, and digital media.")
        if not selling_points:
            selling_points.append("Proven administrative, operations, and analytical background with rapid adaptability.")

    unique_strengths = list(dict.fromkeys(selling_points))[:3]

    summary_parts = [
        f"{recommendation} ({match_score}% Match | {best_category} | {client_region} Client).",
    ]
    if matched_skills:
        summary_parts.append(f"Matched Strengths ({len(matched_skills)}): {', '.join(matched_skills[:6])}.")
    if missing_skills:
        summary_parts.append(f"Gaps to Note: {', '.join(missing_skills[:4])}.")
    if unique_strengths:
        summary_parts.append(f"Resume Angle: {unique_strengths[0]}")

    evaluation_summary = " ".join(summary_parts)

    return {
        "client_region": client_region,
        "peak_window": peak_window,
        "salary_usd_monthly_est": salary_usd_est,
        "match_score": match_score,
        "suitability_tier": suitability_tier,
        "is_matched": 1 if match_score >= 60 else 0,
        "role_category": best_category,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "red_flags": red_flags,
        "strengths": unique_strengths,
        "evaluation_summary": evaluation_summary,
    }

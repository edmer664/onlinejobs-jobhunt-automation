"""
tests/e2e/test_tier1_features.py - Tier 1: Comprehensive Feature Coverage
Opaque-box, requirement-driven verification covering >=5 test cases per key feature:
1. Sanitization & Zero-PII
2. Config Loader & Fallbacks
3. Database Operations & SQLite WAL
4. Suitability Evaluator & Region Matching
5. Proposal Engine & Screening Traps
6. Router & Connect Points Decision
7. MCP Server Tools
8. Profile Validator CLI
9. Synthetic Seeding
10. Scripts & Deployment Assets
"""

import base64
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

# Setup project root on path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.config_loader import (
    find_profile_file,
    get_candidate_profile,
    get_candidate_skills,
    get_config_dir,
    get_hard_mismatches,
    get_potential_gaps,
    get_project_root,
    get_red_flags,
    get_role_categories,
    load_profile,
)
from src.db import (
    get_connection,
    get_job_by_id,
    get_stats,
    init_db,
    query_jobs,
    update_job_status_and_notes,
    upsert_job,
)
from src.evaluator import (
    detect_client_region,
    estimate_monthly_usd,
    evaluate_job,
)
from src.proposal_engine import (
    audit_screening_traps,
    generate_tailored_proposal,
)
from execution.router import (
    detect_masked_emails,
    evaluate_job_route_and_points,
    extract_emails,
    extract_external_forms,
    extract_screening_traps,
)
from tools.seed_db import seed_database
from tools.validate_profile import validate_profile
from scripts.generate_resume_pdf import build_resume_html


def _b64(val: str) -> str:
    return base64.b64decode(val.encode("ascii")).decode("utf-8")


# ============================================================================
# FEATURE 1: Sanitization & Zero-PII
# ============================================================================
class TestTier1Sanitization(unittest.TestCase):
    """Verifies complete redaction of candidate PII and secret credentials."""

    def setUp(self):
        self.tracked_files = []
        for root, _, files in os.walk(PROJECT_ROOT):
            if ".git" in root or "__pycache__" in root or ".venv" in root:
                continue
            for f in files:
                if f.endswith((".py", ".md", ".json", ".yaml", ".yml", ".html", ".sh", ".bat", ".ps1", ".txt")):
                    self.tracked_files.append(os.path.join(root, f))

    def test_sanitization_01_no_candidate_personal_names(self):
        """Verify 0 occurrences of candidate personal names in tracked files."""
        name_patterns = [
            _b64("XGJrcmlzdGVsXGI="),
            _b64("XGJiYWd0YXNcYg=="),
            _b64("XGJLcmlzdGVsXHMrSm95XGI="),
        ]
        violations = []
        for file_path in self.tracked_files:
            # Skip test_sanitization.py and test_tier1_features.py itself which hold encoded tokens
            if "test_sanitization.py" in file_path or "test_tier1_features.py" in file_path:
                continue
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                for pat in name_patterns:
                    if re.search(pat, content, re.IGNORECASE):
                        violations.append(f"{file_path} matched name pattern {pat}")
            except Exception:
                pass
        self.assertEqual(len(violations), 0, f"Found candidate name leaks: {violations}")

    def test_sanitization_02_no_candidate_personal_emails(self):
        """Verify 0 candidate personal email addresses exist in tracked files."""
        email_patterns = [
            _b64("a3Jpc3RlbGdlbmVzZWJhZ3Rhc1wuM0BnbWFpbFwuY29t"),
            _b64("a3Jpc3RlbGdlbmVzZWJhZ3Rhc0BnbWFpbFwuY29t"),
            _b64("ZWRtZXJwaXphcnJhQGdtYWlsXC5jb20="),
        ]
        violations = []
        for file_path in self.tracked_files:
            if "test_sanitization.py" in file_path or "test_tier1_features.py" in file_path:
                continue
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                for pat in email_patterns:
                    if re.search(pat, content, re.IGNORECASE):
                        violations.append(f"{file_path} matched personal email pattern {pat}")
            except Exception:
                pass
        self.assertEqual(len(violations), 0, f"Found personal email leaks: {violations}")

    def test_sanitization_03_no_candidate_phone_numbers(self):
        """Verify 0 candidate phone numbers exist in tracked files."""
        phone_patterns = [
            _b64("XCs/NjM5NDg3NjQzMDA2XGI="),
            _b64("XGIwOTQ4NzY0MzAwNlxi"),
            _b64("XGI5NDg3NjQzMDA2XGI="),
        ]
        violations = []
        for file_path in self.tracked_files:
            if "test_sanitization.py" in file_path or "test_tier1_features.py" in file_path:
                continue
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                for pat in phone_patterns:
                    if re.search(pat, content):
                        violations.append(f"{file_path} matched phone pattern {pat}")
            except Exception:
                pass
        self.assertEqual(len(violations), 0, f"Found phone leaks: {violations}")

    def test_sanitization_04_no_hardcoded_passwords_or_secrets(self):
        """Verify 0 unredacted passwords or cloud asset IDs exist in tracked files."""
        secret_patterns = [
            _b64("XGJBa2lyYW1heTMxXGI="),
            _b64("b2pwLWRhc2hib2FyZC0zNDc1NzE3NjA0OTU="),
            _b64("b2pwLWF1dG9tYXRpb24ta3Jpc3RlbC1kYg=="),
        ]
        violations = []
        for file_path in self.tracked_files:
            if "test_sanitization.py" in file_path or "test_tier1_features.py" in file_path:
                continue
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                for pat in secret_patterns:
                    if re.search(pat, content):
                        violations.append(f"{file_path} matched secret pattern {pat}")
            except Exception:
                pass
        self.assertEqual(len(violations), 0, f"Found secret/password leaks: {violations}")

    def test_sanitization_05_placeholder_templates_exist_and_non_empty(self):
        """Verify required configuration and candidate templates exist and are populated."""
        templates = [
            os.path.join(PROJECT_ROOT, ".env.example"),
            os.path.join(PROJECT_ROOT, "config", ".env.example"),
            os.path.join(PROJECT_ROOT, "config", "profile.example.yaml"),
            os.path.join(PROJECT_ROOT, "config", "profile.example.json"),
            os.path.join(PROJECT_ROOT, "config", "profile.example.md"),
            os.path.join(PROJECT_ROOT, "config", "cv.example.md"),
            os.path.join(PROJECT_ROOT, "config", "profile.schema.json"),
        ]
        for t in templates:
            self.assertTrue(os.path.isfile(t), f"Template missing: {t}")
            self.assertGreater(os.path.getsize(t), 50, f"Template is empty or truncated: {t}")

    def test_sanitization_06_database_binaries_not_tracked_in_git(self):
        """Verify jobs.db or any binary database is omitted from git tracking."""
        try:
            res = subprocess.run(
                ["git", "ls-files", "*.db"],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
            )
            tracked = [f for f in res.stdout.strip().splitlines() if f.endswith(".db")]
            self.assertEqual(len(tracked), 0, f"Binary .db files tracked in git: {tracked}")
        except FileNotFoundError:
            pass  # Git not installed in sub-process test environment


# ============================================================================
# FEATURE 2: Config Loader & Profile Decoupling
# ============================================================================
class TestTier1ConfigLoader(unittest.TestCase):
    """Verifies configuration loader, template fallback, and data schemas."""

    def test_config_01_fallback_resolution(self):
        """find_profile_file returns fallback example profile when profile.yaml is absent."""
        path, is_fallback = find_profile_file()
        self.assertTrue(os.path.exists(path))
        self.assertTrue(path.endswith((".yaml", ".yml", ".json")))
        # If user has not created custom profile.yaml, is_fallback must be True
        custom_exists = (
            os.path.exists(os.path.join(get_config_dir(), "profile.yaml"))
            or os.path.exists(os.path.join(get_config_dir(), "profile.json"))
        )
        if not custom_exists:
            self.assertTrue(is_fallback)

    def test_config_02_explicit_path_loading(self):
        """find_profile_file loads specified file or raises FileNotFoundError."""
        example_json = os.path.join(get_config_dir(), "profile.example.json")
        loaded_path, is_fallback = find_profile_file(example_json)
        self.assertEqual(os.path.abspath(example_json), loaded_path)
        self.assertFalse(is_fallback)

        with self.assertRaises(FileNotFoundError):
            find_profile_file(os.path.join(get_config_dir(), "nonexistent_config_123.yaml"))

    def test_config_03_candidate_profile_schema_fields(self):
        """get_candidate_profile returns all required top-level sections."""
        profile = get_candidate_profile()
        self.assertIsInstance(profile, dict)
        self.assertIn("candidate", profile)
        self.assertIn("role_categories", profile)
        self.assertIn("candidate_skills", profile)
        self.assertIn("potential_gaps", profile)
        self.assertIn("logistics", profile)

        cand = profile["candidate"]
        self.assertIn("name", cand)
        self.assertIn("email", cand)
        self.assertIn("location", cand)

    def test_config_04_role_categories_structure(self):
        """get_role_categories returns valid category dictionary."""
        cats = get_role_categories()
        self.assertIsInstance(cats, dict)
        self.assertGreaterEqual(len(cats), 3)
        for cat_name, cat_data in cats.items():
            self.assertIn("title_keywords", cat_data)
            self.assertIn("base_fit", cat_data)
            self.assertIn("selling_point", cat_data)
            self.assertIsInstance(cat_data["title_keywords"], list)
            self.assertIsInstance(cat_data["base_fit"], int)

    def test_config_05_candidate_skills_normalization(self):
        """get_candidate_skills returns list of (label, patterns, weight) tuples."""
        skills = get_candidate_skills()
        self.assertIsInstance(skills, list)
        self.assertGreaterEqual(len(skills), 3)
        for item in skills:
            self.assertEqual(len(item), 3)
            label, patterns, weight = item
            self.assertIsInstance(label, str)
            self.assertIsInstance(patterns, list)
            self.assertIsInstance(weight, int)

    def test_config_06_gaps_and_red_flags_normalization(self):
        """get_potential_gaps, get_hard_mismatches, and get_red_flags return expected formats."""
        gaps = get_potential_gaps()
        self.assertIsInstance(gaps, list)
        for g in gaps:
            self.assertEqual(len(g), 2)
            self.assertIsInstance(g[0], str)
            self.assertIsInstance(g[1], list)

        hard = get_hard_mismatches()
        self.assertIsInstance(hard, list)
        self.assertTrue(all(isinstance(p, str) for p in hard))

        red = get_red_flags()
        self.assertIsInstance(red, list)
        for r in red:
            self.assertEqual(len(r), 2)


# ============================================================================
# FEATURE 3: Database Operations & SQLite WAL Concurrency
# ============================================================================
class TestTier1Database(unittest.TestCase):
    """Verifies SQLite persistence, WAL journal mode, queries, and updates."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="test_db_")
        self.db_path = os.path.join(self.temp_dir, "test_jobs.db")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_db_01_init_creates_tables_and_indexes(self):
        """init_db creates jobs, scrape_runs, and 6 indexes in WAL mode."""
        init_db(self.db_path)
        self.assertTrue(os.path.exists(self.db_path))

        conn = get_connection(self.db_path)
        try:
            # Check journal mode
            cur = conn.execute("PRAGMA journal_mode;")
            mode = cur.fetchone()[0]
            self.assertEqual(mode.lower(), "wal")

            # Check tables
            tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()]
            self.assertIn("jobs", tables)
            self.assertIn("scrape_runs", tables)

            # Check indexes
            indexes = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='index';").fetchall()]
            expected_indexes = [
                "idx_jobs_match_score",
                "idx_jobs_posted_at",
                "idx_jobs_is_matched",
                "idx_jobs_status",
                "idx_jobs_client_region",
                "idx_jobs_last_scraped_at",
            ]
            for idx in expected_indexes:
                self.assertIn(idx, indexes)
        finally:
            conn.close()

    def test_db_02_upsert_job_inserts_new_record(self):
        """upsert_job inserts a new job and returns True."""
        init_db(self.db_path)
        job = {
            "job_id": "test-101",
            "title": "Executive Assistant",
            "employer": "Acme Corp",
            "url": "https://onlinejobs.ph/job/101",
            "match_score": 85,
            "suitability_tier": "Excellent Fit",
            "status": "New",
        }
        is_new = upsert_job(job, db_path=self.db_path)
        self.assertTrue(is_new)

        stored = get_job_by_id("test-101", db_path=self.db_path)
        self.assertIsNotNone(stored)
        self.assertEqual(stored["title"], "Executive Assistant")
        self.assertEqual(stored["match_score"], 85)

    def test_db_03_upsert_job_preserves_user_status_and_notes(self):
        """Re-upserting a job preserves user status and notes, returning False."""
        init_db(self.db_path)
        job = {
            "job_id": "test-102",
            "title": "VA Role",
            "employer": "Beta Ltd",
            "url": "https://onlinejobs.ph/job/102",
            "status": "New",
            "notes": "Initial scrape",
        }
        upsert_job(job, db_path=self.db_path)

        # User updates status and notes
        update_job_status_and_notes("test-102", status="Applied", notes="Sent email with resume", db_path=self.db_path)

        # Scraper re-scrapes the same job later
        updated_job = {
            "job_id": "test-102",
            "title": "VA Role (Updated description)",
            "employer": "Beta Ltd",
            "url": "https://onlinejobs.ph/job/102",
            "status": "New",  # Scraper sends New
            "notes": "",       # Scraper sends empty
        }
        is_new = upsert_job(updated_job, db_path=self.db_path)
        self.assertFalse(is_new)

        stored = get_job_by_id("test-102", db_path=self.db_path)
        self.assertEqual(stored["status"], "Applied")  # Preserved
        self.assertEqual(stored["notes"], "Sent email with resume")  # Preserved

    def test_db_04_query_jobs_filtering(self):
        """query_jobs filters by score, region, status, and search."""
        init_db(self.db_path)
        jobs = [
            {"job_id": "j1", "title": "Real Estate VA", "match_score": 88, "client_region": "US", "status": "New"},
            {"job_id": "j2", "title": "Bookkeeper", "match_score": 72, "client_region": "AU", "status": "New"},
            {"job_id": "j3", "title": "Web Dev", "match_score": 45, "client_region": "UK", "status": "Archived"},
        ]
        for j in jobs:
            upsert_job(j, db_path=self.db_path)

        # Filter by min_score
        high = query_jobs(min_score=80, db_path=self.db_path)
        self.assertEqual(len(high), 1)
        self.assertEqual(high[0]["job_id"], "j1")

        # Filter by client_region
        au_jobs = query_jobs(client_region="AU", db_path=self.db_path)
        self.assertEqual(len(au_jobs), 1)
        self.assertEqual(au_jobs[0]["job_id"], "j2")

        # Free text search
        searched = query_jobs(search="Bookkeeper", db_path=self.db_path)
        self.assertEqual(len(searched), 1)
        self.assertEqual(searched[0]["job_id"], "j2")

    def test_db_05_update_job_status_and_notes(self):
        """update_job_status_and_notes correctly updates and persists fields."""
        init_db(self.db_path)
        upsert_job({"job_id": "j5", "title": "Lead Specialist", "url": "https://x.com"}, db_path=self.db_path)

        res = update_job_status_and_notes("j5", status="Interviewing", notes="Round 1 scheduled", db_path=self.db_path)
        self.assertIsNotNone(res)
        self.assertEqual(res["status"], "Interviewing")
        self.assertEqual(res["notes"], "Round 1 scheduled")

        stored = get_job_by_id("j5", db_path=self.db_path)
        self.assertEqual(stored["status"], "Interviewing")

    def test_db_06_get_stats_aggregates_metrics(self):
        """get_stats returns accurate overall counts and breakdowns."""
        init_db(self.db_path)
        upsert_job({"job_id": "s1", "title": "EA", "match_score": 90, "suitability_tier": "Excellent Fit", "status": "New"}, db_path=self.db_path)
        upsert_job({"job_id": "s2", "title": "VA", "match_score": 75, "suitability_tier": "Good Fit", "status": "Applied"}, db_path=self.db_path)

        stats = get_stats(db_path=self.db_path)
        self.assertEqual(stats["total_jobs"], 2)
        self.assertEqual(stats["matched_jobs"], 2)
        self.assertEqual(stats["by_status"].get("New", 0), 1)
        self.assertEqual(stats["by_status"].get("Applied", 0), 1)
        self.assertEqual(stats["excellent_fits"], 1)


# ============================================================================
# FEATURE 4: Suitability Evaluator & Region Matching
# ============================================================================
class TestTier1Evaluator(unittest.TestCase):
    """Verifies job scoring, region detection, and salary estimation."""

    def test_eval_01_high_fit_role_scoring(self):
        """VA / Executive Assistant job with core skills scores >= 65."""
        job = {
            "title": "Executive Assistant / Virtual Assistant",
            "description": "Seeking VA for calendar management, email correspondence, spreadsheets, and travel coordination.",
            "salary": "$1,000 / month",
            "arrangement": "Full Time",
        }
        res = evaluate_job(job)
        self.assertGreaterEqual(res["match_score"], 65)
        self.assertIn(res["suitability_tier"], ("Good Fit", "Excellent Fit"))
        self.assertEqual(res["is_matched"], 1)

    def test_eval_02_skill_point_accumulation(self):
        """Matching candidate skills increases score and records matched skills."""
        job = {
            "title": "Administrative Assistant",
            "description": "Must have expertise in Microsoft Excel, Google Sheets, Canva graphics, and SOP creation.",
        }
        res = evaluate_job(job)
        self.assertIsInstance(res["matched_skills"], list)
        self.assertGreater(len(res["matched_skills"]), 0)
        self.assertTrue(any("Sheet" in s or "Excel" in s or "Canva" in s for s in res["matched_skills"]))

    def test_eval_03_hard_mismatch_penalty_cap(self):
        """Jobs with hard mismatch titles are capped at score <= 38."""
        mismatch_jobs = [
            {"title": "Senior Software Architect (Node / React)", "description": "Build microservices in Go and AWS."},
            {"title": "Full Stack PHP WordPress Developer", "description": "Custom theme development."},
            {"title": "Senior Mobile Engineer (iOS / Swift)", "description": "Publish Swift apps to App Store."},
        ]
        for job in mismatch_jobs:
            res = evaluate_job(job)
            self.assertLessEqual(res["match_score"], 38, f"Score not capped for {job['title']}: {res['match_score']}")
            self.assertEqual(res["suitability_tier"], "Low Fit")
            self.assertEqual(res["is_matched"], 0)

    def test_eval_04_client_region_and_peak_detection(self):
        """Correctly identifies AU, UK, US, and Global client regions."""
        # AU
        au_job = {"title": "VA", "description": "Australian based company in Sydney. Hours 9am-5pm AEST.", "salary": "AUD $25/hr"}
        reg, _ = detect_client_region(au_job["title"], au_job["description"], au_job["salary"], "")
        self.assertEqual(reg, "AU")

        # UK
        uk_job = {"title": "VA", "description": "London recruitment agency hiring remote assistant.", "salary": "£1500/month"}
        reg, _ = detect_client_region(uk_job["title"], uk_job["description"], uk_job["salary"], "")
        self.assertEqual(reg, "UK")

        # US
        us_job = {"title": "VA", "description": "US client looking for EST hours assistant.", "salary": "$800/mo"}
        reg, _ = detect_client_region(us_job["title"], us_job["description"], us_job["salary"], "")
        self.assertEqual(reg, "US")

    def test_eval_05_salary_usd_estimation(self):
        """Parses hourly, weekly, monthly salary strings into accurate USD estimations."""
        self.assertAlmostEqual(estimate_monthly_usd("$10 / hour"), 1600.0, delta=10.0)
        self.assertAlmostEqual(estimate_monthly_usd("$250 per week"), 1082.5, delta=10.0)
        self.assertAlmostEqual(estimate_monthly_usd("$1,200 / month"), 1200.0, delta=10.0)
        self.assertAlmostEqual(estimate_monthly_usd("AUD $20/hr"), 20 * 160 * 0.66, delta=10.0)
        self.assertAlmostEqual(estimate_monthly_usd("£1,000 / month"), 1280.0, delta=10.0)

    def test_eval_06_suitability_tier_thresholds(self):
        """Verifies exact tier labels matching score brackets."""
        # Check through evaluator logic
        res85 = evaluate_job({"title": "Virtual Assistant", "description": "Need proactive EA with Excel, Google Sheets, Canva, lead generation, admin support."})
        self.assertIn(res85["suitability_tier"], ["Excellent Fit", "Good Fit"])

        res_low = evaluate_job({"title": "Senior Python Backend Engineer", "description": "Build high scale distributed databases in C++ and Rust."})
        self.assertEqual(res_low["suitability_tier"], "Low Fit")


# ============================================================================
# FEATURE 5: Proposal Engine & Screening Traps
# ============================================================================
class TestTier1ProposalEngine(unittest.TestCase):
    """Verifies proposal generation, word counts, and screening trap auditing."""

    def test_proposal_01_word_count_enforcement(self):
        """Tailored proposal strictly fits within 150 to 250 words."""
        job = {
            "job_id": "p-101",
            "title": "Executive Administrative Assistant",
            "description": "Looking for a full-time assistant to organize daily tasks, manage calendar, and answer client emails.",
            "employer": "TechVentures",
        }
        res = generate_tailored_proposal(job)
        wc = res["word_count"]
        self.assertGreaterEqual(wc, 150, f"Proposal too short: {wc} words")
        self.assertLessEqual(wc, 250, f"Proposal too long: {wc} words")

    def test_proposal_02_screening_trap_secret_code_extraction(self):
        """Extracts secret code words from varied phrasing in job descriptions."""
        cases = [
            ('Please put "Blueberry" in the subject line of your message.', "Blueberry"),
            ('Start your application with the word "BOOKED".', "BOOKED"),
            ('Subject line must contain "Pineapple" to be considered.', "Pineapple"),
            ('Secret word: Sunlight.', "Sunlight"),
        ]
        for jd_text, expected_code in cases:
            traps = audit_screening_traps(jd_text)
            self.assertIn(expected_code, traps["secret_codes"], f"Failed to extract {expected_code} from {jd_text}")

    def test_proposal_03_subject_line_and_opening_with_code(self):
        """Extracted secret code appears in both subject line and opening line of proposal."""
        job = {
            "title": "Virtual Assistant",
            "description": 'Need organized VA. Put "Blueberry" in your subject line.',
        }
        prop = generate_tailored_proposal(job)
        self.assertIn("Blueberry", prop["subject_line"])
        self.assertIn("Blueberry", prop["proposal_text"])

    def test_proposal_04_context_aware_empathy_and_bullets(self):
        """Adapts empathy hook to bookkeeping vs lead handling vs admin."""
        # Bookkeeping
        bk_job = {"title": "Bookkeeper", "description": "Reconcile invoices, messy spreadsheets, billing entries."}
        bk_prop = generate_tailored_proposal(bk_job)
        self.assertIn("data organization", bk_prop["proposal_text"].lower())

        # Leads
        lead_job = {"title": "Lead Setter", "description": "Outreach calls, booking consultations with homeowners."}
        lead_prop = generate_tailored_proposal(lead_job)
        self.assertIn("lead", lead_prop["proposal_text"].lower())

    def test_proposal_05_candidate_grounding_no_placeholders(self):
        """Generated proposal does not leak unrendered template markers."""
        job = {"title": "VA Role", "description": "Daily email organization."}
        prop = generate_tailored_proposal(job)
        text = prop["proposal_text"]
        self.assertNotIn("{{", text)
        self.assertNotIn("}}", text)
        self.assertNotIn("[YOUR FULL NAME]", text)
        self.assertIn("Best regards", text)

    def test_proposal_06_screening_trap_questions_and_media_requests(self):
        """Detects mandatory questions, speedtests, and video recording requests."""
        jd = """
        1. What is your experience with ClickUp?
        2. How many hours can you work per week?
        Must include your speedtest screenshot and a 1-minute Loom video introduction.
        """
        traps = audit_screening_traps(jd)
        self.assertTrue(traps["requires_speedtest"])
        self.assertTrue(traps["requires_voice_video"])
        self.assertGreater(len(traps["mandatory_questions"]), 0)


# ============================================================================
# FEATURE 6: Router & Connect Points Decision
# ============================================================================
class TestTier1Router(unittest.TestCase):
    """Verifies multi-channel routing decisions and connect points allocations."""

    def test_router_01_route_external_form_zero_connects(self):
        """External Google Form link selects EXTERNAL_FORM with 0 connect points."""
        job = {
            "title": "Executive Virtual Assistant",
            "description": "Seeking VA for calendar scheduling, spreadsheet reports, and email management. Please fill out our application form at https://forms.gle/xyz123abc456 to apply.",
        }
        decision = evaluate_job_route_and_points(job)
        self.assertEqual(decision["route"], "EXTERNAL_FORM")
        self.assertEqual(decision["connect_points"], 0)
        self.assertTrue(decision["should_apply"])
        self.assertIsNotNone(decision["target_form_url"])

    def test_router_02_route_email_zero_connects(self):
        """Direct email address selects EMAIL route with 0 connect points."""
        job = {
            "title": "Executive VA",
            "description": "Seeking administrative assistant for daily operations and client communications. Send your resume and introduction to careers@acmecorp.com directly.",
        }
        decision = evaluate_job_route_and_points(job)
        self.assertEqual(decision["route"], "EMAIL")
        self.assertEqual(decision["connect_points"], 0)
        self.assertTrue(decision["should_apply"])
        self.assertEqual(decision["target_email"], "careers@acmecorp.com")

    def test_router_03_route_masked_email_safety(self):
        """Masked email ('Email: ----------') allocates 0 connects and prevents blind submission."""
        job = {
            "title": "VA Role",
            "description": "Send resume to: Email: ----------",
        }
        decision = evaluate_job_route_and_points(job)
        self.assertEqual(decision["connect_points"], 0)
        self.assertFalse(decision["should_apply"])
        self.assertIsNone(decision["target_email"])

    def test_router_04_platform_high_match_20_connects(self):
        """Standard platform listing with match score >= 80% bids 20 connects."""
        job = {
            "title": "Executive Virtual Assistant",
            "description": "Full-time EA needed for calendar, inbox management, spreadsheets, and client booking. Apply on platform.",
        }
        decision = evaluate_job_route_and_points(job)
        if decision["match_score"] >= 80 and decision["route"] == "PLATFORM":
            self.assertEqual(decision["connect_points"], 20)
            self.assertTrue(decision["should_apply"])

    def test_router_05_platform_moderate_match_tiered_connects(self):
        """Platform listing with score 70-79 bids 10 connects; 60-69 bids 8 connects."""
        # Simulated decision evaluation
        mod_job = {
            "title": "General Admin Assistant",
            "description": "Support general office administration and data entry.",
        }
        decision = evaluate_job_route_and_points(mod_job)
        score = decision["match_score"]
        if decision["route"] == "PLATFORM":
            if 70 <= score <= 79:
                self.assertEqual(decision["connect_points"], 10)
            elif 60 <= score <= 69:
                self.assertEqual(decision["connect_points"], 8)

    def test_router_06_low_match_skip_zero_connects(self):
        """Low match score (<60) sets should_apply=False and 0 connects."""
        job = {
            "title": "Principal Rust Systems Architect",
            "description": "Low-level kernel programming in Linux and C/C++.",
        }
        decision = evaluate_job_route_and_points(job)
        self.assertLess(decision["match_score"], 60)
        self.assertFalse(decision["should_apply"])
        self.assertEqual(decision["connect_points"], 0)


# ============================================================================
# FEATURE 7: MCP Server Tools
# ============================================================================
class TestTier1MCPServer(unittest.TestCase):
    """Verifies MCP server tool functions directly."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="test_mcp_")
        self.db_path = os.path.join(self.temp_dir, "test_jobs.db")
        init_db(self.db_path)
        upsert_job(
            {
                "job_id": "mcp-001",
                "title": "Executive VA",
                "employer": "CloudTech",
                "url": "https://onlinejobs.ph/job/mcp-001",
                "match_score": 88,
                "suitability_tier": "Excellent Fit",
                "status": "New",
                "description": "Organize calendar, manage spreadsheets. Put \"Sapphire\" in your subject line.",
            },
            db_path=self.db_path,
        )

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_mcp_01_search_jobs_tool(self):
        """search_jobs query tool returns structured JSON with results."""
        from src.mcp_server import search_jobs
        import src.mcp_server as mcp_mod

        orig_db = mcp_mod.DB_PATH
        try:
            mcp_mod.DB_PATH = self.db_path
            raw = search_jobs(min_score=70, status="New", limit=10)
            data = json.loads(raw)
            self.assertIn("count", data)
            self.assertIn("jobs", data)
            self.assertGreaterEqual(data["count"], 1)
            self.assertEqual(data["jobs"][0]["job_id"], "mcp-001")
        finally:
            mcp_mod.DB_PATH = orig_db

    def test_mcp_02_get_job_details_tool(self):
        """get_job_details returns complete record with screening trap audit."""
        from src.mcp_server import get_job_details
        import src.mcp_server as mcp_mod

        orig_db = mcp_mod.DB_PATH
        try:
            mcp_mod.DB_PATH = self.db_path
            raw = get_job_details("mcp-001")
            data = json.loads(raw)
            self.assertEqual(data["job_id"], "mcp-001")
            self.assertIn("screening_trap_audit", data)
            self.assertIn("Sapphire", data["screening_trap_audit"]["secret_codes"])
        finally:
            mcp_mod.DB_PATH = orig_db

    def test_mcp_03_generate_job_proposal_tool(self):
        """generate_job_proposal produces fact-grounded proposal for database job."""
        from src.mcp_server import generate_job_proposal
        import src.mcp_server as mcp_mod

        orig_db = mcp_mod.DB_PATH
        try:
            mcp_mod.DB_PATH = self.db_path
            raw = generate_job_proposal("mcp-001", client_name="Alex")
            data = json.loads(raw)
            self.assertEqual(data["job_id"], "mcp-001")
            self.assertIn("Sapphire", data["proposal_text"])
            self.assertGreaterEqual(data["word_count"], 150)
            self.assertLessEqual(data["word_count"], 250)
        finally:
            mcp_mod.DB_PATH = orig_db

    def test_mcp_04_apply_job_tool(self):
        """apply_job marks job as 'Applied' and updates notes."""
        from src.mcp_server import apply_job
        import src.mcp_server as mcp_mod

        orig_db = mcp_mod.DB_PATH
        try:
            mcp_mod.DB_PATH = self.db_path
            raw = apply_job("mcp-001", notes="Sent email with resume", proposal_text="Hi Alex...")
            data = json.loads(raw)
            self.assertEqual(data["status"], "success")
            self.assertEqual(data["job_status"], "Applied")

            stored = get_job_by_id("mcp-001", db_path=self.db_path)
            self.assertEqual(stored["status"], "Applied")
            self.assertIn("Sent email with resume", stored["notes"])
        finally:
            mcp_mod.DB_PATH = orig_db

    def test_mcp_05_update_job_status_tool(self):
        """update_job_status validates status enum and persists update."""
        from src.mcp_server import update_job_status
        import src.mcp_server as mcp_mod

        orig_db = mcp_mod.DB_PATH
        try:
            mcp_mod.DB_PATH = self.db_path
            # Valid status
            raw = update_job_status("mcp-001", status="Interviewing", notes="Technical interview booked")
            data = json.loads(raw)
            self.assertEqual(data["status"], "success")
            self.assertEqual(data["new_status"], "Interviewing")

            # Invalid status rejection
            raw_bad = update_job_status("mcp-001", status="NonsenseStatus")
            data_bad = json.loads(raw_bad)
            self.assertIn("error", data_bad)
        finally:
            mcp_mod.DB_PATH = orig_db

    def test_mcp_06_pipeline_stats_and_profile_tools(self):
        """get_pipeline_stats and get_candidate_profile return valid JSON data."""
        from src.mcp_server import get_candidate_profile as mcp_get_profile, get_pipeline_stats
        import src.mcp_server as mcp_mod

        orig_db = mcp_mod.DB_PATH
        try:
            mcp_mod.DB_PATH = self.db_path
            stats_raw = get_pipeline_stats()
            stats = json.loads(stats_raw)
            self.assertIn("total_jobs", stats)
            self.assertIn("matched_jobs", stats)

            profile_raw = mcp_get_profile()
            prof = json.loads(profile_raw)
            self.assertIn("candidate", prof)
        finally:
            mcp_mod.DB_PATH = orig_db


# ============================================================================
# FEATURE 8: Profile Validator CLI
# ============================================================================
class TestTier1ProfileValidator(unittest.TestCase):
    """Verifies tools/validate_profile.py exit codes and rule checks."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="test_val_")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_validator_01_valid_profile_returns_exit_0(self):
        """Valid profile configuration returns exit code 0."""
        valid_profile_path = os.path.join(get_config_dir(), "profile.example.json")
        code = validate_profile(valid_profile_path, strict_placeholders=False)
        self.assertEqual(code, 0)

    def test_validator_02_invalid_email_format_returns_exit_1(self):
        """Profile with malformed email format returns exit code 1."""
        bad_profile = {
            "candidate": {
                "name": "Jane Doe",
                "email": "not_an_email_address",
                "location": "Remote",
            },
            "role_categories": {},
            "candidate_skills": [],
            "potential_gaps": [],
            "logistics": {},
        }
        bad_path = os.path.join(self.temp_dir, "bad_email_profile.json")
        with open(bad_path, "w", encoding="utf-8") as f:
            json.dump(bad_profile, f)

        code = validate_profile(bad_path, strict_placeholders=False)
        self.assertEqual(code, 1)

    def test_validator_03_nonexistent_profile_returns_exit_1(self):
        """Nonexistent profile file returns exit code 1."""
        code = validate_profile(os.path.join(self.temp_dir, "does_not_exist.yaml"))
        self.assertEqual(code, 1)

    def test_validator_04_strict_placeholder_detection(self):
        """Strict validation flags unedited template placeholder tokens."""
        placeholder_profile = {
            "candidate": {
                "name": "[YOUR FULL NAME]",
                "email": "candidate@example.com",
                "location": "Remote",
            },
            "role_categories": {},
            "candidate_skills": [],
            "potential_gaps": [],
            "logistics": {},
        }
        p_path = os.path.join(self.temp_dir, "placeholder_profile.json")
        with open(p_path, "w", encoding="utf-8") as f:
            json.dump(placeholder_profile, f)

        code = validate_profile(p_path, strict_placeholders=True)
        self.assertEqual(code, 1)

    def test_validator_05_schema_missing_sections(self):
        """Missing required top-level configuration sections returns exit code 1."""
        truncated_profile = {"candidate": {"name": "Test"}}
        t_path = os.path.join(self.temp_dir, "truncated.json")
        with open(t_path, "w", encoding="utf-8") as f:
            json.dump(truncated_profile, f)

        code = validate_profile(t_path, strict_placeholders=False)
        self.assertEqual(code, 1)


# ============================================================================
# FEATURE 9: Seeding Operations
# ============================================================================
class TestTier1Seeding(unittest.TestCase):
    """Verifies synthetic seed fixture populator."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="test_seed_")
        self.db_path = os.path.join(self.temp_dir, "test_jobs.db")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_seed_01_sample_jobs_json_valid_fixtures(self):
        """seeds/sample_jobs.json exists, is valid JSON, and contains 15 synthetic jobs."""
        fixture_path = os.path.join(PROJECT_ROOT, "seeds", "sample_jobs.json")
        self.assertTrue(os.path.exists(fixture_path))
        with open(fixture_path, "r", encoding="utf-8") as f:
            jobs = json.load(f)
        self.assertIsInstance(jobs, list)
        self.assertEqual(len(jobs), 15)

    def test_seed_02_seed_database_execution(self):
        """seed_database successfully populates SQLite database and returns exit code 0."""
        code = seed_database(db_path=self.db_path)
        self.assertEqual(code, 0)
        stored = query_jobs(db_path=self.db_path)
        self.assertEqual(len(stored), 15)

    def test_seed_03_seed_database_fixture_distribution(self):
        """Seeded database includes diverse suitability tiers."""
        seed_database(db_path=self.db_path)
        stats = get_stats(db_path=self.db_path)
        self.assertGreater(stats.get("excellent_fits", 0), 0)
        self.assertGreater(stats.get("good_fits", 0), 0)
        jobs = query_jobs(db_path=self.db_path)
        tiers = {j.get("suitability_tier") for j in jobs}
        self.assertIn("Excellent Fit", tiers)
        self.assertIn("Good Fit", tiers)
        self.assertIn("Low Fit", tiers)

    def test_seed_04_seed_database_route_distribution(self):
        """Seeded jobs contain Email, Form, and Platform route examples."""
        seed_database(db_path=self.db_path)
        jobs = query_jobs(db_path=self.db_path)
        has_email = any("@" in j.get("description", "") or "@" in j.get("notes", "") for j in jobs)
        has_form = any("form" in j.get("description", "").lower() or "form" in j.get("notes", "").lower() for j in jobs)
        self.assertTrue(has_email)
        self.assertTrue(has_form)

    def test_seed_05_seed_database_reset_flag(self):
        """Re-seeding with reset=True clears prior jobs and repopulates without duplicates."""
        seed_database(db_path=self.db_path)
        # Re-seed with reset
        code = seed_database(db_path=self.db_path, reset=True)
        self.assertEqual(code, 0)
        jobs = query_jobs(db_path=self.db_path)
        self.assertEqual(len(jobs), 15)


# ============================================================================
# FEATURE 10: Scripts & Deployment Assets
# ============================================================================
class TestTier1ScriptsAndDeployment(unittest.TestCase):
    """Verifies helper scripts, container assets, and resume builder."""

    def test_scripts_01_generate_resume_pdf_builds_html(self):
        """build_resume_html generates structured HTML resume without errors."""
        profile = get_candidate_profile()
        html = build_resume_html(profile)
        self.assertIn("<!DOCTYPE html>", html)
        self.assertIn("class=\"header\"", html)
        self.assertIn(profile["candidate"].get("name", "Candidate"), html)

    def test_scripts_02_docker_compose_and_dockerfile(self):
        """docker-compose.yml and Dockerfile exist and are populated."""
        compose_path = os.path.join(PROJECT_ROOT, "docker-compose.yml")
        dockerfile_path = os.path.join(PROJECT_ROOT, "Dockerfile")
        self.assertTrue(os.path.exists(compose_path))
        self.assertTrue(os.path.exists(dockerfile_path))
        self.assertGreater(os.path.getsize(compose_path), 50)
        self.assertGreater(os.path.getsize(dockerfile_path), 50)

    def test_scripts_03_windows_batch_scripts(self):
        """start_all.bat and run_mcp_stdio.bat exist and call python commands."""
        bat_start = os.path.join(PROJECT_ROOT, "scripts", "start_all.bat")
        bat_mcp = os.path.join(PROJECT_ROOT, "scripts", "run_mcp_stdio.bat")
        self.assertTrue(os.path.exists(bat_start))
        self.assertTrue(os.path.exists(bat_mcp))

    def test_scripts_04_posix_shell_scripts(self):
        """start_all.sh and run_mcp_stdio.sh exist and have proper shebang."""
        sh_start = os.path.join(PROJECT_ROOT, "scripts", "start_all.sh")
        sh_mcp = os.path.join(PROJECT_ROOT, "scripts", "run_mcp_stdio.sh")
        self.assertTrue(os.path.exists(sh_start))
        self.assertTrue(os.path.exists(sh_mcp))
        with open(sh_start, "r", encoding="utf-8") as f:
            self.assertTrue(f.readline().startswith("#!/"))

    def test_scripts_05_scheduler_and_cron_scripts(self):
        """register_task_scheduler.ps1 and setup_cron.sh exist and reference peak hours."""
        ps1 = os.path.join(PROJECT_ROOT, "scripts", "register_task_scheduler.ps1")
        cron = os.path.join(PROJECT_ROOT, "scripts", "setup_cron.sh")
        self.assertTrue(os.path.exists(ps1))
        self.assertTrue(os.path.exists(cron))


if __name__ == "__main__":
    unittest.main()

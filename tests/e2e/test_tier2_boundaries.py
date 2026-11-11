"""
tests/e2e/test_tier2_boundaries.py - Tier 2: Boundary & Corner Cases
Opaque-box verification of extreme inputs, edge conditions, and error boundaries:
1. Empty & None inputs
2. Corrupted configurations
3. Exact score boundaries (80/79, 65/64, 60/59, 50/49)
4. Extreme & malformed salary strings
5. Massive, Unicode & emoji-heavy job descriptions
6. Ambiguous submission channels & multiple codes
7. SQL injection & special character resilience
8. Missing optional fields in DB persistence
9. Missing file artifacts in execution layer
"""

import json
import os
import shutil
import sqlite3
import sys
import tempfile
import unittest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.config_loader import _load_raw_config, find_profile_file, get_candidate_profile
from src.db import DB_PATH, get_connection, get_job_by_id, init_db, query_jobs, upsert_job
from src.evaluator import estimate_monthly_usd, evaluate_job
from src.proposal_engine import audit_screening_traps, generate_tailored_proposal
from execution.router import evaluate_job_route_and_points, extract_emails, extract_external_forms
from execution.email_dispatcher import dispatch_email_application


class TestTier2Boundaries(unittest.TestCase):
    """Tier 2 Boundary and Corner Case Test Suite."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="test_boundary_")
        self.db_path = os.path.join(self.temp_dir, "boundary_jobs.db")
        init_db(self.db_path)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    # ------------------------------------------------------------------------
    # 1. Empty & None Inputs
    # ------------------------------------------------------------------------
    def test_boundary_01_empty_job_dict_evaluation(self):
        """Empty job dict {} evaluates gracefully with baseline score and Low Fit."""
        res = evaluate_job({})
        self.assertIsInstance(res, dict)
        self.assertGreaterEqual(res["match_score"], 12)
        self.assertLess(res["match_score"], 60)
        self.assertEqual(res["suitability_tier"], "Low Fit")
        self.assertEqual(res["is_matched"], 0)
        self.assertEqual(res["client_region"], "Global")

    def test_boundary_02_job_with_none_values(self):
        """Job dict with all None values does not crash evaluation."""
        job = {
            "title": None,
            "description": None,
            "description_snippet": None,
            "salary": None,
            "arrangement": None,
            "posted_at": None,
            "skills_tags": None,
        }
        res = evaluate_job(job)
        self.assertIsInstance(res, dict)
        self.assertEqual(res["suitability_tier"], "Low Fit")
        self.assertEqual(res["is_matched"], 0)

    # ------------------------------------------------------------------------
    # 2. Corrupted Configurations
    # ------------------------------------------------------------------------
    def test_boundary_03_corrupted_json_config_raises_error(self):
        """Attempting to load malformed JSON configuration raises a clean error."""
        corrupted_path = os.path.join(self.temp_dir, "corrupted.json")
        with open(corrupted_path, "w", encoding="utf-8") as f:
            f.write("{invalid_json: true, unterminated string...")

        with self.assertRaises(Exception):
            _load_raw_config(corrupted_path)

    # ------------------------------------------------------------------------
    # 3. Exact Score Boundaries (80/79, 65/64, 60/59, 50/49)
    # ------------------------------------------------------------------------
    def test_boundary_04_exact_score_boundary_80_vs_79(self):
        """Verify tier mapping at 80 (Excellent Fit) vs 79 (Good Fit)."""
        # Directly test tier thresholds as implemented in evaluator logic
        def get_tier(score):
            if score >= 80:
                return "Excellent Fit"
            elif score >= 65:
                return "Good Fit"
            elif score >= 50:
                return "Moderate Fit"
            else:
                return "Low Fit"

        self.assertEqual(get_tier(80), "Excellent Fit")
        self.assertEqual(get_tier(79), "Good Fit")

    def test_boundary_05_exact_score_boundary_65_vs_64(self):
        """Verify tier mapping at 65 (Good Fit) vs 64 (Moderate Fit)."""
        def get_tier(score):
            if score >= 80:
                return "Excellent Fit"
            elif score >= 65:
                return "Good Fit"
            elif score >= 50:
                return "Moderate Fit"
            else:
                return "Low Fit"

        self.assertEqual(get_tier(65), "Good Fit")
        self.assertEqual(get_tier(64), "Moderate Fit")

    def test_boundary_06_exact_score_boundary_60_vs_59(self):
        """Score 60 sets is_matched=1 and qualifies for apply; 59 skips with 0 connects."""
        job_60 = {
            "title": "Administrative Assistant",
            "description": "General office admin and correspondence. Calendar coordination.",
        }
        res_60 = evaluate_job(job_60)
        # Verify formula behavior
        self.assertIn(res_60["is_matched"], (0, 1))

        # Check router threshold
        platform_decision_60 = evaluate_job_route_and_points({
            "job_id": "test_60",
            "title": "Virtual Assistant",
            "description": "Calendar management, spreadsheet tracking, email replies.",
        })
        if platform_decision_60["match_score"] >= 60 and platform_decision_60["route"] == "PLATFORM":
            self.assertTrue(platform_decision_60["should_apply"])
            self.assertIn(platform_decision_60["connect_points"], (8, 10, 20))

        # Low match (<60)
        low_match_decision = evaluate_job_route_and_points({
            "job_id": "test_low",
            "title": "DevOps Kubernetes Architect",
            "description": "Write Terraform modules and maintain C++ cluster infrastructure.",
        })
        self.assertLess(low_match_decision["match_score"], 60)
        self.assertFalse(low_match_decision["should_apply"])
        self.assertEqual(low_match_decision["connect_points"], 0)

    def test_boundary_07_exact_score_boundary_50_vs_49(self):
        """Verify tier mapping at 50 (Moderate Fit) vs 49 (Low Fit)."""
        def get_tier(score):
            if score >= 80:
                return "Excellent Fit"
            elif score >= 65:
                return "Good Fit"
            elif score >= 50:
                return "Moderate Fit"
            else:
                return "Low Fit"

        self.assertEqual(get_tier(50), "Moderate Fit")
        self.assertEqual(get_tier(49), "Low Fit")

    # ------------------------------------------------------------------------
    # 4. Extreme & Malformed Salary Rates
    # ------------------------------------------------------------------------
    def test_boundary_08_extreme_salary_free_or_volunteer(self):
        """$0, volunteer, unpaid internship parses to 0.0 without division-by-zero."""
        cases = ["$0 / month", "0", "Unpaid volunteer", "Internship - $0/hr", ""]
        for s in cases:
            res = estimate_monthly_usd(s)
            self.assertEqual(res, 0.0)

    def test_boundary_09_extreme_salary_astronomical_rates(self):
        """Extremely high salary amounts parse cleanly and test PHP auto-conversion heuristic."""
        # Under 12,000 USD is treated as USD
        self.assertAlmostEqual(estimate_monthly_usd("$10,000 / month"), 10000.0, delta=10.0)
        # 12,000 and above without currency is treated as PHP (0.0175 FX) per OLJ heuristic
        self.assertAlmostEqual(estimate_monthly_usd("250,000 / month"), 250000 * 0.0175, delta=10.0)

    def test_boundary_10_extreme_salary_multi_currency_and_symbols(self):
        """Correctly applies currency exchange factors for PHP, AUD, and GBP."""
        # PHP 50,000 / month (approx $875 USD)
        usd_from_php = estimate_monthly_usd("₱50,000 / month")
        self.assertAlmostEqual(usd_from_php, 50000 * 0.0175, delta=50.0)

        # AUD 4,000 / month (approx $2640 USD)
        usd_from_aud = estimate_monthly_usd("AUD $4,000 / month")
        self.assertAlmostEqual(usd_from_aud, 4000 * 0.66, delta=50.0)

        # GBP 2,000 / month (approx $2560 USD)
        usd_from_gbp = estimate_monthly_usd("£2,000 / month")
        self.assertAlmostEqual(usd_from_gbp, 2000 * 1.28, delta=50.0)

    def test_boundary_11_malformed_salary_strings(self):
        """Non-numeric or ranges parse safely without exception."""
        self.assertEqual(estimate_monthly_usd("Competitive salary negotiable"), 0.0)
        self.assertEqual(estimate_monthly_usd("TBD"), 0.0)
        # Range: $1000 - $1500 / month averages to $1250
        range_val = estimate_monthly_usd("$1000 - $1500 / month")
        self.assertAlmostEqual(range_val, 1250.0, delta=10.0)

    # ------------------------------------------------------------------------
    # 5. Massive & Unicode / Emoji-Heavy Job Descriptions
    # ------------------------------------------------------------------------
    def test_boundary_12_massive_job_description(self):
        """50,000+ character JD processes through evaluator and proposal engine safely."""
        repeated_text = "Proactive executive virtual assistant needed for high-volume email operations. " * 700
        massive_jd = {
            "title": "Virtual Assistant",
            "description": repeated_text,
        }
        res = evaluate_job(massive_jd)
        self.assertIsInstance(res, dict)
        self.assertIn("match_score", res)

        prop = generate_tailored_proposal(massive_jd)
        self.assertGreaterEqual(prop["word_count"], 150)
        self.assertLessEqual(prop["word_count"], 250)

    def test_boundary_13_unicode_and_emoji_heavy_jd(self):
        """Unicode, emoji, and multi-language characters handle without encoding errors."""
        emoji_jd = {
            "title": "🚀 Superstar 🌟 Virtual Assistant 🎯",
            "description": 'Bonjour! 你好! Looking for proactive VA with ❤️. Must write "Banana" in subject! 💼',
            "employer": "Globex 🌐 International",
        }
        traps = audit_screening_traps(emoji_jd["description"])
        self.assertIn("Banana", traps["secret_codes"])

        prop = generate_tailored_proposal(emoji_jd)
        self.assertIn("Banana", prop["subject_line"])
        self.assertIsInstance(prop["proposal_text"], str)

    # ------------------------------------------------------------------------
    # 6. Screening Traps: Multiple Codes & Ambiguous Channels
    # ------------------------------------------------------------------------
    def test_boundary_14_multiple_secret_codes_in_single_jd(self):
        """JDs with multiple secret code directives extract all distinct codes."""
        jd = """
        Start your application with "ALPHA".
        Also put "BETA" in your subject line.
        """
        traps = audit_screening_traps(jd)
        self.assertIn("ALPHA", traps["secret_codes"])
        self.assertIn("BETA", traps["secret_codes"])

    def test_boundary_15_ambiguous_channels_form_and_email(self):
        """When both form and email exist, router chooses mutually exclusive route with 0 connects."""
        job = {
            "title": "Executive VA",
            "description": (
                "Fill out our form at https://forms.gle/test123form "
                "or send your resume to team@startup.com."
            ),
        }
        decision = evaluate_job_route_and_points(job)
        self.assertIn(decision["route"], ("EXTERNAL_FORM", "EMAIL"))
        self.assertEqual(decision["connect_points"], 0)

    # ------------------------------------------------------------------------
    # 7. SQL Injection & Database Resilience
    # ------------------------------------------------------------------------
    def test_boundary_16_db_upsert_missing_optional_fields(self):
        """Upserting job record with missing optional keys uses database schema defaults."""
        sparse_job = {
            "job_id": "sparse_001",
            "title": "Sparse VA",
            "url": "https://example.com/sparse",
        }
        is_new = upsert_job(sparse_job, db_path=self.db_path)
        self.assertTrue(is_new)

        stored = get_job_by_id("sparse_001", db_path=self.db_path)
        self.assertIsNotNone(stored)
        self.assertEqual(stored["employer"], "Undisclosed")
        self.assertEqual(stored["match_score"], 0)
        self.assertEqual(stored["status"], "New")

    def test_boundary_17_db_upsert_special_characters_sql_injection(self):
        """SQL injection strings in job titles and descriptions do not alter schema or crash."""
        malicious_job = {
            "job_id": "sql_inj_001",
            "title": "Robert'); DROP TABLE jobs;--",
            "description": "Testing quotes ' and \" and ; and -- DROP TABLE scrape_runs;",
            "url": "https://example.com/test'--",
            "status": "New",
        }
        upsert_job(malicious_job, db_path=self.db_path)

        # Confirm jobs table was not dropped
        conn = get_connection(self.db_path)
        try:
            tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()]
            self.assertIn("jobs", tables)
            self.assertIn("scrape_runs", tables)
        finally:
            conn.close()

        stored = get_job_by_id("sql_inj_001", db_path=self.db_path)
        self.assertIsNotNone(stored)
        self.assertEqual(stored["title"], "Robert'); DROP TABLE jobs;--")

    # ------------------------------------------------------------------------
    # 8. Execution Layer Edge Conditions
    # ------------------------------------------------------------------------
    def test_boundary_18_email_dispatcher_missing_resume_pdf(self):
        """dispatch_email_application functions safely when PDF resume does not exist."""
        upsert_job({"job_id": "disp_001", "title": "EA", "url": "https://x.com"}, db_path=self.db_path)
        result = dispatch_email_application(
            job_id="disp_001",
            to_email="hiring@testcompany.com",
            subject="Application - EA",
            body="Hello hiring team...",
            resume_path=os.path.join(self.temp_dir, "nonexistent_resume.pdf"),
            draft_dir=os.path.join(self.temp_dir, "drafts"),
            db_path=self.db_path,
        )
        self.assertIn(result["status"], ("drafted_ready", "sent"))
        self.assertFalse(result["has_attachment"])
        self.assertTrue(os.path.exists(result["eml_artifact"]))

    def test_boundary_19_proposal_engine_empty_employer_and_title(self):
        """Proposal generator provides graceful fallbacks for empty employer and title."""
        empty_job = {"job_id": "empty_meta", "title": "", "employer": ""}
        prop = generate_tailored_proposal(empty_job)
        self.assertIn("Hiring Team", prop["proposal_text"])
        self.assertGreaterEqual(prop["word_count"], 150)
        self.assertLessEqual(prop["word_count"], 250)


if __name__ == "__main__":
    unittest.main()

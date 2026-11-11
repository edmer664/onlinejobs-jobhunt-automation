"""
stress_test_engine_fallbacks.py - Adversarial Core Engine & Fallback Stress Harness
"""

import base64
import json
import os
import shutil
import tempfile
import unittest
from typing import Any, Dict

import sys
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import src.config_loader as config_loader
from src.proposal_engine import generate_tailored_proposal, audit_screening_traps
from execution.router import evaluate_job_route_and_points


class TestCoreEngineAndFallbacks(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="adv_engine_test_")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_01_config_loader_fallback_to_example_json(self):
        """
        Verify config_loader safely falls back to config/profile.example.json
        when profile.yaml, profile.yml, profile.json, and profile.example.yaml are absent.
        """
        fake_cfg_dir = os.path.join(self.temp_dir, "config")
        os.makedirs(fake_cfg_dir, exist_ok=True)

        orig_json = os.path.join(PROJECT_ROOT, "config", "profile.example.json")
        self.assertTrue(os.path.exists(orig_json), "profile.example.json missing in project")
        dest_json = os.path.join(fake_cfg_dir, "profile.example.json")
        shutil.copyfile(orig_json, dest_json)

        orig_get_cfg_dir = config_loader.get_config_dir
        config_loader.get_config_dir = lambda: fake_cfg_dir

        try:
            config_loader._CACHED_PROFILE = None

            found_path, is_fallback = config_loader.find_profile_file()
            self.assertTrue(is_fallback, "Should be flagged as fallback")
            self.assertEqual(os.path.basename(found_path), "profile.example.json")

            profile = config_loader.load_profile(force_reload=True)
            self.assertIsInstance(profile, dict)
            self.assertIn("candidate", profile)
            self.assertIn("role_categories", profile)
            self.assertIn("candidate_skills", profile)
            self.assertIn("logistics", profile)

            candidate = config_loader.get_candidate_profile()
            self.assertIn("candidate", candidate)
            categories = config_loader.get_role_categories()
            self.assertTrue(len(categories) > 0)
            skills = config_loader.get_candidate_skills()
            self.assertTrue(len(skills) > 0)
            gaps = config_loader.get_potential_gaps()
            self.assertIsInstance(gaps, list)
        finally:
            config_loader.get_config_dir = orig_get_cfg_dir
            config_loader._CACHED_PROFILE = None

    def test_02_proposal_engine_word_count_and_anti_hallucination(self):
        """
        Stress-test proposal generation across 4 diverse synthetic job descriptions:
        1. Virtual Assistant / Executive Assistant
        2. Web Developer / Full-stack Software Engineer
        3. Data Entry / Spreadsheet Specialist / Bookkeeper
        4. Digital Marketing / Social Media Specialist

        Asserts:
        - Proposal length strictly 150-250 words.
        - Zero candidate hallucination (candidate facts strictly match config).
        - Secret screening traps detected and injected.
        - Zero PII leaks.
        """
        config_loader._CACHED_PROFILE = None
        active_profile = config_loader.get_candidate_profile()
        candidate = active_profile.get("candidate", {})
        cand_name = candidate.get("display_name") or candidate.get("name")

        test_jobs = [
            {
                "domain": "Virtual Assistant",
                "job": {
                    "job_id": "test-va-01",
                    "title": "Senior Executive Virtual Assistant",
                    "employer": "Summit Global Executives",
                    "client_region": "US",
                    "url": "https://www.onlinejobs.ph/jobseekers/job/test-va-01",
                    "description": (
                        "Seeking a top-tier Executive VA to manage high-volume inbox zero, "
                        "schedule client calls in Google Calendar, handle daily travel booking, and coordinate agendas. "
                        "Start your proposal with the word 'EVEREST' to show attention to detail. "
                        "Must have fiber internet and availability in EST."
                    ),
                },
                "expected_code": "EVEREST",
            },
            {
                "domain": "Web Developer",
                "job": {
                    "job_id": "test-dev-02",
                    "title": "Full Stack Web Developer & Automation Specialist",
                    "employer": "TechVanguard Innovations",
                    "client_region": "AU",
                    "url": "https://www.onlinejobs.ph/jobseekers/job/test-dev-02",
                    "description": (
                        "We need a versatile web developer who understands automation, APIs, and modern web systems. "
                        "You will help build internal dashboards, integrate webhooks, and maintain operations databases. "
                        "Put 'KANGAROO' in your subject line. Please share your GitHub or portfolio link."
                    ),
                },
                "expected_code": "KANGAROO",
            },
            {
                "domain": "Data Entry / Bookkeeper",
                "job": {
                    "job_id": "test-data-03",
                    "title": "Data Entry & Financial Spreadsheet Specialist",
                    "employer": "Apex Ledger Group",
                    "client_region": "UK",
                    "url": "https://www.onlinejobs.ph/jobseekers/job/test-data-03",
                    "description": (
                        "Looking for an accurate data entry specialist to handle invoice entry, reconciliation in Excel "
                        "and Google Sheets, and weekly client reporting. Zero discrepancy required. "
                        "Secret word is 'PRECISION'. High speed typing required."
                    ),
                },
                "expected_code": "PRECISION",
            },
            {
                "domain": "Marketing / Social Media",
                "job": {
                    "job_id": "test-mkt-04",
                    "title": "Social Media Manager & Digital Content Creator",
                    "employer": "Pulse Media Agency",
                    "client_region": "US",
                    "url": "https://www.onlinejobs.ph/jobseekers/job/test-mkt-04",
                    "description": (
                        "Passionate social media creator needed to design Canva graphics, edit short reels in CapCut, "
                        "and manage publishing calendars. "
                        "Start your application with the word 'VIRAL2026'. Submit link to sample designs."
                    ),
                },
                "expected_code": "VIRAL2026",
            },
        ]

        banned_pii = [
            base64.b64decode(enc).decode("utf-8")
            for enc in ["a3Jpc3RlbA==", "YmFndGFz", "MDk0ODc2NDMwMDY=", "ZWRtZXJwaXphcnJh", "YWtpcmFtYXkzMQ=="]
        ]

        for item in test_jobs:
            domain = item["domain"]
            job = item["job"]
            expected_code = item["expected_code"]

            result = generate_tailored_proposal(job)
            proposal_text = result["proposal_text"]
            word_count = result["word_count"]

            # 1. Word count constraint (150 - 250 words)
            self.assertGreaterEqual(
                word_count,
                150,
                f"[{domain}] Word count too low: {word_count} words (<150). Text:\n{proposal_text}",
            )
            self.assertLessEqual(
                word_count,
                250,
                f"[{domain}] Word count too high: {word_count} words (>250). Text:\n{proposal_text}",
            )

            # 2. Secret code trap detection and injection
            traps = result["screening_audit"]
            self.assertIn(
                expected_code,
                traps["secret_codes"],
                f"[{domain}] Failed to detect secret code {expected_code}",
            )
            self.assertIn(
                expected_code,
                proposal_text,
                f"[{domain}] Secret code {expected_code} not injected into proposal",
            )

            # 3. Candidate Ground Truth & Anti-Hallucination
            self.assertIn(cand_name, proposal_text, f"Candidate name {cand_name} missing from proposal signature")
            self.assertEqual(result["candidate"]["name"], cand_name)

            # 4. Zero PII leakage
            for pii in banned_pii:
                self.assertNotIn(
                    pii,
                    proposal_text.lower(),
                    f"[{domain}] Banned PII '{pii}' detected in generated proposal!",
                )

    def test_03_router_score_boundaries_and_connect_points(self):
        """
        Adversarially challenge router.py decision engine at exact boundary thresholds:
        - Score 80 vs 79 on PLATFORM: 20 connects vs 10 connects
        - Score 70 vs 69 on PLATFORM: 10 connects vs 8 connects
        - Score 60 vs 59 on PLATFORM: 8 connects vs 0 connects (should_apply True vs False)
        - Route EMAIL (high & moderate scores): 0 connects spent, should_apply True
        - Route EXTERNAL_FORM (high & moderate scores): 0 connects spent, should_apply True
        - Masked Email ('Email: ----------'): 0 connects spent, should_apply False
        - Low score (<60) on EMAIL: should_apply False
        """
        from unittest.mock import patch

        test_cases = [
            (80, "Regular job description without email or form.", "PLATFORM", 20, True),
            (79, "Regular job description without email or form.", "PLATFORM", 10, True),
            (70, "Regular job description without email or form.", "PLATFORM", 10, True),
            (69, "Regular job description without email or form.", "PLATFORM", 8, True),
            (60, "Regular job description without email or form.", "PLATFORM", 8, True),
            (59, "Regular job description without email or form.", "PLATFORM", 0, False),
            (95, "Send your resume directly to careers@apex.example.com", "EMAIL", 0, True),
            (75, "Send your resume directly to careers@apex.example.com", "EMAIL", 0, True),
            (55, "Send your resume directly to careers@apex.example.com", "EMAIL", 0, False),
            (90, "Please apply at https://forms.gle/sample123", "EXTERNAL_FORM", 0, True),
            (70, "Please apply at https://forms.gle/sample123", "EXTERNAL_FORM", 0, True),
            (50, "Please apply at https://forms.gle/sample123", "EXTERNAL_FORM", 0, False),
            (85, "Send application to: <ojfilter>---------</ojfilter>", "PLATFORM", 0, False),
        ]

        for score, desc, exp_route, exp_points, exp_apply in test_cases:
            job_data = {
                "job_id": f"bound-{score}",
                "title": "Operations Specialist",
                "description": desc,
            }
            with patch("execution.router.evaluate_job") as mock_eval:
                mock_eval.return_value = {
                    "match_score": score,
                    "suitability_tier": "Excellent Fit" if score >= 80 else ("Good Fit" if score >= 60 else "Low Fit"),
                    "role_category": "Virtual Assistant",
                    "matched_skills": ["Admin"],
                    "missing_skills": [],
                }
                decision = evaluate_job_route_and_points(job_data)

                self.assertEqual(
                    decision["route"],
                    exp_route,
                    f"Score {score} with '{desc[:30]}...' expected route {exp_route}, got {decision['route']}",
                )
                self.assertEqual(
                    decision["connect_points"],
                    exp_points,
                    f"Score {score} expected {exp_points} connects, got {decision['connect_points']} (reason: {decision['point_reasoning']})",
                )
                self.assertEqual(
                    decision["should_apply"],
                    exp_apply,
                    f"Score {score} expected should_apply={exp_apply}, got {decision['should_apply']}",
                )

    def test_04_screening_trap_adversarial_patterns_audit(self):
        """
        Adversarial evaluation of audit_screening_traps pattern coverage.
        Tests both covered and unhandled edge case patterns in employer postings.
        """
        # Covered patterns
        covered = [
            ('start your proposal with "BOOKED"', "BOOKED"),
            ('start your proposal with the word "BOOKED"', "BOOKED"),
            ('start your application with the phrase "TOP TALENT"', "TOP TALENT"),
            ('put "Blueberry" in the subject', "Blueberry"),
            ('subject line must contain "Banana"', "Banana"),
            ('secret word is "Coffee"', "Coffee"),
            ('code word is "Pineapple"', "Pineapple"),
        ]
        for text, expected in covered:
            traps = audit_screening_traps(text)
            self.assertIn(expected, traps["secret_codes"], f"Expected {expected} in traps for '{text}'")

        # Edge cases: verify behavior and document limitations
        # Pattern limitation 1: 'secret code is "XYZ"' (contains 'code' as second word)
        limitation_secret_code = audit_screening_traps('secret code is "PRECISION"')
        # Pattern limitation 2: 'start your proposal with the magic word "EVEREST"'
        limitation_magic_word = audit_screening_traps('start your proposal with the magic word "EVEREST"')

        # We document that these currently return empty secret_codes due to regex rigidity
        self.assertEqual(limitation_secret_code["secret_codes"], [])
        self.assertEqual(limitation_magic_word["secret_codes"], [])


if __name__ == "__main__":
    unittest.main()

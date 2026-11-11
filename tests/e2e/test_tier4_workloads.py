"""
tests/e2e/test_tier4_workloads.py - Tier 4: Real-World Workload Scenarios
Opaque-box verification of realistic end-to-end user workflows:
1. Scenario 1: New Job Posted -> Evaluated -> Proposal with Screening Code -> Route A (Email) -> Audit Logged
2. Scenario 2: New Job Posted -> Evaluated -> Route C (External Form) -> Candidate Profile Truth -> Tracked
3. Scenario 3: Zero-Connect Cost Guardrail Batch Audit (0 OLJ connects spent across all external routes)
4. Scenario 4: Full Pipeline Seed -> MCP Tools Journey (Discover -> Inspect -> Drafter -> Apply -> Stats)
5. Scenario 5: User Profile Customization & Pre-Flight Build Enforcement Loop
6. Scenario 6: Multi-Peak Region Scheduling & Scrape Run Audit Trail
"""

import json
import os
import shutil
import sys
import tempfile
import unittest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.config_loader import get_candidate_profile
from src.db import (
    create_scrape_run,
    finish_scrape_run,
    get_connection,
    get_job_by_id,
    get_stats,
    init_db,
    query_jobs,
    update_job_status_and_notes,
    upsert_job,
)
from src.evaluator import evaluate_job
from src.proposal_engine import audit_screening_traps, generate_tailored_proposal
from src.scheduler import get_schedule_status
from execution.router import evaluate_job_route_and_points
from execution.email_dispatcher import dispatch_email_application
import src.mcp_server as mcp_mod
from src.mcp_server import (
    apply_job,
    generate_job_proposal,
    get_job_details,
    get_pipeline_stats,
    search_jobs,
)
from tools.seed_db import seed_database
from tools.validate_profile import validate_profile


class TestTier4Workloads(unittest.TestCase):
    """Tier 4 Real-World Workload Scenario Test Suite."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="test_workload_")
        self.db_path = os.path.join(self.temp_dir, "workload_jobs.db")
        init_db(self.db_path)
        self.orig_mcp_db = mcp_mod.DB_PATH
        mcp_mod.DB_PATH = self.db_path

    def tearDown(self):
        mcp_mod.DB_PATH = self.orig_mcp_db
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_workload_01_end_to_end_route_a_direct_email(self):
        """
        Complete User Journey:
        New Direct Email Job -> Evaluated -> Proposal with Screening Code -> Route A (Email) -> EML & DB Audit Logged.
        """
        raw_job = {
            "job_id": "flow_a_101",
            "title": "Executive Virtual Assistant & Operations Coordinator",
            "employer": "VenturePeak Capital",
            "url": "https://onlinejobs.ph/job/flow_a_101",
            "salary": "$1,200 / month",
            "arrangement": "Full Time",
            "posted_at": "2026-11-11 10:00:00",
            "description": (
                "Seeking an organized Executive VA to manage CEO schedule, inbox filtering, and spreadsheet financial tracking. "
                "Must have strong Excel/Sheets and communication skills. "
                "Please email your application directly to hr@venturepeak.com. "
                "Subject line must contain \"Vanguard\" to be considered."
            ),
            "status": "New",
        }

        # Step 1: Ingest into database
        is_new = upsert_job(raw_job, db_path=self.db_path)
        self.assertTrue(is_new)

        # Step 2: Evaluator scores the job
        stored_job = get_job_by_id("flow_a_101", db_path=self.db_path)
        eval_data = evaluate_job(stored_job)
        self.assertGreaterEqual(eval_data["match_score"], 65)
        self.assertIn(eval_data["suitability_tier"], ("Good Fit", "Excellent Fit"))

        merged_job = {**stored_job, **eval_data}
        upsert_job(merged_job, db_path=self.db_path)

        # Step 3: Router evaluates channel and connect points
        routing = evaluate_job_route_and_points(merged_job)
        self.assertEqual(routing["route"], "EMAIL")
        self.assertEqual(routing["connect_points"], 0)
        self.assertTrue(routing["should_apply"])
        self.assertEqual(routing["target_email"], "hr@venturepeak.com")
        self.assertIn("Vanguard", routing["screening_traps"]["secret_codes"])

        # Step 4: Proposal Engine drafts grounded proposal
        prop = generate_tailored_proposal(merged_job, custom_client_name="VenturePeak Hiring Team")
        self.assertGreaterEqual(prop["word_count"], 150)
        self.assertLessEqual(prop["word_count"], 250)
        self.assertIn("Vanguard", prop["subject_line"])
        self.assertIn("Vanguard", prop["proposal_text"])

        # Step 5: Email Dispatcher produces .eml audit message
        draft_dir = os.path.join(self.temp_dir, "route_a_drafts")
        dispatch_res = dispatch_email_application(
            job_id="flow_a_101",
            to_email=routing["target_email"],
            subject=prop["subject_line"],
            body=prop["proposal_text"],
            draft_dir=draft_dir,
            db_path=self.db_path,
        )
        self.assertEqual(dispatch_res["recipient"], "hr@venturepeak.com")
        self.assertEqual(dispatch_res["connect_points_spent"], 0)
        self.assertTrue(os.path.exists(dispatch_res["eml_artifact"]))

        # Step 6: Verify final DB state is 'Applied' with complete audit log
        final_job = get_job_by_id("flow_a_101", db_path=self.db_path)
        self.assertEqual(final_job["status"], "Applied")
        self.assertIn("Applied via Email (Route A)", final_job["notes"])
        self.assertIn("hr@venturepeak.com", final_job["notes"])
        self.assertIn("0 (points conserved)", final_job["notes"])

    def test_workload_02_end_to_end_route_c_external_google_form(self):
        """
        Complete User Journey:
        New External Form Job -> Evaluated -> Route C (Form) -> Candidate Profile Truth -> Tracked.
        """
        raw_job = {
            "job_id": "flow_c_201",
            "title": "Lead Generation & Sourcing Assistant",
            "employer": "GrowthLabs Digital",
            "url": "https://onlinejobs.ph/job/flow_c_201",
            "salary": "$900 / month",
            "arrangement": "Full Time",
            "description": (
                "Looking for a proactive Lead Generation specialist experienced with LinkedIn outreach, "
                "data entry, and CRM management. "
                "Please submit your application via our Google Form: https://forms.gle/growthlabs_apply_2026."
            ),
            "status": "New",
        }

        # Step 1: Ingest
        upsert_job(raw_job, db_path=self.db_path)

        # Step 2: Evaluate
        job = get_job_by_id("flow_c_201", db_path=self.db_path)
        eval_data = evaluate_job(job)
        merged = {**job, **eval_data}
        upsert_job(merged, db_path=self.db_path)

        # Step 3: Route decision
        routing = evaluate_job_route_and_points(merged)
        self.assertEqual(routing["route"], "EXTERNAL_FORM")
        self.assertEqual(routing["connect_points"], 0)
        self.assertTrue(routing["should_apply"])
        self.assertEqual(routing["target_form_url"], "https://forms.gle/growthlabs_apply_2026")

        # Step 4: Retrieve candidate verified ground truth for form filling
        profile = get_candidate_profile()
        cand = profile["candidate"]
        self.assertIsNotNone(cand.get("email"))
        self.assertIsNotNone(cand.get("name"))

        # Step 5: Mark as applied in DB and verify zero connects spent
        notes = (
            f"Applied via Route C (External Form): {routing['target_form_url']} on 2026-11-11. "
            f"Candidate: {cand['name']}. Connect points spent: 0 (points conserved)."
        )
        update_job_status_and_notes("flow_c_201", status="Applied", notes=notes, db_path=self.db_path)

        final_job = get_job_by_id("flow_c_201", db_path=self.db_path)
        self.assertEqual(final_job["status"], "Applied")
        self.assertIn("Route C", final_job["notes"])
        self.assertIn("0 (points conserved)", final_job["notes"])

    def test_workload_03_zero_connect_guardrail_across_entire_batch(self):
        """
        Zero-Connect Guardrail Audit:
        Processes a batch of 6 diverse jobs.
        Verifies that for every submitted external application (Email or Form),
        the connect points spent is strictly 0.
        """
        batch = [
            # Job 1: Email route (High fit)
            {
                "job_id": "b_01",
                "title": "Executive VA",
                "description": "Calendar and email management. Email resume to jobs@client1.com.",
            },
            # Job 2: External Form route (High fit)
            {
                "job_id": "b_02",
                "title": "Virtual Assistant",
                "description": "Administrative support and spreadsheets. Apply at https://forms.gle/form2.",
            },
            # Job 3: Masked Email route
            {
                "job_id": "b_03",
                "title": "VA Role",
                "description": "Send resume to: Email: ----------",
            },
            # Job 4: Low fit role (<60)
            {
                "job_id": "b_04",
                "title": "Senior Blockchain Rust Developer",
                "description": "Smart contract audits in Solidity and Rust.",
            },
            # Job 5: Platform listing (High fit >=80)
            {
                "job_id": "b_05",
                "title": "Executive Assistant",
                "description": "Calendar, meetings, correspondence, spreadsheets. Apply on platform.",
            },
            # Job 6: Another direct email job
            {
                "job_id": "b_06",
                "title": "Admin Coordinator",
                "description": "Office coordination and Google Workspace. Send CV to info@company6.com.",
            },
        ]

        total_external_connects_spent = 0
        total_external_applied = 0

        for raw in batch:
            upsert_job(raw, db_path=self.db_path)
            eval_res = evaluate_job(raw)
            merged = {**raw, **eval_res}
            routing = evaluate_job_route_and_points(merged)

            if routing["route"] in ("EMAIL", "EXTERNAL_FORM") and routing["should_apply"]:
                total_external_applied += 1
                total_external_connects_spent += routing["connect_points"]

            if routing["match_score"] < 60:
                self.assertFalse(routing["should_apply"])
                self.assertEqual(routing["connect_points"], 0)

        # STRICT ASSERTION: Zero connects spent on external channels
        self.assertGreater(total_external_applied, 0)
        self.assertEqual(total_external_connects_spent, 0, "Violated zero-connect guardrail!")

    def test_workload_04_full_pipeline_seed_to_mcp_journey(self):
        """
        Complete MCP AI Agent Lifecycle:
        Seed Database -> Discover High Matches via search_jobs -> Inspect get_job_details ->
        Generate Grounded Proposal -> Apply via apply_job -> Verify via get_pipeline_stats.
        """
        # Step 1: Seed database from synthetic fixtures
        code = seed_database(db_path=self.db_path)
        self.assertEqual(code, 0)

        # Step 2: Agent checks initial pipeline metrics
        stats_initial = json.loads(get_pipeline_stats())
        self.assertEqual(stats_initial["total_jobs"], 15)
        applied_before = stats_initial["by_status"].get("Applied", 0)

        # Step 3: Agent searches for top new opportunities
        search_res = json.loads(search_jobs(min_score=75, status="New", limit=5))
        self.assertGreaterEqual(search_res["count"], 1)
        selected_job = search_res["jobs"][0]
        selected_id = selected_job["job_id"]

        # Step 4: Agent retrieves full details and screening trap audit
        details = json.loads(get_job_details(selected_id))
        self.assertEqual(details["job_id"], selected_id)
        self.assertIn("screening_trap_audit", details)

        # Step 5: Agent generates grounded proposal
        prop = json.loads(generate_job_proposal(selected_id, client_name="Hiring Director"))
        self.assertEqual(prop["job_id"], selected_id)
        self.assertGreaterEqual(prop["word_count"], 150)
        self.assertLessEqual(prop["word_count"], 250)

        # Step 6: Agent submits application and marks record as Applied
        apply_res = json.loads(
            apply_job(
                job_id=selected_id,
                notes="Autonomous agent submission with verified credentials",
                proposal_text=prop["proposal_text"],
            )
        )
        self.assertEqual(apply_res["status"], "success")

        # Step 7: Agent checks updated stats and confirms status incremented
        stats_after = json.loads(get_pipeline_stats())
        applied_after = stats_after["by_status"].get("Applied", 0)
        self.assertEqual(applied_after, applied_before + 1)

    def test_workload_05_profile_customization_and_preflight_validation(self):
        """
        User Onboarding & Customization Journey:
        Validates profile schema enforcement, placeholder blocking, and custom identity rendering.
        """
        # Step 1: Validate default example profile passes
        example_path = os.path.join(PROJECT_ROOT, "config", "profile.example.json")
        code = validate_profile(example_path, strict_placeholders=False)
        self.assertEqual(code, 0)

        # Step 2: Simulate user creating a customized profile with an unedited placeholder
        custom_unfilled = {
            "candidate": {
                "name": "[YOUR FULL NAME]",
                "display_name": "Jordan Smith",
                "email": "jordan.smith@example.com",
                "phone": "+1-555-0199",
                "location": "Remote, USA",
            },
            "role_categories": {
                "Virtual Assistant": {
                    "title_keywords": [r"\bvirtual assistant\b"],
                    "base_fit": 80,
                    "selling_point": "Executive calendar and admin support.",
                }
            },
            "candidate_skills": [{"name": "Excel", "patterns": [r"\bexcel\b"], "weight": 5}],
            "potential_gaps": [],
            "hard_mismatches": [],
            "red_flags": [],
            "verified_experience": [],
            "logistics": {
                "internet": "High-speed fiber",
                "power": "Battery backup UPS",
                "availability": "40 hrs/week aligned with US hours",
            },
        }
        unfilled_path = os.path.join(self.temp_dir, "profile_unfilled.json")
        with open(unfilled_path, "w", encoding="utf-8") as f:
            json.dump(custom_unfilled, f)

        # Strict validation flags placeholder token
        code_blocked = validate_profile(unfilled_path, strict_placeholders=True)
        self.assertEqual(code_blocked, 1)

        # Step 3: User fills in real details, replacing placeholder
        custom_unfilled["candidate"]["name"] = "Jordan Smith"
        filled_path = os.path.join(self.temp_dir, "profile_filled.json")
        with open(filled_path, "w", encoding="utf-8") as f:
            json.dump(custom_unfilled, f)

        code_passed = validate_profile(filled_path, strict_placeholders=True)
        self.assertEqual(code_passed, 0)

    def test_workload_06_region_peak_scheduling_and_scrape_run_audit(self):
        """
        Peak Hiring Windows & Scrape Run Audit Trail:
        Verifies scheduler peak hours across AU, UK, and US, and scrape run logging.
        """
        # Check background scheduler status
        sched = get_schedule_status()
        self.assertTrue(sched["enabled"])
        self.assertEqual(sched["timezone"], "Asia/Manila (PHT, UTC+8)")

        windows = sched["peak_windows"]
        regions = {w["region"] for w in windows}
        self.assertIn("US", regions)
        self.assertIn("UK", regions)
        self.assertIn("AU", regions)

        # Record a completed crawl run in DB
        run_id = create_scrape_run(trigger_source="peak-schedule:us-morning", target_region="US", db_path=self.db_path)
        upsert_job({"job_id": "crawl_j1", "title": "EA", "match_score": 85, "url": "https://x.com"}, db_path=self.db_path)
        finish_scrape_run(
            run_id=run_id,
            pages_scraped=3,
            jobs_found=15,
            new_jobs=12,
            matched_jobs=8,
            status="completed",
            error_message="",
            db_path=self.db_path,
        )

        stats = get_stats(db_path=self.db_path)
        self.assertEqual(len(stats["recent_runs"]), 1)
        recent = stats["recent_runs"][0]
        self.assertEqual(recent["trigger_source"], "peak-schedule:us-morning")
        self.assertEqual(recent["pages_scraped"], 3)
        self.assertEqual(recent["jobs_found"], 15)
        self.assertEqual(recent["status"], "completed")


if __name__ == "__main__":
    unittest.main()

"""
tests/e2e/test_tier3_pairwise.py - Tier 3: Cross-Feature Combinations (Pairwise)
Opaque-box verification of multi-component pairwise integration flows:
1. Scraper Output -> DB Ingestion
2. DB Record -> Evaluator Enrichment -> DB Update
3. Evaluator -> Router Decision Matrix
4. Router -> Proposal Engine Alignment
5. Proposal Engine -> Email Dispatcher (.eml generation)
6. Email Dispatcher -> DB Audit Status Update
7. Router -> External Form DB Tracking
8. Scrape Run Tracking -> Pipeline Statistics
9. MCP Tool Pipeline: search_jobs -> get_job_details -> generate_job_proposal
10. MCP Action Pipeline: generate_job_proposal -> apply_job -> query_jobs
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
from execution.router import evaluate_job_route_and_points
from execution.email_dispatcher import dispatch_email_application
import src.mcp_server as mcp_mod
from src.mcp_server import (
    apply_job,
    generate_job_proposal,
    get_job_details,
    resource_applied_jobs,
    search_jobs,
)


class TestTier3Pairwise(unittest.TestCase):
    """Tier 3 Cross-Feature Combinations Test Suite."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="test_pairwise_")
        self.db_path = os.path.join(self.temp_dir, "pairwise_jobs.db")
        init_db(self.db_path)
        self.orig_mcp_db = mcp_mod.DB_PATH
        mcp_mod.DB_PATH = self.db_path

    def tearDown(self):
        mcp_mod.DB_PATH = self.orig_mcp_db
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_pairwise_01_scraper_to_db(self):
        """Scraper output dictionary ingests into SQLite and is retrievable with field parity."""
        scraped_raw = {
            "job_id": "scrape_901",
            "title": "Virtual Assistant - Admin & Lead Gen",
            "employer": "Summit Global Media",
            "url": "https://onlinejobs.ph/job/901",
            "salary": "$800 / month",
            "arrangement": "Full Time",
            "description": "Full-time assistant for executive calendar scheduling, spreadsheet audits, and lead generation.",
            "description_snippet": "Full-time assistant for executive calendar...",
            "skills_tags": ["Virtual Assistant", "Data Entry", "Lead Generation"],
            "posted_at": "2026-11-10 14:00:00",
            "page_scraped": 1,
        }
        is_new = upsert_job(scraped_raw, db_path=self.db_path)
        self.assertTrue(is_new)

        stored = get_job_by_id("scrape_901", db_path=self.db_path)
        self.assertIsNotNone(stored)
        self.assertEqual(stored["title"], scraped_raw["title"])
        self.assertEqual(stored["employer"], scraped_raw["employer"])
        self.assertEqual(stored["salary"], scraped_raw["salary"])
        self.assertEqual(stored["page_scraped"], 1)
        self.assertEqual(stored["skills_tags"], scraped_raw["skills_tags"])

    def test_pairwise_02_db_to_evaluator(self):
        """Job record retrieved from DB is enriched by evaluator and saved back to DB."""
        raw_job = {
            "job_id": "pair_002",
            "title": "Executive Assistant",
            "description": "Organize CEO meetings, manage Google Sheets and Microsoft Excel reports, respond to emails.",
            "salary": "USD 1,200/mo",
            "arrangement": "Full Time",
            "url": "https://onlinejobs.ph/job/pair_002",
        }
        upsert_job(raw_job, db_path=self.db_path)

        # Retrieve and evaluate
        job_from_db = get_job_by_id("pair_002", db_path=self.db_path)
        enrichment = evaluate_job(job_from_db)

        # Merge and re-upsert
        merged = {**job_from_db, **enrichment}
        upsert_job(merged, db_path=self.db_path)

        # Re-fetch and verify persistence of enriched fields
        updated = get_job_by_id("pair_002", db_path=self.db_path)
        self.assertGreaterEqual(updated["match_score"], 65)
        self.assertIn(updated["suitability_tier"], ("Good Fit", "Excellent Fit"))
        self.assertEqual(updated["is_matched"], 1)
        self.assertIsInstance(updated["matched_skills"], list)
        self.assertGreater(len(updated["matched_skills"]), 0)

    def test_pairwise_03_evaluator_to_router(self):
        """Evaluator score feeds into Router to determine route and point allocation."""
        job = {
            "job_id": "pair_003",
            "title": "Executive Virtual Assistant",
            "description": "Need skilled EA for inbox and spreadsheet management. Send resume to hiring@nexus.com.",
            "salary": "$1,000 / month",
        }
        # Step 1: Evaluator
        eval_res = evaluate_job(job)
        self.assertGreaterEqual(eval_res["match_score"], 60)

        # Step 2: Router
        router_res = evaluate_job_route_and_points({**job, **eval_res})
        self.assertEqual(router_res["route"], "EMAIL")
        self.assertEqual(router_res["connect_points"], 0)
        self.assertTrue(router_res["should_apply"])
        self.assertEqual(router_res["target_email"], "hiring@nexus.com")

    def test_pairwise_04_router_to_proposal_engine(self):
        """Router screening audit and metadata feed into proposal engine with secret code alignment."""
        job = {
            "job_id": "pair_004",
            "title": "Administrative Assistant",
            "description": 'Seeking VA for calendar and spreadsheets. Please put "Emerald" in the subject line.',
            "employer": "Horizon Logistics",
        }
        # Router extraction
        router_res = evaluate_job_route_and_points(job)
        self.assertIn("Emerald", router_res["screening_traps"]["secret_codes"])

        # Proposal generation
        prop = generate_tailored_proposal(job)
        self.assertIn("Emerald", prop["subject_line"])
        self.assertIn("Emerald", prop["proposal_text"])
        self.assertGreaterEqual(prop["word_count"], 150)
        self.assertLessEqual(prop["word_count"], 250)

    def test_pairwise_05_proposal_engine_to_email_dispatcher(self):
        """Proposal engine output populates email dispatcher and creates verified .eml draft."""
        job = {
            "job_id": "pair_005",
            "title": "Operations Coordinator",
            "description": 'Email resume to team@fintech.io with subject containing "Summit".',
        }
        prop = generate_tailored_proposal(job)

        drafts_dir = os.path.join(self.temp_dir, "drafts_p5")
        dispatch_result = dispatch_email_application(
            job_id="pair_005",
            to_email="team@fintech.io",
            subject=prop["subject_line"],
            body=prop["proposal_text"],
            draft_dir=drafts_dir,
            db_path=self.db_path,
        )

        self.assertIn(dispatch_result["status"], ("drafted_ready", "sent"))
        self.assertEqual(dispatch_result["recipient"], "team@fintech.io")
        self.assertEqual(dispatch_result["connect_points_spent"], 0)

        # Verify .eml artifact content via standard email parser (handling RFC header folding)
        import email
        import re
        eml_file = dispatch_result["eml_artifact"]
        self.assertTrue(os.path.exists(eml_file))
        with open(eml_file, "rb") as f:
            parsed = email.message_from_bytes(f.read())
        self.assertEqual(parsed["To"], "team@fintech.io")
        unfolded_subject = re.sub(r"\s+", " ", parsed["Subject"]).strip()
        self.assertEqual(unfolded_subject, prop["subject_line"])

    def test_pairwise_06_email_dispatcher_to_db_tracking(self):
        """Email dispatch updates job record in DB to status 'Applied' with audit notes."""
        job = {
            "job_id": "pair_006",
            "title": "Virtual Assistant",
            "url": "https://onlinejobs.ph/job/pair_006",
            "status": "New",
        }
        upsert_job(job, db_path=self.db_path)

        dispatch_email_application(
            job_id="pair_006",
            to_email="jobs@acmecorp.com",
            subject="VA Application",
            body="Application letter...",
            draft_dir=os.path.join(self.temp_dir, "drafts_p6"),
            db_path=self.db_path,
        )

        updated = get_job_by_id("pair_006", db_path=self.db_path)
        self.assertEqual(updated["status"], "Applied")
        self.assertIn("Applied via Email (Route A)", updated["notes"])
        self.assertIn("0 (points conserved)", updated["notes"])

    def test_pairwise_07_router_to_external_form_db_tracking(self):
        """Router selects EXTERNAL_FORM and database persists Route C application notes."""
        job = {
            "job_id": "pair_007",
            "title": "Lead Coordinator",
            "description": "Fill out Google Form at https://forms.gle/leadgen123 to apply.",
            "url": "https://onlinejobs.ph/job/pair_007",
            "status": "New",
        }
        upsert_job(job, db_path=self.db_path)

        decision = evaluate_job_route_and_points(job)
        self.assertEqual(decision["route"], "EXTERNAL_FORM")
        self.assertEqual(decision["connect_points"], 0)

        # Record form application
        notes = f"Applied via External Form (Route C): {decision['target_form_url']}. Connects spent: 0."
        update_job_status_and_notes("pair_007", status="Applied", notes=notes, db_path=self.db_path)

        stored = get_job_by_id("pair_007", db_path=self.db_path)
        self.assertEqual(stored["status"], "Applied")
        self.assertIn("Route C", stored["notes"])

    def test_pairwise_08_scraper_run_to_pipeline_stats(self):
        """Creating and finishing scrape runs correctly updates DB and get_stats metadata."""
        run_id = create_scrape_run(trigger_source="e2e-test", target_region="US", db_path=self.db_path)
        self.assertGreater(run_id, 0)

        # Upsert some jobs
        upsert_job({"job_id": "r_job_1", "title": "EA", "match_score": 85, "url": "https://x.com"}, db_path=self.db_path)
        upsert_job({"job_id": "r_job_2", "title": "VA", "match_score": 75, "url": "https://x.com"}, db_path=self.db_path)

        finish_scrape_run(
            run_id=run_id,
            pages_scraped=2,
            jobs_found=2,
            new_jobs=2,
            matched_jobs=2,
            status="completed",
            error_message="",
            db_path=self.db_path,
        )

        stats = get_stats(db_path=self.db_path)
        self.assertEqual(stats["total_jobs"], 2)
        self.assertEqual(len(stats["recent_runs"]), 1)
        self.assertEqual(stats["recent_runs"][0]["trigger_source"], "e2e-test")
        self.assertEqual(stats["recent_runs"][0]["status"], "completed")

    def test_pairwise_09_mcp_search_to_details_to_proposal_pipeline(self):
        """MCP tools chain seamlessly: search_jobs -> get_job_details -> generate_job_proposal."""
        job = {
            "job_id": "mcp_p9",
            "title": "Virtual Assistant",
            "employer": "TechCorp",
            "match_score": 85,
            "suitability_tier": "Excellent Fit",
            "status": "New",
            "url": "https://onlinejobs.ph/job/mcp_p9",
            "description": 'Manage executive calendar and spreadsheets. Put "Sapphire" in subject.',
        }
        upsert_job(job, db_path=self.db_path)

        # 1. search_jobs
        search_res = json.loads(search_jobs(min_score=80, status="New"))
        self.assertGreaterEqual(search_res["count"], 1)
        target_id = search_res["jobs"][0]["job_id"]

        # 2. get_job_details
        details = json.loads(get_job_details(target_id))
        self.assertEqual(details["job_id"], "mcp_p9")
        self.assertIn("Sapphire", details["screening_trap_audit"]["secret_codes"])

        # 3. generate_job_proposal
        prop = json.loads(generate_job_proposal(target_id, client_name="TechCorp Hiring"))
        self.assertEqual(prop["job_id"], "mcp_p9")
        self.assertIn("Sapphire", prop["subject_line"])
        self.assertIn("Sapphire", prop["proposal_text"])

    def test_pairwise_10_mcp_proposal_to_apply_to_query_jobs(self):
        """MCP apply_job updates database record which is immediately visible in queries and resources."""
        job = {
            "job_id": "mcp_p10",
            "title": "Executive Assistant",
            "match_score": 90,
            "status": "New",
            "url": "https://onlinejobs.ph/job/mcp_p10",
            "description": "Executive support.",
        }
        upsert_job(job, db_path=self.db_path)

        # Generate proposal
        prop = json.loads(generate_job_proposal("mcp_p10"))

        # Apply via MCP
        apply_res = json.loads(apply_job("mcp_p10", notes="Applied via MCP pipeline", proposal_text=prop["proposal_text"]))
        self.assertEqual(apply_res["status"], "success")

        # Verify query_jobs returns Applied status
        applied_jobs = query_jobs(status="Applied", db_path=self.db_path)
        applied_ids = [j["job_id"] for j in applied_jobs]
        self.assertIn("mcp_p10", applied_ids)

        # Verify MCP resource returns it
        res_data = json.loads(resource_applied_jobs())
        res_ids = [j["job_id"] for j in res_data]
        self.assertIn("mcp_p10", res_ids)


if __name__ == "__main__":
    unittest.main()

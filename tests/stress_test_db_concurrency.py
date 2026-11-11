"""
stress_test_db_concurrency.py - Adversarial Concurrency & Database Integrity Stress Harness
"""

import concurrent.futures
import json
import os
import shutil
import sqlite3
import tempfile
import time
import unittest
from typing import Any, Dict, List

import sys
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.db import (
    init_db,
    get_connection,
    upsert_job,
    get_job_by_id,
    query_jobs,
    update_job_status_and_notes,
    get_stats,
    checkpoint_wal,
)
from tools.seed_db import seed_database


class TestDatabaseIntegrityAndConcurrency(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="adv_db_test_")
        self.test_db = os.path.join(self.temp_dir, "test_jobs.db")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_01_clean_state_auto_init_and_wal(self):
        """Verify DB auto-initialization from clean state and WAL mode."""
        self.assertFalse(os.path.exists(self.test_db))

        # Test in nested directory that doesn't exist yet
        nested_db = os.path.join(self.temp_dir, "sub", "dir", "nested_jobs.db")
        init_db(nested_db)
        self.assertTrue(os.path.exists(nested_db))

        conn = get_connection(nested_db)
        try:
            # Check journal_mode is WAL
            cursor = conn.execute("PRAGMA journal_mode;")
            journal_mode = cursor.fetchone()[0].lower()
            self.assertEqual(journal_mode, "wal", f"Expected WAL mode, got {journal_mode}")

            # Check synchronous is NORMAL (1)
            cursor = conn.execute("PRAGMA synchronous;")
            sync_mode = cursor.fetchone()[0]
            self.assertEqual(sync_mode, 1, f"Expected synchronous=1 (NORMAL), got {sync_mode}")

            # Check tables exist
            tables = [row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()]
            self.assertIn("jobs", tables)
            self.assertIn("scrape_runs", tables)

            # Check indexes
            indexes = [row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='index';").fetchall()]
            expected_indexes = [
                "idx_jobs_match_score",
                "idx_jobs_posted_at",
                "idx_jobs_is_matched",
                "idx_jobs_status",
                "idx_jobs_client_region",
                "idx_jobs_last_scraped_at",
            ]
            for idx in expected_indexes:
                self.assertIn(idx, indexes, f"Missing index: {idx}")
        finally:
            conn.close()

    def test_02_sample_jobs_schema_adherence(self):
        """Verify all 15 sample jobs in seeds/sample_jobs.json adhere strictly to the schema."""
        seed_path = os.path.join(PROJECT_ROOT, "seeds", "sample_jobs.json")
        self.assertTrue(os.path.exists(seed_path), "sample_jobs.json does not exist")

        with open(seed_path, "r", encoding="utf-8") as f:
            jobs = json.load(f)

        self.assertEqual(len(jobs), 15, f"Expected 15 seed jobs, found {len(jobs)}")

        required_keys = [
            "job_id", "title", "employer", "url", "salary", "salary_usd_monthly_est",
            "arrangement", "hours_per_week", "posted_at", "description",
            "skills_tags", "client_region", "match_score", "suitability_tier",
            "is_matched", "role_category", "matched_skills", "missing_skills",
            "red_flags", "strengths", "status"
        ]

        valid_tiers = {"Excellent Fit", "Good Fit", "Moderate Fit", "Low Fit"}
        valid_regions = {"US", "UK", "AU", "Global", "Other"}

        for idx, job in enumerate(jobs):
            for k in required_keys:
                self.assertIn(k, job, f"Job #{idx} ({job.get('job_id')}) missing key: {k}")

            self.assertIsInstance(job["job_id"], str)
            self.assertIsInstance(job["title"], str)
            self.assertTrue(len(job["title"]) > 0)
            self.assertIsInstance(job["salary_usd_monthly_est"], (int, float))
            self.assertIsInstance(job["match_score"], int)
            self.assertTrue(0 <= job["match_score"] <= 100, f"Score out of range: {job['match_score']}")
            self.assertIn(job["is_matched"], (0, 1))
            self.assertIn(job["suitability_tier"], valid_tiers)
            self.assertIn(job["client_region"], valid_regions)

            # JSON list fields
            for list_field in ["skills_tags", "matched_skills", "missing_skills", "red_flags", "strengths"]:
                self.assertIsInstance(job[list_field], list, f"{list_field} in job #{idx} must be a list")

    def test_03_seed_idempotency_and_preservation(self):
        """Verify tools/seed_db.py idempotently upserts fixtures without corruption."""
        seed_path = os.path.join(PROJECT_ROOT, "seeds", "sample_jobs.json")

        # Run 1: Clean insertion
        res1 = seed_database(db_path=self.test_db, seed_file=seed_path, reset=True)
        self.assertEqual(res1, 0)

        conn = get_connection(self.test_db)
        count1 = conn.execute("SELECT COUNT(*) FROM jobs;").fetchone()[0]
        conn.close()
        self.assertEqual(count1, 15)

        # Modify status & notes on a specific job to test preservation
        test_job_id = "seed-001"
        update_job_status_and_notes(test_job_id, status="Applied", notes="Custom challenger note", db_path=self.test_db)
        modified_job = get_job_by_id(test_job_id, db_path=self.test_db)
        self.assertEqual(modified_job["status"], "Applied")
        self.assertEqual(modified_job["notes"], "Custom challenger note")

        # Run 2: Re-run seed WITHOUT reset
        res2 = seed_database(db_path=self.test_db, seed_file=seed_path, reset=False)
        self.assertEqual(res2, 0)

        conn = get_connection(self.test_db)
        count2 = conn.execute("SELECT COUNT(*) FROM jobs;").fetchone()[0]
        conn.close()
        self.assertEqual(count2, 15, "Re-seeding should not duplicate records")

        # Verify status and notes were preserved by upsert_job
        preserved_job = get_job_by_id(test_job_id, db_path=self.test_db)
        self.assertEqual(preserved_job["status"], "Applied", "User status was overwritten by seed re-run!")
        self.assertEqual(preserved_job["notes"], "Custom challenger note", "User notes were overwritten by seed re-run!")

        # Run 3: Re-run seed WITH reset
        res3 = seed_database(db_path=self.test_db, seed_file=seed_path, reset=True)
        self.assertEqual(res3, 0)
        reset_job = get_job_by_id(test_job_id, db_path=self.test_db)
        self.assertEqual(reset_job["status"], "New", "Reset should restore status to seed initial value")

    def test_04_high_concurrency_stress(self):
        """Stress-test concurrent writes, reads, and updates across 30 threads."""
        init_db(self.test_db)

        NUM_WRITERS = 15
        NUM_READERS = 15
        NUM_UPDATERS = 10
        NUM_ITERATIONS = 5

        errors: List[str] = []

        def worker_write(thread_id: int):
            try:
                for i in range(NUM_ITERATIONS):
                    job_data = {
                        "job_id": f"conc-job-{thread_id}-{i}",
                        "title": f"Concurrent Job {thread_id}-{i}",
                        "employer": f"Employer {thread_id}",
                        "url": f"https://example.com/job/{thread_id}/{i}",
                        "salary": "$1000/mo",
                        "salary_usd_monthly_est": 1000.0,
                        "description": f"Description for thread {thread_id} iteration {i}",
                        "match_score": 75 + (i % 20),
                        "suitability_tier": "Good Fit",
                        "is_matched": 1,
                        "role_category": "Virtual Assistant",
                        "client_region": "US" if thread_id % 2 == 0 else "UK",
                        "skills_tags": ["Python", "Async"],
                        "matched_skills": ["Python"],
                        "missing_skills": [],
                        "red_flags": [],
                        "strengths": ["Quick"],
                        "status": "New",
                    }
                    upsert_job(job_data, db_path=self.test_db)
            except Exception as e:
                errors.append(f"Write error in thread {thread_id}: {e}")

        def worker_read(thread_id: int):
            try:
                for _ in range(NUM_ITERATIONS * 2):
                    jobs = query_jobs(only_matched=True, min_score=70, db_path=self.test_db)
                    stats = get_stats(db_path=self.test_db)
                    self.assertIsInstance(jobs, list)
                    self.assertIsInstance(stats, dict)
            except Exception as e:
                errors.append(f"Read error in thread {thread_id}: {e}")

        def worker_update(thread_id: int):
            try:
                for i in range(NUM_ITERATIONS):
                    target_id = f"conc-job-{thread_id % NUM_WRITERS}-{i}"
                    update_job_status_and_notes(
                        target_id,
                        status="Reviewed",
                        notes=f"Updated by thread {thread_id}",
                        db_path=self.test_db,
                    )
            except Exception as e:
                errors.append(f"Update error in thread {thread_id}: {e}")

        with concurrent.futures.ThreadPoolExecutor(max_workers=NUM_WRITERS + NUM_READERS + NUM_UPDATERS) as executor:
            futures = []
            for t in range(NUM_WRITERS):
                futures.append(executor.submit(worker_write, t))
            for t in range(NUM_READERS):
                futures.append(executor.submit(worker_read, t))
            for t in range(NUM_UPDATERS):
                futures.append(executor.submit(worker_update, t))

            concurrent.futures.wait(futures)

        self.assertEqual(len(errors), 0, f"Concurrency errors occurred: {errors}")

        # Check total jobs inserted
        conn = get_connection(self.test_db)
        total = conn.execute("SELECT COUNT(*) FROM jobs;").fetchone()[0]
        conn.close()
        expected_total = NUM_WRITERS * NUM_ITERATIONS
        self.assertEqual(total, expected_total, f"Expected {expected_total} jobs, found {total}")

        # Test WAL checkpointing under load
        checkpoint_wal(self.test_db)


if __name__ == "__main__":
    unittest.main()

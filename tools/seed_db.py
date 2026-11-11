"""
tools/seed_db.py - Synthetic Seed Data Populator
Populates the SQLite database with 15 synthetic, sanitized job fixtures
from seeds/sample_jobs.json for immediate offline evaluation and testing.
"""

import argparse
import json
import os
import sys

# Ensure project root is in sys.path
TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(TOOLS_DIR, ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.db import init_db, upsert_job, get_connection, DB_PATH


def seed_database(
    db_path: str = DB_PATH,
    seed_file: str = os.path.join(PROJECT_ROOT, "seeds", "sample_jobs.json"),
    reset: bool = False,
) -> int:
    """Populates db_path with sample_jobs fixtures."""
    if not os.path.exists(seed_file):
        print(f"[SEED ERROR] Fixture file not found: {seed_file}", file=sys.stderr)
        return 1

    print(f"[SEED] Target Database: {db_path}")
    print(f"[SEED] Seed Fixtures:    {seed_file}")

    # Ensure schema and indexes exist
    init_db(db_path)

    if reset:
        print("[SEED] Resetting existing jobs and scrape_runs tables...")
        conn = get_connection(db_path)
        try:
            conn.execute("DELETE FROM jobs;")
            conn.execute("DELETE FROM scrape_runs;")
            conn.commit()
        finally:
            conn.close()

    with open(seed_file, "r", encoding="utf-8") as f:
        jobs = json.load(f)

    if not isinstance(jobs, list) or len(jobs) == 0:
        print(f"[SEED ERROR] Invalid seed fixture: expected non-empty list of jobs", file=sys.stderr)
        return 1

    inserted = 0
    updated = 0
    tier_counts = {"Excellent Fit": 0, "Good Fit": 0, "Moderate Fit": 0, "Low Fit": 0}
    route_counts = {"Route A (Email)": 0, "Route C (Form)": 0, "Route B (Platform)": 0}

    for job in jobs:
        is_new = upsert_job(job, db_path=db_path)
        if is_new:
            inserted += 1
        else:
            updated += 1

        tier = job.get("suitability_tier", "Low Fit")
        tier_counts[tier] = tier_counts.get(tier, 0) + 1

        notes = job.get("notes", "")
        if "Route A Email" in notes or "@" in notes:
            route_counts["Route A (Email)"] += 1
        elif "Route C" in notes or "Form" in notes:
            route_counts["Route C (Form)"] += 1
        else:
            route_counts["Route B (Platform)"] += 1

    # Insert a synthetic initial scrape run to simulate a completed crawl
    conn = get_connection(db_path)
    try:
        conn.execute(
            """
            INSERT INTO scrape_runs (
                started_at, completed_at, trigger_source, target_region,
                pages_scraped, jobs_found, new_jobs, matched_jobs, status, error_message
            ) VALUES (
                datetime('now', '-1 hour'), datetime('now'), 'seed_fixture', 'US/UK/AU',
                1, ?, ?, ?, 'completed', ''
            )
            """,
            (len(jobs), inserted, tier_counts.get("Excellent Fit", 0) + tier_counts.get("Good Fit", 0)),
        )
        conn.commit()
    finally:
        conn.close()

    print(f"[SEED SUCCESS] Populated {len(jobs)} synthetic job fixtures ({inserted} inserted, {updated} updated).")
    print(f"  - Excellent Fit (>=80%): {tier_counts.get('Excellent Fit', 0)}")
    print(f"  - Good Fit (60-79%):     {tier_counts.get('Good Fit', 0)}")
    print(f"  - Moderate Fit (50-59%): {tier_counts.get('Moderate Fit', 0)}")
    print(f"  - Low Fit (<50%):        {tier_counts.get('Low Fit', 0)}")
    print(f"  - Channel Breakdown:     {route_counts['Route A (Email)']} Email, {route_counts['Route C (Form)']} Form, {route_counts['Route B (Platform)']} Platform")

    return 0


def main():
    parser = argparse.ArgumentParser(description="Populate SQLite database with synthetic job fixtures.")
    parser.add_argument(
        "--db-path",
        default=DB_PATH,
        help="Path to target SQLite database file (default: jobs.db in project root)",
    )
    parser.add_argument(
        "--seed-file",
        default=os.path.join(PROJECT_ROOT, "seeds", "sample_jobs.json"),
        help="Path to JSON seed fixture file",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Clear existing jobs and scrape_runs records before seeding",
    )
    args = parser.parse_args()
    sys.exit(seed_database(db_path=args.db_path, seed_file=args.seed_file, reset=args.reset))


if __name__ == "__main__":
    main()

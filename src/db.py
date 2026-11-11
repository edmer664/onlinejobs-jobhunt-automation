"""
src/db.py - SQLite WAL Concurrency Engine & Database Manager
Production-grade persistence layer supporting WAL mode, atomic upserts,
query filtering, and optional Cloud Storage synchronization.
"""

import json
import os
import sqlite3
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional

SRC_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SRC_DIR, ".."))
DB_PATH = os.path.join(PROJECT_ROOT, "jobs.db")

GCS_BUCKET = os.environ.get("GCS_BUCKET", "").strip()
GCS_OBJECT = os.environ.get("GCS_OBJECT", "jobs.db").strip()
_GCS_LOCK = threading.Lock()
_GCS_RESTORED_ONCE = False

GCS_STATE: Dict[str, Any] = {
    "enabled": bool(GCS_BUCKET),
    "bucket": GCS_BUCKET or None,
    "object": GCS_OBJECT,
    "last_restored_at": None,
    "last_uploaded_at": None,
    "last_error": None,
}


def checkpoint_wal(db_path: str = DB_PATH) -> None:
    """Flushes SQLite WAL frames directly into the main database file."""
    try:
        conn = sqlite3.connect(db_path, timeout=30.0)
        try:
            conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")
        finally:
            conn.close()
    except Exception as exc:
        print(f"[DB] Warning: WAL checkpoint failed: {exc}")


def restore_db_from_gcs(db_path: str = DB_PATH) -> bool:
    """Downloads DB from GCS bucket if configured (optional cloud persistence)."""
    bucket_name = os.environ.get("GCS_BUCKET", GCS_BUCKET).strip()
    object_name = os.environ.get("GCS_OBJECT", GCS_OBJECT).strip()
    GCS_STATE["enabled"] = bool(bucket_name)
    GCS_STATE["bucket"] = bucket_name or None
    GCS_STATE["object"] = object_name
    if not bucket_name:
        return False

    with _GCS_LOCK:
        try:
            from google.cloud import storage
            client = storage.Client()
            bucket = client.bucket(bucket_name)
            blob = bucket.blob(object_name)
            if not blob.exists():
                print(f"[GCS] Remote gs://{bucket_name}/{object_name} does not exist yet. Skipping restore.")
                return False

            os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
            blob.download_to_filename(db_path)
            now_iso = datetime.now().isoformat()
            GCS_STATE["last_restored_at"] = now_iso
            GCS_STATE["last_error"] = None
            print(f"[GCS] Successfully restored {db_path} from gs://{bucket_name}/{object_name} at {now_iso}")
            return True
        except Exception as exc:
            GCS_STATE["last_error"] = str(exc)
            print(f"[GCS] Warning: restore_db_from_gcs failed: {exc}")
            return False


def sync_db_to_gcs(db_path: str = DB_PATH) -> bool:
    """Uploads DB to GCS bucket if configured."""
    bucket_name = os.environ.get("GCS_BUCKET", GCS_BUCKET).strip()
    object_name = os.environ.get("GCS_OBJECT", GCS_OBJECT).strip()
    if not bucket_name:
        return False

    checkpoint_wal(db_path)
    with _GCS_LOCK:
        try:
            from google.cloud import storage
            client = storage.Client()
            bucket = client.bucket(bucket_name)
            blob = bucket.blob(object_name)
            blob.upload_from_filename(db_path)
            now_iso = datetime.now().isoformat()
            GCS_STATE["last_uploaded_at"] = now_iso
            GCS_STATE["last_error"] = None
            return True
        except Exception as exc:
            GCS_STATE["last_error"] = str(exc)
            print(f"[GCS] Warning: sync_db_to_gcs failed: {exc}")
            return False


def get_connection(db_path: str = DB_PATH) -> sqlite3.Connection:
    """Returns a thread-safe connection configured with WAL mode and row factory."""
    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
    conn = sqlite3.connect(db_path, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn


def init_db(db_path: str = DB_PATH) -> None:
    """Idempotently initializes SQLite WAL tables and indexes."""
    global _GCS_RESTORED_ONCE
    bucket_name = os.environ.get("GCS_BUCKET", GCS_BUCKET).strip()
    restored = False
    if bucket_name and not _GCS_RESTORED_ONCE:
        _GCS_RESTORED_ONCE = True
        restored = restore_db_from_gcs(db_path)

    conn = get_connection(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                job_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                employer TEXT DEFAULT 'Undisclosed',
                url TEXT NOT NULL,
                salary TEXT DEFAULT 'Not specified',
                salary_usd_monthly_est REAL DEFAULT 0.0,
                arrangement TEXT DEFAULT 'Any',
                hours_per_week TEXT DEFAULT '',
                posted_at TEXT DEFAULT '',
                posted_at_utc TEXT DEFAULT '',
                date_updated TEXT DEFAULT '',
                description TEXT DEFAULT '',
                description_snippet TEXT DEFAULT '',
                skills_tags TEXT DEFAULT '[]',
                employer_member_since TEXT DEFAULT '',
                employer_total_posts TEXT DEFAULT '',
                client_region TEXT DEFAULT 'Global',
                peak_window TEXT DEFAULT 'General',
                match_score INTEGER DEFAULT 0,
                suitability_tier TEXT DEFAULT 'Low Fit',
                is_matched INTEGER DEFAULT 0,
                role_category TEXT DEFAULT 'Other',
                matched_skills TEXT DEFAULT '[]',
                missing_skills TEXT DEFAULT '[]',
                red_flags TEXT DEFAULT '[]',
                strengths TEXT DEFAULT '[]',
                evaluation_summary TEXT DEFAULT '',
                status TEXT DEFAULT 'New',
                notes TEXT DEFAULT '',
                page_scraped INTEGER DEFAULT 1,
                first_scraped_at TEXT NOT NULL,
                last_scraped_at TEXT NOT NULL
            );
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_match_score ON jobs(match_score DESC);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_posted_at ON jobs(posted_at DESC);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_is_matched ON jobs(is_matched);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_client_region ON jobs(client_region);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_last_scraped_at ON jobs(last_scraped_at DESC);")

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS scrape_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TEXT NOT NULL,
                completed_at TEXT DEFAULT '',
                trigger_source TEXT DEFAULT 'manual',
                target_region TEXT DEFAULT 'US/UK/AU',
                pages_scraped INTEGER DEFAULT 0,
                jobs_found INTEGER DEFAULT 0,
                new_jobs INTEGER DEFAULT 0,
                matched_jobs INTEGER DEFAULT 0,
                status TEXT DEFAULT 'running',
                error_message TEXT DEFAULT ''
            );
            """
        )
        cur_clean = conn.execute(
            "DELETE FROM scrape_runs WHERE status = 'failed' AND trigger_source LIKE 'peak-schedule:%'"
        )
        cleaned_rows = cur_clean.rowcount
        conn.commit()
    finally:
        conn.close()

    if bucket_name and (cleaned_rows > 0 or (not restored and GCS_STATE["last_restored_at"] is None)):
        sync_db_to_gcs(db_path)


def upsert_job(job: Dict[str, Any], db_path: str = DB_PATH) -> bool:
    """
    Insert or update a scraped & evaluated job.
    Preserves user-assigned `status` and `notes` if the record previously existed.
    Returns True if newly inserted, False if updated.
    """
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_connection(db_path)
    try:
        existing = conn.execute(
            "SELECT job_id, status, notes, first_scraped_at FROM jobs WHERE job_id = ?",
            (str(job["job_id"]),),
        ).fetchone()

        is_new = existing is None
        status = existing["status"] if existing and existing["status"] else job.get("status", "New")
        notes = existing["notes"] if existing and existing["notes"] is not None else job.get("notes", "")
        first_scraped = existing["first_scraped_at"] if existing else now_str

        conn.execute(
            """
            INSERT INTO jobs (
                job_id, title, employer, url, salary, salary_usd_monthly_est,
                arrangement, hours_per_week, posted_at, posted_at_utc, date_updated,
                description, description_snippet, skills_tags,
                employer_member_since, employer_total_posts,
                client_region, peak_window,
                match_score, suitability_tier, is_matched, role_category,
                matched_skills, missing_skills, red_flags, strengths, evaluation_summary,
                status, notes, page_scraped, first_scraped_at, last_scraped_at
            ) VALUES (
                ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?,
                ?, ?, ?,
                ?, ?,
                ?, ?,
                ?, ?, ?, ?,
                ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?
            )
            ON CONFLICT(job_id) DO UPDATE SET
                title = excluded.title,
                employer = excluded.employer,
                url = excluded.url,
                salary = excluded.salary,
                salary_usd_monthly_est = excluded.salary_usd_monthly_est,
                arrangement = excluded.arrangement,
                hours_per_week = CASE WHEN excluded.hours_per_week != '' THEN excluded.hours_per_week ELSE jobs.hours_per_week END,
                posted_at = CASE WHEN excluded.posted_at != '' THEN excluded.posted_at ELSE jobs.posted_at END,
                posted_at_utc = CASE WHEN excluded.posted_at_utc != '' THEN excluded.posted_at_utc ELSE jobs.posted_at_utc END,
                date_updated = CASE WHEN excluded.date_updated != '' THEN excluded.date_updated ELSE jobs.date_updated END,
                description = CASE WHEN length(excluded.description) >= length(jobs.description) THEN excluded.description ELSE jobs.description END,
                description_snippet = excluded.description_snippet,
                skills_tags = CASE WHEN length(excluded.description) >= length(jobs.description) THEN excluded.skills_tags ELSE jobs.skills_tags END,
                employer_member_since = CASE WHEN excluded.employer_member_since != '' THEN excluded.employer_member_since ELSE jobs.employer_member_since END,
                employer_total_posts = CASE WHEN excluded.employer_total_posts != '' THEN excluded.employer_total_posts ELSE jobs.employer_total_posts END,
                client_region = excluded.client_region,
                peak_window = excluded.peak_window,
                match_score = CASE WHEN length(excluded.description) >= length(jobs.description) THEN excluded.match_score ELSE jobs.match_score END,
                suitability_tier = CASE WHEN length(excluded.description) >= length(jobs.description) THEN excluded.suitability_tier ELSE jobs.suitability_tier END,
                is_matched = CASE WHEN length(excluded.description) >= length(jobs.description) THEN excluded.is_matched ELSE jobs.is_matched END,
                role_category = CASE WHEN length(excluded.description) >= length(jobs.description) THEN excluded.role_category ELSE jobs.role_category END,
                matched_skills = CASE WHEN length(excluded.description) >= length(jobs.description) THEN excluded.matched_skills ELSE jobs.matched_skills END,
                missing_skills = CASE WHEN length(excluded.description) >= length(jobs.description) THEN excluded.missing_skills ELSE jobs.missing_skills END,
                red_flags = CASE WHEN length(excluded.description) >= length(jobs.description) THEN excluded.red_flags ELSE jobs.red_flags END,
                strengths = CASE WHEN length(excluded.description) >= length(jobs.description) THEN excluded.strengths ELSE jobs.strengths END,
                evaluation_summary = CASE WHEN length(excluded.description) >= length(jobs.description) THEN excluded.evaluation_summary ELSE jobs.evaluation_summary END,
                page_scraped = excluded.page_scraped,
                last_scraped_at = excluded.last_scraped_at
            """,
            (
                str(job["job_id"]),
                job.get("title", ""),
                job.get("employer", "Undisclosed"),
                job.get("url", ""),
                job.get("salary", "Not specified"),
                float(job.get("salary_usd_monthly_est", 0.0)),
                job.get("arrangement", "Any"),
                str(job.get("hours_per_week", "")),
                job.get("posted_at", ""),
                job.get("posted_at_utc", ""),
                job.get("date_updated", ""),
                job.get("description", ""),
                job.get("description_snippet", ""),
                json.dumps(job.get("skills_tags", []), ensure_ascii=False) if not isinstance(job.get("skills_tags"), str) else job.get("skills_tags"),
                job.get("employer_member_since", ""),
                str(job.get("employer_total_posts", "")),
                job.get("client_region", "Global"),
                job.get("peak_window", "General"),
                int(job.get("match_score", 0)),
                job.get("suitability_tier", "Low Fit"),
                1 if int(job.get("match_score", 0)) >= 60 else 0,
                job.get("role_category", "Other"),
                json.dumps(job.get("matched_skills", []), ensure_ascii=False) if not isinstance(job.get("matched_skills"), str) else job.get("matched_skills"),
                json.dumps(job.get("missing_skills", []), ensure_ascii=False) if not isinstance(job.get("missing_skills"), str) else job.get("missing_skills"),
                json.dumps(job.get("red_flags", []), ensure_ascii=False) if not isinstance(job.get("red_flags"), str) else job.get("red_flags"),
                json.dumps(job.get("strengths", []), ensure_ascii=False) if not isinstance(job.get("strengths"), str) else job.get("strengths"),
                job.get("evaluation_summary", ""),
                status,
                notes,
                int(job.get("page_scraped", 1)),
                first_scraped,
                now_str,
            ),
        )
        conn.commit()
        return is_new
    finally:
        conn.close()


def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    """Helper converting sqlite3.Row to Python dict with parsed JSON columns."""
    d = dict(row)
    for json_field in ["skills_tags", "matched_skills", "missing_skills", "red_flags", "strengths"]:
        raw = d.get(json_field, "[]")
        try:
            d[json_field] = json.loads(raw) if isinstance(raw, str) else (raw or [])
        except Exception:
            d[json_field] = []
    return d


def get_job_by_id(job_id: str, db_path: str = DB_PATH) -> Optional[Dict[str, Any]]:
    init_db(db_path)
    conn = get_connection(db_path)
    try:
        row = conn.execute("SELECT * FROM jobs WHERE job_id = ?", (str(job_id),)).fetchone()
        return _row_to_dict(row) if row else None
    finally:
        conn.close()


def query_jobs(
    only_matched: bool = False,
    min_score: Optional[int] = None,
    status: Optional[str] = None,
    client_region: Optional[str] = None,
    role_category: Optional[str] = None,
    arrangement: Optional[str] = None,
    suitability_tier: Optional[str] = None,
    search: Optional[str] = None,
    date_filter: Optional[str] = None,
    last_scraped_hours: Optional[float] = None,
    sort_by: str = "match_score",
    sort_dir: str = "desc",
    db_path: str = DB_PATH,
) -> List[Dict[str, Any]]:
    init_db(db_path)
    clauses = []
    params: List[Any] = []

    now_pht = datetime.now()

    if only_matched:
        clauses.append("is_matched = 1")
    if min_score is not None:
        clauses.append("match_score >= ?")
        params.append(int(min_score))
    if status and status.lower() != "all":
        clauses.append("status = ?")
        params.append(status)
    if client_region and client_region.lower() != "all":
        if client_region.upper() == "US_UK_AU":
            clauses.append("client_region IN ('US', 'UK', 'AU')")
        else:
            clauses.append("client_region = ?")
            params.append(client_region)
    if role_category and role_category.lower() != "all":
        clauses.append("role_category = ?")
        params.append(role_category)
    if arrangement and arrangement.lower() != "all":
        clauses.append("LOWER(arrangement) LIKE ?")
        params.append(f"%{arrangement.lower()}%")
    if suitability_tier and suitability_tier.lower() != "all":
        clauses.append("suitability_tier = ?")
        params.append(suitability_tier)
    if search and search.strip():
        q = f"%{search.strip().lower()}%"
        clauses.append(
            "(LOWER(title) LIKE ? OR LOWER(description) LIKE ? OR LOWER(employer) LIKE ? OR LOWER(skills_tags) LIKE ? OR LOWER(matched_skills) LIKE ?)"
        )
        params.extend([q, q, q, q, q])

    if last_scraped_hours is not None and float(last_scraped_hours) > 0:
        from datetime import timedelta
        cutoff_str = (now_pht - timedelta(hours=float(last_scraped_hours))).strftime("%Y-%m-%d %H:%M:%S")
        clauses.append("last_scraped_at >= ?")
        params.append(cutoff_str)

    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""

    valid_sort_columns = {
        "match_score": "match_score",
        "posted_at": "posted_at",
        "last_scraped_at": "last_scraped_at",
        "salary": "salary_usd_monthly_est",
        "title": "title",
        "client_region": "client_region",
        "status": "status",
        "page_scraped": "page_scraped",
    }
    sort_col = valid_sort_columns.get(sort_by, "match_score")
    direction = "ASC" if sort_dir.lower() == "asc" else "DESC"

    order_sql = f"ORDER BY {sort_col} {direction}, posted_at DESC"

    conn = get_connection(db_path)
    try:
        rows = conn.execute(f"SELECT * FROM jobs {where_sql} {order_sql}", params).fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        conn.close()


def update_job_status_and_notes(
    job_id: str,
    status: Optional[str] = None,
    notes: Optional[str] = None,
    db_path: str = DB_PATH,
) -> Optional[Dict[str, Any]]:
    init_db(db_path)
    conn = get_connection(db_path)
    try:
        if status is not None and notes is not None:
            conn.execute(
                "UPDATE jobs SET status = ?, notes = ? WHERE job_id = ?",
                (status, notes, str(job_id)),
            )
        elif status is not None:
            conn.execute(
                "UPDATE jobs SET status = ? WHERE job_id = ?",
                (status, str(job_id)),
            )
        elif notes is not None:
            conn.execute(
                "UPDATE jobs SET notes = ? WHERE job_id = ?",
                (notes, str(job_id)),
            )
        conn.commit()
    finally:
        conn.close()
    sync_db_to_gcs(db_path)
    return get_job_by_id(job_id, db_path)


def get_stats(db_path: str = DB_PATH) -> Dict[str, Any]:
    init_db(db_path)
    conn = get_connection(db_path)
    try:
        total = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
        matched = conn.execute("SELECT COUNT(*) FROM jobs WHERE is_matched = 1").fetchone()[0]
        excellent = conn.execute("SELECT COUNT(*) FROM jobs WHERE match_score >= 80").fetchone()[0]
        good = conn.execute("SELECT COUNT(*) FROM jobs WHERE match_score >= 60 AND match_score < 80").fetchone()[0]
        avg_score = conn.execute("SELECT COALESCE(ROUND(AVG(match_score), 1), 0) FROM jobs WHERE is_matched = 1").fetchone()[0]

        from datetime import timedelta
        now_dt = datetime.now()
        five_hours_ago = (now_dt - timedelta(hours=5)).strftime("%Y-%m-%d %H:%M:%S")

        scraped_last_5h = conn.execute(
            "SELECT COUNT(*) FROM jobs WHERE last_scraped_at >= ?", (five_hours_ago,)
        ).fetchone()[0]
        matched_last_5h = conn.execute(
            "SELECT COUNT(*) FROM jobs WHERE is_matched = 1 AND last_scraped_at >= ?", (five_hours_ago,)
        ).fetchone()[0]

        by_region = {
            row["client_region"]: row["cnt"]
            for row in conn.execute("SELECT client_region, COUNT(*) as cnt FROM jobs GROUP BY client_region").fetchall()
        }
        by_status = {
            row["status"]: row["cnt"]
            for row in conn.execute("SELECT status, COUNT(*) as cnt FROM jobs GROUP BY status").fetchall()
        }
        by_category = {
            row["role_category"]: row["cnt"]
            for row in conn.execute("SELECT role_category, COUNT(*) as cnt FROM jobs GROUP BY role_category").fetchall()
        }
        recent_runs = [
            dict(r)
            for r in conn.execute("SELECT * FROM scrape_runs ORDER BY id DESC LIMIT 10").fetchall()
        ]

        return {
            "total_jobs": total,
            "matched_jobs": matched,
            "excellent_fits": excellent,
            "good_fits": good,
            "avg_matched_score": avg_score,
            "scraped_last_5h": scraped_last_5h,
            "matched_last_5h": matched_last_5h,
            "by_region": by_region,
            "by_status": by_status,
            "by_category": by_category,
            "recent_runs": recent_runs,
            "gcs_persistence": dict(GCS_STATE),
        }
    finally:
        conn.close()


def create_scrape_run(trigger_source: str = "manual", target_region: str = "US/UK/AU", db_path: str = DB_PATH) -> int:
    init_db(db_path)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_connection(db_path)
    try:
        cur = conn.execute(
            """
            INSERT INTO scrape_runs (started_at, trigger_source, target_region, status)
            VALUES (?, ?, ?, 'running')
            """,
            (now_str, trigger_source, target_region),
        )
        conn.commit()
        return int(cur.lastrowid)
    finally:
        conn.close()


def finish_scrape_run(
    run_id: int,
    pages_scraped: int,
    jobs_found: int,
    new_jobs: int,
    matched_jobs: int,
    status: str = "completed",
    error_message: str = "",
    db_path: str = DB_PATH,
) -> bool:
    init_db(db_path)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_connection(db_path)
    try:
        conn.execute(
            """
            UPDATE scrape_runs
            SET completed_at = ?, pages_scraped = ?, jobs_found = ?,
                new_jobs = ?, matched_jobs = ?, status = ?, error_message = ?
            WHERE id = ?
            """,
            (now_str, pages_scraped, jobs_found, new_jobs, matched_jobs, status, error_message, run_id),
        )
        conn.commit()
    finally:
        conn.close()
    return sync_db_to_gcs(db_path)


# Interface Contract Aliases per PROJECT.md
get_job = get_job_by_id


def search_jobs(filters: Optional[Dict[str, Any]] = None, db_path: str = DB_PATH, **kwargs) -> List[Dict[str, Any]]:
    """Alias/wrapper conforming to PROJECT.md interface contract.
    Supports either a dictionary of filters (per PROJECT.md specification)
    or keyword arguments matching query_jobs directly.
    """
    if isinstance(filters, dict):
        merged = dict(filters)
        merged.update(kwargs)
        return query_jobs(
            only_matched=merged.get("only_matched", False),
            min_score=merged.get("min_score"),
            status=merged.get("status"),
            client_region=merged.get("client_region"),
            role_category=merged.get("role_category"),
            arrangement=merged.get("arrangement"),
            suitability_tier=merged.get("suitability_tier"),
            search=merged.get("search") or merged.get("query"),
            date_filter=merged.get("date_filter"),
            last_scraped_hours=merged.get("last_scraped_hours"),
            sort_by=merged.get("sort_by", "match_score"),
            sort_dir=merged.get("sort_dir", "desc"),
            db_path=merged.get("db_path", db_path),
        )
    if isinstance(filters, bool):
        return query_jobs(only_matched=filters, db_path=db_path, **kwargs)
    if filters is None and kwargs:
        return query_jobs(db_path=db_path, **kwargs)
    return query_jobs(db_path=db_path)


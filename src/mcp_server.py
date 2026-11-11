"""
Model Context Protocol (MCP) Server for OnlineJobs.ph Portal
Empowers AI agents (Claude Desktop, Cursor, Antigravity, Windsurf, custom agents)
to discover enriched jobs, inspect requirements, generate grounded proposals,
and track applications directly via MCP tools and resources.
"""

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# Ensure local imports work regardless of working directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

try:
    from db import (
        DB_PATH,
        get_job_by_id,
        get_stats,
        init_db,
        query_jobs,
        sync_db_to_gcs,
        update_job_status_and_notes,
    )
    from config_loader import get_candidate_profile as get_profile_data
    from proposal_engine import audit_screening_traps, generate_tailored_proposal
    from scheduler import get_schedule_status
except ImportError:
    from src.db import (
        DB_PATH,
        get_job_by_id,
        get_stats,
        init_db,
        query_jobs,
        sync_db_to_gcs,
        update_job_status_and_notes,
    )
    from src.config_loader import get_candidate_profile as get_profile_data
    from src.proposal_engine import audit_screening_traps, generate_tailored_proposal
    from src.scheduler import get_schedule_status

# Import modern MCP Server (mcp 2.x)
from mcp.server.mcpserver import MCPServer

# Initialize MCP Server
mcp = MCPServer(
    name="onlinejobs-portal",
    instructions=(
        "You are connected to the OnlineJobs.ph Job Enrichment & Application Portal MCP Server. "
        "Use these tools to search high-fit remote jobs, audit screening questions/codes, generate 100% fact-grounded "
        "tailored proposals (150-250 words), and track application statuses directly."
    ),
    version="1.0.0",
)


@mcp.tool()
def search_jobs(
    min_score: int = 70,
    status: str = "New",
    client_region: str = "All",
    role_category: str = "All",
    arrangement: str = "All",
    search: str = "",
    date_filter: str = "All",
    scraped_within_hours: Optional[float] = None,
    limit: int = 15,
) -> str:
    """
    Search and filter enriched remote jobs from OnlineJobs.ph stored in the database.

    Args:
        min_score: Minimum suitability match score (0-100). Default is 70.
        status: Application status ('New', 'Shortlisted', 'Applied', 'Interviewing', or 'All').
        client_region: Client region ('US', 'UK', 'AU', 'US_UK_AU', or 'All').
        role_category: Role category ('Virtual Assistant', 'Lead Generation', 'Data & Bookkeeping', 'Social Media & Content', 'Operations Coordinator', or 'All').
        arrangement: Work arrangement ('Full Time', 'Part Time', 'Gig', or 'All').
        search: Free-text search query across job title, description, skills, and employer.
        date_filter: Optional date filter ('All', 'last5hours', 'today', 'yesterday', 'pastweek').
        scraped_within_hours: Optional float filter for jobs scraped within the last N hours (e.g. 5.0).
        limit: Maximum number of jobs to return (default 15).
    """
    init_db(DB_PATH)
    jobs = query_jobs(
        only_matched=True,
        min_score=min_score,
        status=status,
        client_region=client_region,
        role_category=role_category,
        arrangement=arrangement,
        search=search,
        date_filter=date_filter,
        last_scraped_hours=scraped_within_hours,
        sort_by="match_score",
        sort_dir="desc",
        db_path=DB_PATH,
    )
    trimmed = jobs[:limit]
    results = []
    for j in trimmed:
        results.append(
            {
                "job_id": j["job_id"],
                "title": j["title"],
                "employer": j["employer"],
                "match_score": j["match_score"],
                "suitability_tier": j["suitability_tier"],
                "role_category": j["role_category"],
                "client_region": j["client_region"],
                "salary": j["salary"],
                "status": j["status"],
                "url": j["url"],
                "posted_at": j["posted_at"],
                "matched_skills": j["matched_skills"],
                "missing_skills": j["missing_skills"],
                "red_flags": j["red_flags"],
            }
        )
    return json.dumps({"count": len(results), "total_found": len(jobs), "jobs": results}, indent=2)


@mcp.tool()
def get_job_details(job_id: str) -> str:
    """
    Retrieve full, un-truncated details for a specific job post, including screening trap audit,
    employer information, matched skills, and full description.

    Args:
        job_id: OnlineJobs.ph Job ID (e.g. '1762346' or 'seed-001')
    """
    init_db(DB_PATH)
    job = get_job_by_id(str(job_id).strip(), db_path=DB_PATH)
    if not job:
        return json.dumps({"error": f"Job ID {job_id} not found in database"}, indent=2)

    traps = audit_screening_traps(job.get("description", "") or job.get("description_snippet", ""))
    job["screening_trap_audit"] = traps
    return json.dumps(job, indent=2)


@mcp.tool()
def generate_job_proposal(
    job_id: str,
    client_name: str = "",
    extra_instructions: str = "",
) -> str:
    """
    Generate an authentic, high-conversion, fact-grounded proposal for the candidate (150-250 words max).
    Automatically audits screening codes, secret words, and addresses client pain points with zero hallucinations.

    Args:
        job_id: OnlineJobs.ph Job ID (e.g. 'seed-001')
        client_name: Optional direct name of the hiring manager or client
        extra_instructions: Optional specific focus areas or tone instructions
    """
    init_db(DB_PATH)
    job = get_job_by_id(str(job_id).strip(), db_path=DB_PATH)
    if not job:
        return json.dumps({"error": f"Job ID {job_id} not found in database"}, indent=2)

    proposal = generate_tailored_proposal(
        job,
        custom_client_name=client_name,
        extra_instructions=extra_instructions,
    )
    return json.dumps(proposal, indent=2)


@mcp.tool()
def apply_job(
    job_id: str,
    notes: str = "",
    proposal_text: str = "",
) -> str:
    """
    Mark a job as 'Applied' in the database and append timestamped application notes and submitted proposal.

    Args:
        job_id: OnlineJobs.ph Job ID
        notes: Application notes (e.g. 'Applied via email to hiring@company.com with code BLUEBERRY')
        proposal_text: The exact proposal letter submitted to the employer
    """
    init_db(DB_PATH)
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    record = get_job_by_id(str(job_id).strip(), db_path=DB_PATH)
    if not record:
        return json.dumps({"error": f"Job ID {job_id} not found"}, indent=2)

    existing_notes = record.get("notes") or ""
    append_parts = [f"Applied on {now_str}"]
    if notes:
        append_parts.append(notes)
    if proposal_text:
        append_parts.append(f"\n--- Submitted Proposal ---\n{proposal_text}")

    new_notes = f"{existing_notes}\n\n" + "\n".join(append_parts) if existing_notes else "\n".join(append_parts)

    updated = update_job_status_and_notes(str(job_id).strip(), status="Applied", notes=new_notes.strip(), db_path=DB_PATH)
    return json.dumps({"status": "success", "job_id": job_id, "job_status": "Applied", "notes": updated["notes"]}, indent=2)


@mcp.tool()
def update_job_status(
    job_id: str,
    status: str,
    notes: Optional[str] = None,
) -> str:
    """
    Update the tracking status of a job (e.g. Shortlisted, Interviewing, Offer, Rejected, Archived).

    Args:
        job_id: OnlineJobs.ph Job ID
        status: New status ('New', 'Shortlisted', 'Applied', 'Interviewing', 'Offer', 'Rejected', 'Archived')
        notes: Optional notes to update or append
    """
    init_db(DB_PATH)
    valid_statuses = ["New", "Shortlisted", "Applied", "Interviewing", "Offer", "Rejected", "Archived"]
    matched_status = next((s for s in valid_statuses if s.lower() == status.strip().lower()), None)
    if not matched_status:
        return json.dumps({"error": f"Invalid status '{status}'. Valid options: {valid_statuses}"}, indent=2)

    updated = update_job_status_and_notes(str(job_id).strip(), status=matched_status, notes=notes, db_path=DB_PATH)
    if not updated:
        return json.dumps({"error": f"Job ID {job_id} not found"}, indent=2)

    return json.dumps({"status": "success", "job_id": job_id, "new_status": matched_status, "notes": updated["notes"]}, indent=2)


@mcp.tool()
def trigger_scrape(
    pages: int = 5,
    target_region: str = "US/UK/AU",
) -> str:
    """
    Trigger an on-demand scraper run against OnlineJobs.ph. Scrapes recent jobs, calculates match scores, and stores them in SQLite.

    Args:
        pages: Number of pages to scrape (default 5, ~150 jobs)
        target_region: Target client timezone region ('US', 'UK', 'AU', or 'US/UK/AU')
    """
    try:
        from scraper import SCRAPE_PROGRESS, run_scrape
    except ImportError:
        from src.scraper import SCRAPE_PROGRESS, run_scrape

    if SCRAPE_PROGRESS.get("is_running"):
        return json.dumps({"status": "already_running", "progress": SCRAPE_PROGRESS}, indent=2)

    loop = asyncio.get_event_loop()
    if loop.is_running():
        import threading
        result_holder = {}

        def _worker():
            res = asyncio.run(run_scrape(num_pages=pages, trigger_source="mcp-tool", target_region=target_region, db_path=DB_PATH))
            result_holder.update(res)

        t = threading.Thread(target=_worker)
        t.start()
        t.join(timeout=300.0)
        return json.dumps(result_holder or {"status": "started_async"}, indent=2)
    else:
        res = loop.run_until_complete(run_scrape(num_pages=pages, trigger_source="mcp-tool", target_region=target_region, db_path=DB_PATH))
        return json.dumps(res, indent=2)


@mcp.tool()
def get_pipeline_stats() -> str:
    """
    Get overall job pipeline metrics: total scraped jobs, matched count, status breakdown, and scheduler state.
    """
    init_db(DB_PATH)
    stats = get_stats(DB_PATH)
    stats["scheduler"] = get_schedule_status()
    return json.dumps(stats, indent=2)


@mcp.tool()
def get_candidate_profile() -> str:
    """
    Returns candidate verified master resume ground truth, certifications, metrics, and anti-hallucination rules.
    """
    return json.dumps(get_profile_data(), indent=2)


# Resources
@mcp.resource("jobs://matched")
def resource_matched_jobs() -> str:
    """List of all currently matched jobs (score >= 60%) in JSON."""
    init_db(DB_PATH)
    jobs = query_jobs(only_matched=True, sort_by="match_score", sort_dir="desc", db_path=DB_PATH)
    return json.dumps([{"job_id": j["job_id"], "title": j["title"], "score": j["match_score"], "status": j["status"], "salary": j["salary"]} for j in jobs], indent=2)


@mcp.resource("jobs://recent-5h")
def resource_recent_5h_jobs() -> str:
    """List of all jobs scraped in the last 5 hours in JSON."""
    init_db(DB_PATH)
    jobs = query_jobs(last_scraped_hours=5.0, sort_by="last_scraped_at", sort_dir="desc", db_path=DB_PATH)
    return json.dumps([{"job_id": j["job_id"], "title": j["title"], "score": j["match_score"], "status": j["status"], "salary": j["salary"], "scraped_at": j["last_scraped_at"], "url": j["url"]} for j in jobs], indent=2)


@mcp.resource("jobs://applied")
def resource_applied_jobs() -> str:
    """List of all jobs currently marked as Applied."""
    init_db(DB_PATH)
    jobs = query_jobs(status="Applied", sort_by="posted_at", sort_dir="desc", db_path=DB_PATH)
    return json.dumps(jobs, indent=2)


@mcp.resource("candidate://profile")
def resource_candidate_profile() -> str:
    """Full verified candidate profile and qualification ground truth."""
    return json.dumps(get_profile_data(), indent=2)


@mcp.resource("portal://stats")
def resource_portal_stats() -> str:
    """Current pipeline and scraper statistics."""
    init_db(DB_PATH)
    stats = get_stats(DB_PATH)
    return json.dumps(stats, indent=2)


# Prompts
@mcp.prompt()
def find_and_apply_flow() -> str:
    """Interactive workflow prompt to review top matched jobs, audit screening traps, and apply."""
    return (
        "Follow this workflow to discover, evaluate, and apply to high-fit remote jobs:\n"
        "1. Call `search_jobs(min_score=75, status='New', limit=5)` to get the top unapplied opportunities.\n"
        "2. For the best match, call `get_job_details(job_id=...)` and inspect the complete description and screening trap audit.\n"
        "3. Call `generate_job_proposal(job_id=...)` to generate a 150-250 word high-conversion proposal addressing secret codes and client pain points.\n"
        "4. Review the generated proposal with the user or submit it via the indicated submission channel.\n"
        "5. Once submitted, call `apply_job(job_id=..., notes=..., proposal_text=...)` to mark it as Applied and record it in the database."
    )


def main():
    parser = argparse.ArgumentParser(description="OnlineJobs.ph MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse", "streamable-http"],
        default="stdio",
        help="Transport protocol (stdio, sse, or streamable-http)",
    )
    parser.add_argument("--host", default="0.0.0.0", help="Host for SSE / Streamable HTTP server")
    parser.add_argument("--port", type=int, default=5055, help="Port for SSE / Streamable HTTP server")
    args = parser.parse_args()

    init_db(DB_PATH)

    if args.transport == "stdio":
        # Standard MCP stdio transport (Claude Desktop, Cursor, Antigravity)
        mcp.run(transport="stdio")
    elif args.transport == "sse":
        print(f"\n[MCP] Starting OnlineJobs Portal MCP Server (SSE) on http://{args.host}:{args.port}/sse\n")
        mcp.run(transport="sse", host=args.host, port=args.port)
    elif args.transport == "streamable-http":
        print(f"\n[MCP] Starting OnlineJobs Portal MCP Server (Streamable HTTP) on http://{args.host}:{args.port}/mcp\n")
        mcp.run(transport="streamable-http", host=args.host, port=args.port)


if __name__ == "__main__":
    main()

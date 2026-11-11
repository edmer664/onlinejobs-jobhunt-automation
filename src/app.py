import asyncio
import os
import sys
import threading
from flask import Flask, jsonify, render_template, request

try:
    from db import (
        DB_PATH,
        GCS_STATE,
        get_job_by_id,
        get_stats,
        init_db,
        query_jobs,
        restore_db_from_gcs,
        sync_db_to_gcs,
        update_job_status_and_notes,
    )
    from proposal_engine import audit_screening_traps, generate_tailored_proposal
    from scheduler import SCHEDULER_STATE, get_schedule_status, start_background_scheduler
    from scraper import SCRAPE_PROGRESS, run_scrape
except ImportError:
    from src.db import (
        DB_PATH,
        GCS_STATE,
        get_job_by_id,
        get_stats,
        init_db,
        query_jobs,
        restore_db_from_gcs,
        sync_db_to_gcs,
        update_job_status_and_notes,
    )
    from src.proposal_engine import audit_screening_traps, generate_tailored_proposal
    from src.scheduler import SCHEDULER_STATE, get_schedule_status, start_background_scheduler
    from src.scraper import SCRAPE_PROGRESS, run_scrape

# Locate templates directory
SRC_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SRC_DIR, ".."))
TEMPLATES_DIR = os.path.join(PROJECT_ROOT, "templates")

app = Flask(__name__, template_folder=TEMPLATES_DIR)
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.jinja_env.auto_reload = True

# Ensure SQLite schema and background scheduler initialize under both WSGI (Gunicorn/Cloud Run) and direct execution
init_db(DB_PATH)
start_background_scheduler()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/stats", methods=["GET"])
def api_stats():
    stats = get_stats(DB_PATH)
    stats["scrape_progress"] = SCRAPE_PROGRESS
    stats["schedule"] = get_schedule_status()
    return jsonify(stats)


@app.route("/api/jobs", methods=["GET"])
def api_jobs():
    view = request.args.get("view", "matched").lower()
    only_matched = view == "matched"

    last_scraped_hours_raw = request.args.get("last_scraped_hours")
    last_scraped_hours = None
    if last_scraped_hours_raw:
        try:
            last_scraped_hours = float(last_scraped_hours_raw)
        except ValueError:
            pass
    elif view in ("last5h", "last_5_hours", "last5hours", "5h"):
        last_scraped_hours = 5.0

    min_score_raw = request.args.get("min_score")
    min_score = int(min_score_raw) if (min_score_raw and min_score_raw.isdigit()) else None

    status = request.args.get("status", "All")
    date_filter = request.args.get("date_filter", "All")
    client_region = request.args.get("client_region", "All")
    role_category = request.args.get("role_category", "All")
    arrangement = request.args.get("arrangement", "All")
    suitability_tier = request.args.get("suitability_tier", "All")
    search = request.args.get("search", "")

    default_sort = "last_scraped_at" if view in ("last5h", "last_5_hours", "last5hours", "5h") else "match_score"
    sort_by = request.args.get("sort_by", default_sort)
    sort_dir = request.args.get("sort_dir", "desc")

    jobs = query_jobs(
        only_matched=only_matched,
        min_score=min_score,
        status=status,
        date_filter=date_filter,
        last_scraped_hours=last_scraped_hours,
        client_region=client_region,
        role_category=role_category,
        arrangement=arrangement,
        suitability_tier=suitability_tier,
        search=search,
        sort_by=sort_by,
        sort_dir=sort_dir,
        db_path=DB_PATH,
    )
    return jsonify({"count": len(jobs), "view": view, "jobs": jobs})


@app.route("/api/jobs/<job_id>", methods=["GET"])
def api_get_job(job_id: str):
    job = get_job_by_id(job_id, db_path=DB_PATH)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(job)


@app.route("/api/jobs/<job_id>", methods=["PATCH", "POST"])
def api_update_job(job_id: str):
    data = request.get_json(force=True, silent=True) or {}
    status = data.get("status")
    notes = data.get("notes")
    updated = update_job_status_and_notes(job_id, status=status, notes=notes, db_path=DB_PATH)
    if not updated:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(updated)


@app.route("/api/mcp/info", methods=["GET"])
def api_mcp_info():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    python_exe = sys.executable
    mcp_script = os.path.join(base_dir, "mcp_server.py")

    claude_desktop_config = {
        "mcpServers": {
            "onlinejobs-portal": {
                "command": python_exe,
                "args": [mcp_script],
            }
        }
    }

    cursor_config = {
        "mcpServers": {
            "onlinejobs-portal": {
                "command": python_exe,
                "args": [mcp_script],
            }
        }
    }

    antigravity_config = {
        "onlinejobs-portal": {
            "command": python_exe,
            "args": [mcp_script],
        }
    }

    sse_config = {
        "mcpServers": {
            "onlinejobs-portal": {
                "url": "http://localhost:5055/sse",
            }
        }
    }

    tools = [
        {"name": "search_jobs", "description": "Search and filter high-fit jobs with score >= 70%, region, arrangement, and keywords"},
        {"name": "get_job_details", "description": "Retrieve full untruncated job description, candidate match scores, skills, and screening traps"},
        {"name": "generate_job_proposal", "description": "Generate 150-250 word grounded proposal addressing secret codes and client pain points"},
        {"name": "apply_job", "description": "Mark job as Applied in database, save notes, date, and submitted proposal text"},
        {"name": "update_job_status", "description": "Update job status (Shortlisted, Interviewing, Offer, Archived) and notes"},
        {"name": "trigger_scrape", "description": "Scrape and enrich latest jobs from OnlineJobs.ph on-demand"},
        {"name": "get_pipeline_stats", "description": "Get total scraped, matched, applied counts and scheduler state"},
        {"name": "get_candidate_profile", "description": "Get candidate verified resume facts, metrics, and anti-hallucination rules"},
    ]

    return jsonify(
        {
            "status": "ready",
            "mcp_version": "2.3.0",
            "transports": ["stdio", "sse", "streamable-http"],
            "server_path": mcp_script,
            "python_executable": python_exe,
            "tools": tools,
            "configs": {
                "claude_desktop": claude_desktop_config,
                "cursor": cursor_config,
                "antigravity": antigravity_config,
                "sse_http": sse_config,
            },
        }
    )


@app.route("/api/mcp/proposal/<job_id>", methods=["GET", "POST"])
def api_mcp_proposal(job_id: str):
    job = get_job_by_id(str(job_id).strip(), db_path=DB_PATH)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    data = request.get_json(force=True, silent=True) or {}
    custom_name = data.get("client_name") or request.args.get("client_name") or ""
    extra = data.get("extra_instructions") or request.args.get("extra_instructions") or ""
    proposal = generate_tailored_proposal(job, custom_client_name=custom_name, extra_instructions=extra)
    return jsonify(proposal)


@app.route("/api/scrape", methods=["POST"])
def api_trigger_scrape():
    if SCRAPE_PROGRESS.get("is_running"):
        return jsonify({"status": "already_running", "progress": SCRAPE_PROGRESS}), 409

    data = request.get_json(force=True, silent=True) or {}

    # Optional CRON_SECRET check when header is provided
    cron_secret = os.environ.get("CRON_SECRET", "").strip()
    req_secret = (request.headers.get("X-Cron-Secret") or data.get("cron_secret") or "").strip()
    if cron_secret and req_secret and req_secret != cron_secret:
        return jsonify({"error": "Invalid cron secret"}), 403

    pages = int(request.args.get("pages") or data.get("pages") or 10)
    region = str(request.args.get("target_region") or data.get("target_region") or "US/UK/AU")
    trigger_source = str(request.args.get("trigger_source") or data.get("trigger_source") or "web-ui")
    slot_id = data.get("slot_id") or request.args.get("slot_id")

    if slot_id:
        from datetime import datetime
        SCHEDULER_STATE["last_triggered_slot"] = f"{datetime.now().strftime('%Y-%m-%d')}_{slot_id}"
        SCHEDULER_STATE["last_triggered_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Default to synchronous execution (keeps Cloud Run CPU active across scale-to-zero)
    # unless caller explicitly requests async background execution (`sync=false`).
    sync_arg = request.args.get("sync")
    if sync_arg is not None:
        run_sync = sync_arg.lower() not in ("0", "false", "no")
    elif "sync" in data:
        run_sync = bool(data["sync"])
    else:
        run_sync = True

    if run_sync:
        try:
            result = asyncio.run(
                run_scrape(
                    num_pages=pages,
                    trigger_source=trigger_source,
                    target_region=region,
                    db_path=DB_PATH,
                )
            )
            return jsonify(result)
        except Exception as exc:
            print(f"[Sync Scrape Error] {exc}")
            return jsonify({"status": "failed", "error": str(exc), "progress": SCRAPE_PROGRESS}), 500

    def _bg():
        try:
            asyncio.run(
                run_scrape(
                    num_pages=pages,
                    trigger_source=trigger_source,
                    target_region=region,
                    db_path=DB_PATH,
                )
            )
        except Exception as exc:
            print(f"[WebUI Scrape Error] {exc}")

    threading.Thread(target=_bg, daemon=True).start()
    return jsonify({"status": "started", "progress": SCRAPE_PROGRESS})


@app.route("/api/db/sync", methods=["POST"])
def api_db_sync():
    data = request.get_json(force=True, silent=True) or {}
    direction = (data.get("direction") or request.args.get("direction") or "push").lower()
    if direction == "pull":
        ok = restore_db_from_gcs(DB_PATH)
    else:
        ok = sync_db_to_gcs(DB_PATH)
    return jsonify({"ok": ok, "direction": direction, "gcs_persistence": GCS_STATE})


@app.route("/api/scrape/status", methods=["GET"])
def api_scrape_status():
    return jsonify(
        {
            "progress": SCRAPE_PROGRESS,
            "schedule": get_schedule_status(),
        }
    )


@app.route("/api/schedule/toggle", methods=["POST"])
def api_toggle_schedule():
    data = request.get_json(force=True, silent=True) or {}
    if "enabled" in data:
        SCHEDULER_STATE["enabled"] = bool(data["enabled"])
    else:
        SCHEDULER_STATE["enabled"] = not SCHEDULER_STATE["enabled"]
    return jsonify(get_schedule_status())


if __name__ == "__main__":
    default_port = 8080 if os.environ.get("K_SERVICE") else 5050
    port = int(os.environ.get("PORT", default_port))
    host = os.environ.get("HOST", "0.0.0.0")
    print(f"\n============================================================")
    print(f" OnlineJobs.ph Enrichment & Matcher Dashboard")
    print(f" Local URL: http://localhost:{port}")
    print(f" Database : {DB_PATH}")
    print(f"============================================================\n")
    app.run(host=host, port=port, debug=False)

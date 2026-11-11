import asyncio
import os
import threading
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

try:
    from db import DB_PATH, get_connection
    from scraper import SCRAPE_PROGRESS, run_scrape
except ImportError:
    from src.db import DB_PATH, get_connection
    from src.scraper import SCRAPE_PROGRESS, run_scrape

# Distinct Peak Hours Schedule in Philippine Time (Asia/Manila, UTC+8)
# Targeting when AU, UK, and US employers actively post new roles on OnlineJobs.ph
PEAK_WINDOWS: List[Dict[str, Any]] = [
    {
        "id": "us_west_1",
        "hour": 1,
        "minute": 0,
        "time_pht": "01:00 AM PHT",
        "region": "US",
        "label": "US West Coast Morning Peak",
        "client_local_time": "09:00 AM PST / 12:00 PM EST",
        "cron_expr": "0 1 * * *",
    },
    {
        "id": "us_west_2",
        "hour": 3,
        "minute": 30,
        "time_pht": "03:30 AM PHT",
        "region": "US",
        "label": "US West Midday / US East Afternoon Peak",
        "client_local_time": "11:30 AM PST / 02:30 PM EST",
        "cron_expr": "30 3 * * *",
    },
    {
        "id": "au_1",
        "hour": 7,
        "minute": 0,
        "time_pht": "07:00 AM PHT",
        "region": "AU",
        "label": "Australia Morning Business Start (Sydney/Melbourne)",
        "client_local_time": "09:00 AM AEST / 10:00 AM AEDT",
        "cron_expr": "0 7 * * *",
    },
    {
        "id": "au_2",
        "hour": 9,
        "minute": 30,
        "time_pht": "09:30 AM PHT",
        "region": "AU",
        "label": "Australia Midday Hiring Peak",
        "client_local_time": "11:30 AM AEST / 12:30 PM AEDT",
        "cron_expr": "30 9 * * *",
    },
    {
        "id": "uk_1",
        "hour": 17,
        "minute": 0,
        "time_pht": "05:00 PM PHT",
        "region": "UK",
        "label": "UK Morning Business Start (London)",
        "client_local_time": "09:00 AM GMT / 10:00 AM BST",
        "cron_expr": "0 17 * * *",
    },
    {
        "id": "uk_2",
        "hour": 19,
        "minute": 30,
        "time_pht": "07:30 PM PHT",
        "region": "UK",
        "label": "UK Midday Hiring Peak",
        "client_local_time": "11:30 AM GMT / 12:30 PM BST",
        "cron_expr": "30 19 * * *",
    },
    {
        "id": "us_east_1",
        "hour": 21,
        "minute": 0,
        "time_pht": "09:00 PM PHT",
        "region": "US",
        "label": "US East Coast Morning Start (NY/Miami/Atlanta)",
        "client_local_time": "08:00 AM EST / 09:00 AM EDT",
        "cron_expr": "0 21 * * *",
    },
    {
        "id": "us_east_2",
        "hour": 23,
        "minute": 30,
        "time_pht": "11:30 PM PHT",
        "region": "US",
        "label": "US East Coast Midday Hiring Peak",
        "client_local_time": "10:30 AM EST / 11:30 AM EDT",
        "cron_expr": "30 23 * * *",
    },
]

SCHEDULER_STATE: Dict[str, Any] = {
    "enabled": True,
    "last_triggered_slot": None,
    "last_triggered_at": None,
}


def get_next_peak_window(now: Optional[datetime] = None) -> Dict[str, Any]:
    if now is None:
        now = datetime.now()

    candidates = []
    for slot in PEAK_WINDOWS:
        slot_dt = now.replace(hour=slot["hour"], minute=slot["minute"], second=0, microsecond=0)
        if slot_dt <= now:
            slot_dt += timedelta(days=1)
        delta_sec = int((slot_dt - now).total_seconds())
        candidates.append((delta_sec, slot_dt, slot))

    candidates.sort(key=lambda x: x[0])
    best_delta, best_dt, best_slot = candidates[0]
    hours, rem = divmod(best_delta, 3600)
    minutes, seconds = divmod(rem, 60)

    return {
        "next_window": best_slot,
        "next_run_at": best_dt.strftime("%Y-%m-%d %H:%M:%S"),
        "seconds_until": best_delta,
        "countdown_human": f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m {seconds}s",
    }


def get_schedule_status() -> Dict[str, Any]:
    now = datetime.now()
    next_info = get_next_peak_window(now)
    if not SCHEDULER_STATE.get("last_triggered_at"):
        try:
            with get_connection(DB_PATH) as conn:
                row = conn.execute(
                    """
                    SELECT trigger_source, started_at
                    FROM scrape_runs
                    WHERE status = 'completed'
                      AND (trigger_source LIKE 'github-actions:%' OR trigger_source LIKE 'peak-schedule:%')
                    ORDER BY id DESC LIMIT 1
                    """
                ).fetchone()
                if row:
                    src = row["trigger_source"] or ""
                    slot_part = src.split(":", 1)[1] if ":" in src else src
                    date_part = (row["started_at"] or "")[:10]
                    SCHEDULER_STATE["last_triggered_slot"] = f"{date_part}_{slot_part}"
                    SCHEDULER_STATE["last_triggered_at"] = row["started_at"]
        except Exception:
            pass

    return {
        "enabled": SCHEDULER_STATE["enabled"],
        "mode": "github-actions-http" if os.environ.get("K_SERVICE") else "local-daemon",
        "timezone": "Asia/Manila (PHT, UTC+8)",
        "current_time_pht": now.strftime("%Y-%m-%d %H:%M:%S"),
        "peak_windows": PEAK_WINDOWS,
        "next_peak": next_info,
        "last_triggered_slot": SCHEDULER_STATE["last_triggered_slot"],
        "last_triggered_at": SCHEDULER_STATE["last_triggered_at"],
    }


def _scheduler_loop() -> None:
    while True:
        try:
            if SCHEDULER_STATE["enabled"] and not SCRAPE_PROGRESS.get("is_running"):
                now = datetime.now()
                for slot in PEAK_WINDOWS:
                    if now.hour == slot["hour"] and now.minute == slot["minute"]:
                        slot_key = f"{now.strftime('%Y-%m-%d')}_{slot['id']}"
                        if SCHEDULER_STATE["last_triggered_slot"] != slot_key:
                            SCHEDULER_STATE["last_triggered_slot"] = slot_key
                            SCHEDULER_STATE["last_triggered_at"] = now.strftime("%Y-%m-%d %H:%M:%S")
                            print(
                                f"[Scheduler] Firing scheduled peak scrape: "
                                f"{slot['label']} ({slot['region']}) at {SCHEDULER_STATE['last_triggered_at']}"
                            )
                            asyncio.run(
                                run_scrape(
                                    num_pages=10,
                                    trigger_source=f"peak-schedule:{slot['id']}",
                                    target_region=slot["region"],
                                )
                            )
        except Exception as exc:
            print(f"[Scheduler] Error in loop: {exc}")
        time.sleep(20)


def start_background_scheduler() -> Optional[threading.Thread]:
    # On Cloud Run (K_SERVICE), background threads outside an HTTP request have their CPU
    # throttled to <1%, causing Playwright timeouts and blocking incoming GitHub Actions requests.
    if os.environ.get("K_SERVICE") and os.environ.get("ENABLE_INTERNAL_SCHEDULER", "0") != "1":
        print("[Scheduler] Cloud Run detected (K_SERVICE): disabling internal background timer; using synchronous GitHub Actions HTTP cron triggers.")
        return None
    t = threading.Thread(target=_scheduler_loop, name="PeakHoursScheduler", daemon=True)
    t.start()
    return t


if __name__ == "__main__":
    print("[Scheduler] Starting standalone US/UK/AU Peak-Hours Automation daemon...")
    print("[Scheduler] Configured peak windows (Asia/Manila PHT):")
    for w in PEAK_WINDOWS:
        print(f"  - {w['time_pht']:14s} | [{w['region']}] {w['label']} ({w['client_local_time']})")
    _scheduler_loop()

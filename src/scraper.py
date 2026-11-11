import argparse
import asyncio
import os
import re
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

try:
    from db import DB_PATH, create_scrape_run, finish_scrape_run, init_db, upsert_job
    from evaluator import evaluate_job
except ImportError:
    from src.db import DB_PATH, create_scrape_run, finish_scrape_run, init_db, upsert_job
    from src.evaluator import evaluate_job


def _load_dotenv() -> None:
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env")
    if not os.path.exists(env_path):
        env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_dotenv()

DEFAULT_EMAIL = os.environ.get("OJP_EMAIL", "")
DEFAULT_PASSWORD = os.environ.get("OJP_PASSWORD", "")
BASE_URL = "https://www.onlinejobs.ph"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)

# Shared live state for Web UI progress polling
SCRAPE_PROGRESS: Dict[str, Any] = {
    "is_running": False,
    "stage": "idle",
    "current_page": 0,
    "total_pages": 10,
    "jobs_discovered": 0,
    "jobs_enriched": 0,
    "new_jobs": 0,
    "matched_jobs": 0,
    "started_at": None,
    "last_completed_at": None,
    "last_error": None,
}


def parse_listing_card(box: Any, page_num: int) -> Optional[Dict[str, Any]]:
    """
    Extracts summary fields from a `.jobpost-cat-box` element on the search page.
    """
    link_el = box.find("a", href=re.compile(r"/jobseekers/job/"))
    if not link_el:
        return None

    href = link_el.get("href", "").strip()
    if not href:
        return None
    full_url = urljoin(BASE_URL, href)

    # Extract job_id from end of URL slug or digits
    m_id = re.search(r"-(\d+)(?:$|\?)", href) or re.search(r"/job/(\d+)", href)
    job_id = m_id.group(1) if m_id else href.split("/")[-1]

    # Title & Arrangement badge
    h4 = box.select_one("h4")
    arrangement = "Any"
    title = ""
    if h4:
        badge = h4.select_one(".badge")
        if badge:
            arrangement = badge.get_text(strip=True)
            badge.extract()
        title = h4.get_text(" ", strip=True)

    # Employer & Exact Post Date with Time
    employer = "Undisclosed"
    posted_at = ""
    posted_at_utc = ""
    meta_p = box.find("p", attrs={"data-temp": True}) or box.select_one("p.fs-13")
    if meta_p:
        posted_at = (meta_p.get("data-temp") or "").strip()
        posted_at_utc = (meta_p.get("data-temp-2") or "").strip()
        raw_meta = meta_p.get_text(" ", strip=True)
        # Format is usually: "Employer Name • Posted on 2026-11-06 16:02:19"
        if "•" in raw_meta:
            employer = raw_meta.split("•")[0].strip()
        elif "Posted on" in raw_meta:
            employer = raw_meta.split("Posted on")[0].replace("", "").strip(" -•")
        if not posted_at:
            m_date = re.search(r"Posted on\s+([\d\-:\s]+)", raw_meta)
            if m_date:
                posted_at = m_date.group(1).strip()

    # Salary
    salary = "Not specified"
    dl_badges = box.select(".badge-salary, dd.badge-salary, .badge")
    for b in dl_badges:
        txt = b.get_text(strip=True)
        if any(c in txt for c in ["$", "₱", "/month", "/hr", "/week", "Sal"]):
            salary = txt
            break

    # Description snippet (overview text)
    desc_p = box.select_one(".desc, .job-description, p.text-muted")
    description_snippet = desc_p.get_text(" ", strip=True) if desc_p else ""

    # Skills tags if any on the card
    tags = [t.get_text(strip=True) for t in box.select(".skill-badge, .badge-light")]

    return {
        "job_id": str(job_id),
        "title": title,
        "employer": employer or "Undisclosed",
        "url": full_url,
        "salary": salary,
        "arrangement": arrangement,
        "posted_at": posted_at,
        "posted_at_utc": posted_at_utc,
        "description_snippet": description_snippet,
        "skills_tags": tags,
        "page_scraped": page_num,
    }


def parse_job_detail_page(html: str) -> Dict[str, Any]:
    """
    Parses the full job posting page to extract complete untruncated description,
    employer verification stats, and explicit skills requirements.
    """
    soup = BeautifulSoup(html, "html.parser")

    # 1. Full Description
    # OnlineJobs.ph places job description in a dedicated container or card-body
    desc_container = (
        soup.select_one("#job-description")
        or soup.select_one(".job-description")
        or soup.select_one(".jobpost-details")
        or soup.select_one("div.fs-16")
    )
    if not desc_container:
        # Fallback to general content container
        desc_container = soup.select_one(".card-body") or soup.select_one("main")

    description = ""
    if desc_container:
        description = desc_container.get_text("\n", strip=True)

    # 2. Employer details & Verification
    employer = ""
    member_since = ""
    total_posts = ""
    emp_meta = soup.select_one(".employer-meta, .employer-info, .sidebar")
    if emp_meta:
        m_since = re.search(r"Member Since:?\s*([A-Za-z0-9\s,]+)", emp_meta.get_text())
        if m_since:
            member_since = m_since.group(1).strip()
        m_posts = re.search(r"Job Posts:?\s*(\d+)", emp_meta.get_text())
        if m_posts:
            total_posts = m_posts.group(1).strip()

    # 3. Hours per week & Arrangement confirmation
    hours_per_week = ""
    m_hours = re.search(r"(\d+)\s*(?:hrs?|hours?)\s*/?\s*(?:week|wk)", html, re.IGNORECASE)
    if m_hours:
        hours_per_week = m_hours.group(1)

    # 4. Detailed skills badges
    skill_badges = [
        t.get_text(strip=True)
        for t in soup.select(".badge-skill, .badge-outline-primary, .skills-container .badge")
    ]

    # 5. Salary if more detailed on view page
    salary_view = ""
    salary_el = soup.select_one(".salary-range, dd.col-sm-9")
    if salary_el and any(c in salary_el.get_text() for c in ["$", "₱"]):
        salary_view = salary_el.get_text(strip=True)

    return {
        "description": description,
        "employer_member_since": member_since,
        "employer_total_posts": total_posts,
        "hours_per_week": hours_per_week,
        "skills_tags_detailed": skill_badges,
        "salary_detailed": salary_view,
    }


async def authenticate_and_get_cookies(
    email: str = DEFAULT_EMAIL, password: str = DEFAULT_PASSWORD
) -> List[Dict[str, Any]]:
    """
    Automates login via Playwright to obtain authenticated session cookies.
    If no credentials provided, returns empty list (scraper falls back to public listings).
    """
    if not email or not password:
        print("[Auth] No OJP_EMAIL or OJP_PASSWORD provided in .env; scraping in public unauthenticated mode.")
        return []

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"],
        )
        context = await browser.new_context(
            user_agent=USER_AGENT,
            viewport={"width": 1280, "height": 800},
        )
        page = await context.new_page()

        try:
            print("[Auth] Navigating to login page...")
            await page.goto(f"{BASE_URL}/jobseekers/login", wait_until="domcontentloaded", timeout=45000)

            # Wait for login form
            await page.wait_for_selector('input[name="email"], input[type="email"]', timeout=15000)

            print(f"[Auth] Entering credentials for {email}...")
            await page.fill('input[name="email"], input[type="email"]', email)
            await page.fill('input[name="password"], input[type="password"]', password)

            # Click login button
            await page.click('button[type="submit"], input[type="submit"], .btn-login')

            # Wait for successful navigation past login
            await page.wait_for_url(lambda url: "/login" not in url, timeout=20000)
            print(f"[Auth] Successfully logged in! Current URL: {page.url}")

            cookies = await context.cookies()
            await browser.close()
            return cookies

        except Exception as exc:
            print(f"[Auth Warning] Playwright automated login failed or timed out: {exc}")
            print("[Auth] Continuing with unauthenticated scraping session.")
            await browser.close()
            return []


async def run_scrape(
    num_pages: int = 10,
    email: str = DEFAULT_EMAIL,
    password: str = DEFAULT_PASSWORD,
    trigger_source: str = "manual",
    target_region: str = "US/UK/AU",
    db_path: str = DB_PATH,
    progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> Dict[str, Any]:
    """
    Full end-to-end automation flow:
    1. Open onlinejobs.ph and authenticate (or public mode if no credentials)
    2. Scrape first `num_pages` (default 10) pages
    3. Fetch full job details for every discovered job post
    4. Evaluate & rate suitability against candidate profile
    5. Store in SQLite
    """
    if SCRAPE_PROGRESS.get("is_running"):
        return {"status": "already_running", "progress": SCRAPE_PROGRESS}

    init_db(db_path)
    run_id = create_scrape_run(trigger_source=trigger_source, target_region=target_region, db_path=db_path)

    SCRAPE_PROGRESS.update(
        {
            "is_running": True,
            "stage": "authenticating",
            "current_page": 0,
            "total_pages": num_pages,
            "jobs_discovered": 0,
            "jobs_enriched": 0,
            "new_jobs": 0,
            "matched_jobs": 0,
            "started_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "last_error": None,
        }
    )

    try:
        print(f"[Scraper] Initializing session...")
        cookies = await authenticate_and_get_cookies(email, password)
        if cookies:
            print(f"[Scraper] Authenticated successfully ({len(cookies)} session cookies acquired).")

        headers = {"User-Agent": USER_AGENT}
        discovered_jobs: Dict[str, Dict[str, Any]] = {}
        pages_scraped_count = 0

        async with httpx.AsyncClient(
            cookies=cookies,
            headers=headers,
            follow_redirects=True,
            timeout=30.0,
        ) as client:
            # Step 1: Scrape first 10 listing pages
            SCRAPE_PROGRESS["stage"] = "scraping_pages"
            for page_num in range(1, num_pages + 1):
                SCRAPE_PROGRESS["current_page"] = page_num
                offset = (page_num - 1) * 30
                page_url = (
                    f"{BASE_URL}/jobseekers/jobsearch"
                    if offset == 0
                    else f"{BASE_URL}/jobseekers/jobsearch/{offset}"
                )

                resp = await client.get(page_url)
                soup = BeautifulSoup(resp.text, "html.parser")
                boxes = soup.select(".jobpost-cat-box")

                # OnlineJobs.ph caps the unfiltered default feed around ~245 items (page 9).
                # If page returns 0 items, break early.
                if not boxes:
                    print(f"[Scraper] Page {page_num} returned 0 cards. Reached end of default feed.")
                    break

                pages_scraped_count += 1
                for box in boxes:
                    card = parse_listing_card(box, page_num)
                    if card and card["job_id"] not in discovered_jobs:
                        discovered_jobs[card["job_id"]] = card

                SCRAPE_PROGRESS["jobs_discovered"] = len(discovered_jobs)
                print(
                    f"[Scraper] Scraped page {page_num}/{num_pages} ({len(boxes)} cards on page). Total discovered: {len(discovered_jobs)}"
                )

                if progress_callback:
                    progress_callback(dict(SCRAPE_PROGRESS))

                # Polite delay between page requests
                await asyncio.sleep(0.5)

            # Step 2: Concurrently fetch full details for all discovered jobs
            SCRAPE_PROGRESS["stage"] = "enriching_details"
            print(f"[Scraper] Fetching full details for {len(discovered_jobs)} discovered jobs...")

            semaphore = asyncio.Semaphore(5)  # 5 concurrent detail fetches to avoid rate limits
            total_discovered = len(discovered_jobs)
            enriched_counter = 0

            async def fetch_detail(job_id: str, job_summary: Dict[str, Any]) -> Dict[str, Any]:
                nonlocal enriched_counter
                async with semaphore:
                    try:
                        resp = await client.get(job_summary["url"])
                        if resp.status_code == 200:
                            details = parse_job_detail_page(resp.text)
                            job_summary["description"] = details["description"] or job_summary["description_snippet"]
                            job_summary["employer_member_since"] = details["employer_member_since"]
                            job_summary["employer_total_posts"] = details["employer_total_posts"]
                            job_summary["hours_per_week"] = details["hours_per_week"]
                            if details.get("salary_detailed"):
                                job_summary["salary"] = details["salary_detailed"]
                            if details.get("skills_tags_detailed"):
                                job_summary["skills_tags"] = list(
                                    set(job_summary["skills_tags"] + details["skills_tags_detailed"])
                                )
                    except Exception as exc:
                        print(f"[Detail Error] Could not fetch details for job {job_id}: {exc}")
                        job_summary["description"] = job_summary["description_snippet"]

                    enriched_counter += 1
                    SCRAPE_PROGRESS["jobs_enriched"] = enriched_counter
                    return job_summary

            detail_tasks = [fetch_detail(jid, jdata) for jid, jdata in discovered_jobs.items()]
            full_jobs = await asyncio.gather(*detail_tasks)

            # Step 3: Evaluate suitability, rate against candidate profile, and upsert into SQLite
            SCRAPE_PROGRESS["stage"] = "evaluating_and_saving"
            new_jobs_count = 0
            matched_jobs_count = 0

            for job_data in full_jobs:
                evaluation = evaluate_job(job_data)
                job_data.update(evaluation)

                is_new = upsert_job(job_data, db_path=db_path)
                if is_new:
                    new_jobs_count += 1
                if job_data.get("is_matched", 0) == 1:
                    matched_jobs_count += 1

            SCRAPE_PROGRESS["new_jobs"] = new_jobs_count
            SCRAPE_PROGRESS["matched_jobs"] = matched_jobs_count
            SCRAPE_PROGRESS["stage"] = "completed"
            SCRAPE_PROGRESS["is_running"] = False
            SCRAPE_PROGRESS["last_completed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            finish_scrape_run(
                run_id=run_id,
                pages_scraped=pages_scraped_count,
                jobs_found=len(full_jobs),
                new_jobs=new_jobs_count,
                matched_jobs=matched_jobs_count,
                status="completed",
                db_path=db_path,
            )

            print(
                f"[Scraper] Completed! Discovered: {len(full_jobs)}, New: {new_jobs_count}, Matched: {matched_jobs_count}."
            )
            return {
                "status": "success",
                "pages_scraped": pages_scraped_count,
                "jobs_found": len(full_jobs),
                "new_jobs": new_jobs_count,
                "matched_jobs": matched_jobs_count,
            }

    except Exception as exc:
        print(f"[Scraper Critical Error] {exc}")
        SCRAPE_PROGRESS["is_running"] = False
        SCRAPE_PROGRESS["stage"] = "error"
        SCRAPE_PROGRESS["last_error"] = str(exc)
        finish_scrape_run(
            run_id=run_id,
            pages_scraped=0,
            jobs_found=0,
            new_jobs=0,
            matched_jobs=0,
            status="failed",
            error_message=str(exc),
            db_path=db_path,
        )
        raise exc


def main():
    parser = argparse.ArgumentParser(description="OnlineJobs.ph Job Scraper & Enricher")
    parser.add_argument("--pages", type=int, default=10, help="Number of pages to scrape (default: 10)")
    parser.add_argument("--db-path", default=DB_PATH, help="Path to SQLite database")
    parser.add_argument("--region", default="US/UK/AU", help="Target region label")
    args = parser.parse_args()

    asyncio.run(run_scrape(num_pages=args.pages, db_path=args.db_path, target_region=args.region))


if __name__ == "__main__":
    main()

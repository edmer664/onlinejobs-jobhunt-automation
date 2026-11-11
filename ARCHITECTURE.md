# JobHunt OpenSource: Deep-Dive Architecture Specification

This document provides the definitive architectural specification for the **JobHunt OpenSource** platform. It details the system context, component decomposition, data contracts, zero-cost execution model, and security architecture.

---

## 1. System Context & Decomposition

The system is organized into five decoupled architectural layers:

```text
+---------------------------------------------------------------------------------------+
|                                  1. CLIENT / AGENT TIER                               |
|   Claude Desktop  |  Cursor IDE  |  Windsurf  |  Web Browser  |  POSIX/PowerShell CLI  |
+---------------------------------------------------------------------------------------+
                                           |
                                           v
+---------------------------------------------------------------------------------------+
|                               2. INTERFACE ADAPTER TIER                               |
|   mcp_server.py (stdio / sse)  |  app.py (Flask Web UI)  |  skills.sh (Agent Runner)  |
+---------------------------------------------------------------------------------------+
                                           |
                                           v
+---------------------------------------------------------------------------------------+
|                                   3. CORE ENGINE TIER                                 |
|  ProfileManager  |  Evaluator  |  ProposalEngine  |  PlaywrightScraper  |  Scheduler  |
+---------------------------------------------------------------------------------------+
                                           |
                                           v
+---------------------------------------------------------------------------------------+
|                                4. EXECUTION ROUTER TIER                               |
|    Route A: email_dispatcher.py   |   Route C: form_automator.py   |   Route B: Guard |
+---------------------------------------------------------------------------------------+
                                           |
                                           v
+---------------------------------------------------------------------------------------+
|                              5. PERSISTENCE & DATA TIER                               |
|             SQLite3 (WAL Mode, 32 Columns, 6 Indexes)  |  seeds/sample_jobs.json      |
+---------------------------------------------------------------------------------------+
```

---

## 2. Core Pipelines & Data Flow

### A. Scrape & Ingest Pipeline
1. **Trigger**: An automated scheduler (`scheduler.py`), manual user request via Web UI (`app.py`), or agent MCP tool (`trigger_scrape`) initiates a run.
2. **Extraction**: `scraper.py` initiates an HTTPX session or launches headless Playwright. If credentials (`OJP_EMAIL`, `OJP_PASSWORD`) are absent, it operates in unauthenticated public search mode.
3. **Parse & Normalize**: HTML listings are parsed via BeautifulSoup into standardized job dictionaries containing `job_id`, `title`, `employer`, `salary`, `arrangement`, `posted_at`, and `description`.
4. **Enrichment Hook**: Before database insertion, each job is synchronously evaluated by `evaluator.py`.
5. **Persistence**: `db.upsert_job()` inserts or updates the record in SQLite WAL mode. Existing user status (e.g. `Applied`, `Shortlisted`) and user notes are preserved across updates.

### B. Suitability Evaluation & Scoring Pipeline
`src/evaluator.py` implements a multi-factor dynamic scoring algorithm:

$$\text{Final Score} = \text{Base} + \text{Skills} + \text{ArrangementBonus} + \text{RegionBonus} - \text{Gaps} - \text{SeniorityPenalty} - \text{RedFlags}$$

```text
[Raw Job Description]
         |
         v
+------------------------+
| Client Region & Peak   | ---> Detects AU, UK, US, or Global
| Window Detection       |      Maps posting time to PHT Peak Window
+------------------------+
         |
         v
+------------------------+
| Hard Mismatch Check    | ---> Checks dealbreaker patterns (e.g., Senior Fullstack,
+------------------------+      Director). If matched: score capped at 38%.
         |
         v
+------------------------+
| Role Classification    | ---> Matches title/tags against configured categories
| (Base Fit: 18 - 52)    |      (Virtual Assistant, Sourcing, Data/Bookkeeping, etc.)
+------------------------+
         |
         v
+------------------------+
| Candidate Skills Match | ---> Adds weighted points per matched skill (max 40 pts)
+------------------------+      Title matches receive bonus weighting (+2 pts)
         |
         v
+------------------------+
| Gap & Penalty Analysis | ---> Deducts gap penalties (max 38 pts), seniority/exp
+------------------------+      penalties (-12 to -24 pts), and red flag penalties (max 12)
         |
         v
+------------------------+
| Final Score & Tiering  | ---> Clamped between 12% and 98%
+------------------------+      Tiers: Excellent (>=80), Good (65-79), Moderate (50-64), Low (<50)
```

### C. Proposal Generation & Screening Trap Audit Pipeline
`src/proposal_engine.py` operates under strict anti-hallucination constraints:
1. **Screening Trap Audit**: Scans the text for secret code phrases (e.g. `"put 'Banana' in the subject"`), numbered mandatory questions, and hardware/speedtest requests.
2. **Subject Construction**: Formats the subject line to include the secret code immediately:
   `[Job Title] Application - [Candidate Name] [Secret Code] | [Strongest Micro-Proof Hook]`
3. **Drafting (150–250 Words Max)**:
   - **Line 1**: Secret code and direct answers to screening questions.
   - **Paragraph 1**: Empathy hook addressing the employer's core business problem.
   - **Paragraph 2**: 2–3 fact-grounded proof bullets citing verified candidate metrics.
   - **Workstation Logistics**: Reassurance confirming dedicated workstation, high-speed fiber internet, mobile data backup, and client timezone availability.
   - **Call to Action**: Low-friction invite for a 10-minute discovery chat or trial task.

### D. Multi-Channel Execution & Connect Point Decision Pipeline
`execution/router.py` evaluates the job listing to determine the optimal, cost-free submission route:
- **Route A (`EMAIL`)**: Employer explicitly requests direct email submission. Connect points spent on OLJ = 0. Handled by `execution/email_dispatcher.py`, which generates a timestamped `.eml` audit file and optionally dispatches via SMTP.
- **Route C (`EXTERNAL_FORM`)**: Employer specifies an external Google Form, ClickUp, RecruitCRM, or Airtable link. Connect points spent on OLJ = 0. Handled by `execution/form_automator.py` via Playwright.
- **Route B (`PLATFORM`)**: Standard on-platform listing. Connect points are allocated according to match tier:
  - High Match ($\ge 80\%$): 20 connects (maximum visibility bid).
  - Good Match (70–79%): 10 connects.
  - Transferable Match (60–69%): 8 connects.
  - Low Match ($< 60\%$): 0 connects (application withheld).
- **Mutual Exclusivity Rule**: Applications are executed via exactly one channel. The engine forbids double-applying on both email and platform.

---

## 3. Core Component Deep Dive

### ProfileManager (`src/config_loader.py`)
- **Schema**: Enforces `config/profile.schema.json`.
- **Precedence**: Checks for `config/profile.yaml`, then `config/profile.json`. If neither is found, safely falls back to `config/profile.example.json` with a console warning.
- **Safety**: Isolates candidate personal information from the codebase.

### MCPServer (`src/mcp_server.py`)
Built on the Model Context Protocol (MCP 2.x) standard:
- **Tools**:
  - `search_jobs`: Query and filter database jobs by minimum score, region, category, status, arrangement, and time range.
  - `get_job_details`: Retrieve un-truncated description, employer stats, and screening trap audit.
  - `generate_job_proposal`: Build 150–250 word fact-grounded cover letter.
  - `apply_job`: Update status to `Applied`, append timestamped proposal and submission notes.
  - `update_job_status`: Transition job status (`Shortlisted`, `Interviewing`, `Offer`, `Rejected`, `Archived`).
  - `trigger_scrape`: Run on-demand scraper run (pages, target region).
  - `get_pipeline_stats`: Pipeline health metrics and scheduler status.
  - `get_candidate_profile`: Verified candidate ground truth and logistics data.
- **Resources**: Exposes URIs `jobs://matched`, `jobs://recent-5h`, `jobs://applied`, `candidate://profile`, and `portal://stats`.
- **Transports**: Supports `stdio` (IDE agents), `sse` (network clients), and `streamable-http`.

### Scheduler (`src/scheduler.py`)
Synchronizes with 8 peak hiring windows in Philippine Time (PHT, UTC+8):
1. `us_west_1` (01:00 PHT): US West Coast Morning (09:00 AM PST)
2. `us_west_2` (03:30 PHT): US West Midday / US East Afternoon (11:30 AM PST / 02:30 PM EST)
3. `au_1` (07:00 PHT): Australia Morning Business Start (09:00 AM AEST)
4. `au_2` (09:30 PHT): Australia Midday Hiring Peak (11:30 AM AEST)
5. `uk_1` (17:00 PHT): UK Morning Business Start (09:00 AM GMT)
6. `uk_2` (19:30 PHT): UK Midday Hiring Peak (11:30 AM GMT)
7. `us_east_1` (21:00 PHT): US East Coast Morning Start (08:00 AM EST)
8. `us_east_2` (23:30 PHT): US East Coast Midday Hiring Peak (10:30 AM EST)

---

## 4. Zero-Cost Infrastructure Model

| Operational Area | Standard Enterprise SaaS Cost | JobHunt OpenSource Cost | Implementation Mechanism |
|---|---|---|---|
| **Database Tier** | $15–$50 / month (Hosted Postgres) | **$0.00** | Embedded SQLite 3 in WAL mode with normal sync. Zero network latency, zero hosting cost. |
| **Compute / Host** | $10–$25 / month (Cloud VPS) | **$0.00** | Local Python runtime or free GitHub Actions cron runner (`ubuntu-latest`). |
| **Scraper Automation** | $20–$100 / month (Cloud Scraper API) | **$0.00** | Local Playwright Chromium + HTTPX scraping directly against public endpoints. |
| **Job Board Tokens** | $10–$30 / month (Connect points) | **$0.00** | Route A (Email) and Route C (External Forms) routing bypasses platform tokens entirely. |
| **Total Cost** | **$55 – $205 / month** | **$0.00 / month** | **100% Free & Open-Source** |

---

## 5. Security, Sanitization & Privacy Model

1. **Zero-PII Storage**:
   - The repository contains 0 hardcoded personal candidate details.
   - Candidate configuration is isolated in gitignored files: `config/profile.yaml`, `config/resume.pdf`, and `.env`.
   - `tests/test_sanitization.py` executes base64-encoded keyword and regex scans during CI to prevent personal names, personal emails, personal phone numbers, or platform passwords from being committed.
2. **Credential Sanitization**:
   - Plaintext passwords and private tokens are prohibited.
   - `.env.example` provides non-functional dummy credentials.
3. **Execution Auditing**:
   - Outbound email applications generate local `.eml` files in `execution/artifacts/` prior to dispatch, providing full human-in-the-loop auditability.

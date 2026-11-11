# Zero-Cost Deployment & Automation Guide

## 1. Executive Summary & $0.00 Cost Breakdown

`jobhunt_opensource` is engineered from the ground up for **100% zero-cost operation**. Every capability—from multi-page scraping, suitability scoring, and anti-hallucination proposal drafting to automated multi-channel job submissions—runs without subscription fees, cloud database bills, or on-platform connect charges.

### Complete Cost Accounting Matrix

| Infrastructure Component | Commercial / Cloud Alternative | `jobhunt_opensource` Solution | Monthly Cost |
|---|---|---|---|
| **Data Persistence** | Managed PostgreSQL / Supabase ($25–$50/mo) | Local SQLite3 in WAL mode | **$0.00** |
| **Web Dashboard UI** | Vercel / Heroku / AWS ECS ($15–$40/mo) | Local Flask server (Port 5050) | **$0.00** |
| **AI Agent Interface** | Hosted API Gateway / Cloud MCP ($20/mo) | Native MCP stdio / SSE (Port 5055) | **$0.00** |
| **Cloud Automation** | AWS Lambda / Cloud Run / Celery ($10–$30/mo) | GitHub Actions Scheduled Cron | **$0.00** |
| **Artifact / DB Storage** | AWS S3 / Google Cloud Storage ($5/mo) | GitHub Actions 30-day Run Artifacts | **$0.00** |
| **Platform Connects** | OnlineJobs.ph paid connects ($10–$50/pack) | Route A (Email) + Route C (Form) bypass | **$0.00** |
| **Total Operational Cost** | **$70 – $190 / month** | **Self-Hosted Open-Source** | **$0.00** |

---

## 2. Architectural Pillars of Zero-Cost Automation

```text
+---------------------------------------------------------------------------------------+
|                                    User / AI Agent                                    |
+---------------------------------------------------------------------------------------+
        |                                   |                                   |
        v                                   v                                   v
[MCP Server (stdio/sse)]           [Web Dashboard (Flask)]             [skills.sh CLI]
  8 Tools, 5 Resources              Local UI & Live Progress            Install & Run Skills
  (Port 5055, $0.00)                 (Port 5050, $0.00)                  (Local CLI, $0.00)
        |                                   |                                   |
        +-----------------------------------+-----------------------------------+
                                            |
                                            v
                +-------------------------------------------------------+
                |                      Core Engine                      |
                | - ProfileManager (config/profile.yaml & validation)   |
                | - Evaluator (Dynamic Suitability & Region Matcher)    |
                | - ProposalEngine (150-250 Word Trap-Audited Drafter)  |
                | - PlaywrightScraper (Auth + Public Fallback Modes)    |
                | - Scheduler (AU, UK, US Peak Hiring Windows)          |
                +-------------------------------------------------------+
                                            |
                                            v
                +-------------------------------------------------------+
                |                    Execution Layer                    |
                | - Route A: Direct Email Dispatch (SMTP / .eml audit)  |
                | - Route C: External Forms Automation (Playwright)     |
                | - Route B: On-Platform (Zero-Connect Cost Guardrail)  |
                +-------------------------------------------------------+
                                            |
                                            v
                +-------------------------------------------------------+
                |               Persistence & Data Tier                 |
                | - SQLite3 (WAL Mode, Concurrency-Safe, Auto-Init)     |
                | - Seed Fixtures (seeds/sample_jobs.json)              |
                | - GitHub Actions Run Artifacts (500 MB Free Tier)     |
                +-------------------------------------------------------+
```

### Pillar 1: Local-First Persistence & Compute
- **Zero Database Fees**: High-performance SQLite3 configured with Write-Ahead Logging (`WAL`), concurrency-safe busy timeouts, and indexed queries. Eliminates paid database services.
- **Zero API Gateway Fees**: The Model Context Protocol (MCP) server provides both standard input/output (`stdio`) transport for direct IDE integration and Server-Sent Events (`SSE`) on `http://localhost:5055/sse`.

### Pillar 2: Native Free Cloud Automation (GitHub Actions)
- **Zero Cloud Hosting Fees**: GitHub Actions provides **2,000 free minutes per month** on `ubuntu-latest` runners for all accounts.
- **Lightweight Scrape Footprint**: A scheduled 5-page crawl and evaluation pass completes in ~40–60 seconds on `ubuntu-latest`.
- **Monthly Usage Calculation**:
  $$\text{3 runs/day} \times 30\text{ days} = 90\text{ runs/month}$$
  $$90\text{ runs} \times 1\text{ minute} = 90\text{ runner minutes/month}$$
  $$\text{Quota Consumed}: \frac{90}{2,000} = 4.5\% \quad (\mathbf{95.5\% \text{ safety margin remaining}})$$

### Pillar 3: Zero-Connect Job Application Routing
- **OnlineJobs.ph Connect Preservation**: Applying on-platform requires purchasing connect packs. `jobhunt_opensource` enforces strict routing guardrails in `execution/router.py`:
  - **Route A (Direct Email)**: Extracts employer contact emails from job posts, screening prompts, and external contact badges. Submits via free SMTP or drafts local `.eml` audit files ($0.00).
  - **Route C (External Forms)**: Detects off-platform application forms (Google Forms, ClickUp, Typeform, RecruitCRM) and automates truthful form completion via Playwright ($0.00).
  - **Route B (On-Platform)**: Automatically blocked or routed to human review with zero automated points spent ($0.00).

---

## 3. Deployment Modes

### Mode 1: Local Interactive Workstation (Zero-Cost Default)
Run both the Flask Web UI and the MCP Server concurrently on your local development machine.

#### Launch on Linux / macOS:
```bash
chmod +x scripts/*.sh
./scripts/start_all.sh
```

#### Launch on Windows:
```cmd
scripts\start_all.bat
```

#### Exposed Local Endpoints:
- **Web UI & REST API**: `http://localhost:5050`
- **MCP Server (SSE Transport)**: `http://localhost:5055/sse`

---

### Mode 2: AI Coding Agent Integration (stdio Transport)
Connect your AI coding assistants (Claude Desktop, Cursor, Antigravity, Windsurf, Cline) directly to the MCP server with zero network overhead.

#### Launcher Command:
- Linux / macOS: `./scripts/run_mcp_stdio.sh`
- Windows: `scripts\run_mcp_stdio.bat`

#### Example `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "jobhunt-portal": {
      "command": "python",
      "args": ["-m", "src.mcp_server", "--transport", "stdio"],
      "cwd": "/path/to/jobhunt_opensource"
    }
  }
}
```

---

### Mode 3: Local Background Scheduling

Automate scraping on your workstation during peak hiring windows across global regions:
- **AU Morning Peak**: 23:00 UTC (07:00 AWST / 10:00 AEST / 07:00 PHT)
- **UK Morning Peak**: 08:00 UTC (08:00 GMT / 09:00 BST / 16:00 PHT)
- **US Morning Peak**: 14:00 UTC (09:00 EST / 06:00 PST / 22:00 PHT)

#### Linux / macOS Crontab Setup:
```bash
# Install scheduled crontab entries
./scripts/setup_cron.sh --install

# View active entries
./scripts/setup_cron.sh --list

# Remove entries
./scripts/setup_cron.sh --remove
```

#### Windows Task Scheduler Setup:
```powershell
# Register scheduled tasks (in PowerShell as Administrator or standard user)
.\scripts\register_task_scheduler.ps1 -Action Register

# Check installation status
.\scripts\register_task_scheduler.ps1 -Action Status

# Remove scheduled tasks
.\scripts\register_task_scheduler.ps1 -Action Unregister
```

---

### Mode 4: 100% Free Cloud Automation (GitHub Actions)

Deploy serverless scheduled scraping to GitHub's free cloud infrastructure. No servers to maintain, 0 hosting costs.

#### 1. Workflow Configuration (`.github/workflows/scheduled_scrape.yml`):
- Runs automatically at `23:00 UTC`, `08:00 UTC`, and `14:00 UTC`.
- Allows manual on-demand execution via GitHub Actions **Run workflow** button with configurable pages and region filters.
- Uses `ubuntu-latest` with Python 3.12 caching.

#### 2. Optional GitHub Secrets Configuration:
If you have an OnlineJobs.ph account, navigate to **Settings > Secrets and variables > Actions** in your repository and set:
- `OJP_EMAIL`: Your account email address.
- `OJP_PASSWORD`: Your account password.

> **Public Unauthenticated Fallback**: If these secrets are not configured, the scraper automatically runs in public unauthenticated mode, extracting listings and calculating suitabilities without credentials.

#### 3. Monitoring & Artifacts:
- **Run Summary**: Generates a Markdown report in `$GITHUB_STEP_SUMMARY` detailing jobs found, tier distributions, and top matches.
- **Database Artifact**: Automatically uploads `jobs.db` as a downloadable run artifact retained for 30 days.

---

### Mode 5: Containerized Deployment (Docker Compose)

Deploy in an isolated container environment on any local machine, NAS, or home server.

#### 1. Build and Run:
```bash
docker compose up -d --build
```

#### 2. Verify Health:
```bash
docker compose ps
docker compose logs -f
```

The container includes a native healthcheck querying `http://localhost:5050/api/stats` and persists all data to `./jobs.db`, `./config`, and `./logs`.

---

## 4. Operational Best Practices

1. **Pre-Flight Validation**:
   Always validate candidate profile configurations before initiating scheduled automation:
   ```bash
   python tools/validate_profile.py --config config/profile.yaml
   ```

2. **Database Backup**:
   SQLite WAL mode allows safe atomic backups while services are running:
   ```bash
   python -c "import sqlite3; s=sqlite3.connect('jobs.db'); b=sqlite3.connect('jobs_backup.db'); s.backup(b); b.close(); s.close()"
   ```

3. **Log Rotation**:
   All scripts append output to `logs/cron.log`. Review logs regularly to monitor scrape yields and application routing outcomes.

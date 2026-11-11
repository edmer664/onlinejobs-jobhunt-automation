# JobHunt OpenSource: Autonomous Remote Job Enrichment & Proposal Engine

[![CI](https://github.com/your-username/jobhunt_opensource/actions/workflows/test.yml/badge.svg)](https://github.com/your-username/jobhunt_opensource/actions/workflows/test.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Cost: $0.00](https://img.shields.io/badge/Operating%20Cost-%240.00%20%2F%20mo-success.svg)](#zero-cost-deployment-architecture)
[![MCP 2.x](https://img.shields.io/badge/MCP-2.x%20Ready-purple.svg)](https://modelcontextprotocol.io/)

A decoupled, production-grade, zero-cost remote job hunt and proposal generation ecosystem built for AI coding agents (Claude, Cursor, Windsurf, Antigravity) and human jobseekers.

Automate the discovery, suitability scoring, screening trap detection, fact-grounded proposal drafting, and multi-channel submission of remote jobs on OnlineJobs.ph and global platforms—without spending platform connect points or risking AI hallucinations.

---

## 🏛️ System Architecture

```text
+---------------------------------------------------------------------------------------+
|                                    User / AI Agent                                    |
+---------------------------------------------------------------------------------------+
        |                                   |                                   |
        v                                   v                                   v
[MCP Server (stdio/sse)]           [Web Dashboard (Flask)]             [skills.sh CLI]
  8 Tools, 5 Resources              Local UI & Live Progress            Install & Run Skills
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
                | - Optional GCS Sync (for Serverless Containers)       |
                +-------------------------------------------------------+
```

---

## ✨ Key Features Matrix

| Feature | Description | Technical Implementation |
|---|---|---|
| **Dynamic Suitability Scoring** | Computes 0–100% suitability match against candidate skills, role categories, and client timezone. | `src/evaluator.py` dynamically loads `config/profile.yaml`, penalizes gaps/seniority, and caps hard mismatches at 38%. |
| **Anti-Hallucination Proposal Engine** | Generates concise (150–250 word) cover letters grounded strictly in verified profile facts. | `src/proposal_engine.py` audits screening traps, answers secret codes, and addresses client pain points with zero fluff. |
| **Screening Trap Audit** | Scans job descriptions for mandatory questions, typing tests, speedtests, and hidden code words. | Multi-pattern regex engine detects secret keywords (e.g., `"Banana"`, `"BOOKED"`) and guarantees placement in line 1. |
| **SQLite WAL Persistence** | Thread-safe, process-safe local database with zero external database dependencies. | `src/db.py` configures `PRAGMA journal_mode=WAL;` across 32 columns and 6 performance-tuned indexes. |
| **Multi-Channel Execution** | Automatically routes applications through direct email, external forms, or on-platform modals. | `execution/router.py` enforces single-channel execution; Route A (`.eml` audit/SMTP) & Route C (Playwright forms). |
| **Zero-Connect Cost Guardrail** | Guarantees $0.00 spent on platform tokens by prioritizing external direct application routes. | Automatically routes to Route A (Email) or Route C (External Forms), conserving 100% of platform connects. |
| **Model Context Protocol (MCP)** | Exposes 8 tools, 5 resources, and 1 prompt to AI agents via stdio, SSE, or streamable-http. | `src/mcp_server.py` implements MCP 2.x standard for seamless integration with Claude Desktop, Cursor, and Windsurf. |
| **Multi-Peak Regional Scheduler** | Aligns automated crawls with peak employer hiring hours across AU, UK, and US timezones. | `src/scheduler.py` maps 8 distinct windows (01:00, 03:30, 07:00, 09:30, 17:00, 19:30, 21:00, 23:30 PHT). |
| **Packaged Skill & `skills.sh`** | Single-command portable skill installer for agent environments. | Exposes `/onlinejobs-proposal-generator` with standardized YAML frontmatter for `.agents`, `.cursor`, and `.claude`. |

---

## 💰 Zero-Cost Deployment Architecture

JobHunt OpenSource is intentionally engineered for a **$0.00/month operational footprint**:

1. **Local Execution Tier ($0.00)**: Runs entirely on your local machine using Python 3.12+ and SQLite WAL mode. No managed database fees, no server hosting bills, and no third-party API subscription mandates.
2. **Free Cloud Automation ($0.00)**: Uses native GitHub Actions scheduled workflows (`.github/workflows/scheduled_scrape.yml`) on free Ubuntu runners. Running 3 crawls per day uses ~60 minutes/month out of your 2,000 free monthly GitHub Actions minutes.
3. **Application Cost Guardrail ($0.00)**: By identifying direct employer emails (Route A) and external application forms (Route C, e.g. Google Forms, ClickUp), applications bypass platform connect requirements entirely, preserving your connects for unrouted roles.

---

## ⚡ Quickstart in 3 Commands

```bash
# 1. Clone the repository and install dependencies
git clone https://github.com/your-username/jobhunt_opensource.git && cd jobhunt_opensource
python -m venv .venv && source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 2. Configure environment and validate candidate profile
cp .env.example .env && cp config/profile.example.yaml config/profile.yaml
python tools/validate_profile.py

# 3. Seed sample data and launch services
python tools/seed_db.py --seed-file seeds/sample_jobs.json --reset
python src/app.py
```

Open your browser to **`http://localhost:5050`** to inspect the Web Dashboard!

---

## 🤖 AI Coding Agent Integration (MCP)

To connect JobHunt OpenSource with **Claude Desktop**, **Cursor**, **Antigravity**, or **Windsurf**, add the following stdio server configuration to your agent config file:

```json
{
  "mcpServers": {
    "onlinejobs-portal": {
      "command": "python",
      "args": ["src/mcp_server.py", "--transport", "stdio"],
      "cwd": "/path/to/jobhunt_opensource"
    }
  }
}
```

### Available MCP Tools & Resources

- **Tools (8)**: `search_jobs`, `get_job_details`, `generate_job_proposal`, `apply_job`, `update_job_status`, `trigger_scrape`, `get_pipeline_stats`, `get_candidate_profile`.
- **Resources (5)**: `jobs://matched`, `jobs://recent-5h`, `jobs://applied`, `candidate://profile`, `portal://stats`.
- **Prompt (1)**: `find_and_apply_flow` (interactive multi-step application workflow).

---

## 📁 Project Layout

```text
jobhunt_opensource/
├── .github/workflows/        # CI test suite, scheduled scraper cron, pages deploy
├── config/
│   ├── .env.example          # Clean environment variable template
│   ├── profile.schema.json   # JSON Schema for candidate validation
│   ├── profile.example.yaml  # Reference YAML candidate profile
│   ├── profile.example.json  # Reference JSON candidate profile
│   └── cv.example.md         # Reference Markdown CV template
├── src/                      # Core automation engine
│   ├── app.py                # Flask Web UI & REST API (port 5050)
│   ├── config_loader.py      # Profile loader and fallback manager
│   ├── db.py                 # SQLite WAL persistence & query engine
│   ├── evaluator.py          # Suitability scoring & region detector
│   ├── proposal_engine.py    # Anti-hallucination proposal generator
│   ├── scraper.py            # Playwright + HTTPX scraping engine
│   ├── scheduler.py          # Multi-peak hiring window scheduler
│   └── mcp_server.py         # Model Context Protocol 2.x server (port 5055)
├── execution/                # Multi-channel execution layer
│   ├── router.py             # Channel selection & connect points decision
│   ├── email_dispatcher.py   # Route A: SMTP dispatcher & .eml audit logger
│   └── form_automator.py     # Route C: Playwright external forms engine
├── skills/                   # Packaged skills
│   └── onlinejobs-proposal-generator/SKILL.md
├── seeds/                    # Synthetic sanitized test fixtures
│   └── sample_jobs.json      # 15 synthetic jobs across all fit tiers
├── tools/                    # Validation & CLI utilities
│   ├── validate_profile.py   # Pre-flight candidate profile validator
│   └── seed_db.py            # Database populator & reset CLI
├── scripts/                  # Runnable startup and scheduling scripts
│   ├── start_all.bat/.sh     # Dual launcher for Web UI + MCP SSE
│   ├── run_mcp_stdio.bat/.sh # Stdio launcher for AI agent IDEs
│   ├── register_task_scheduler.ps1 # Windows Task Scheduler installer
│   └── setup_cron.sh         # Linux/macOS crontab installer
├── tests/                    # Comprehensive unit, E2E & sanitization tests
├── AGENT_SETUP_PROMPT.md     # 1-click copy-paste prompt for AI coding agents
├── ARCHITECTURE.md           # In-depth architectural specification
├── SETUP.md                  # Comprehensive setup & configuration guide
├── CONTRIBUTING.md           # Contribution guidelines & code style
└── LICENSE                   # MIT License
```

---

## 🔒 Security & Privacy (0-PII Guarantee)

This repository enforces a **strict Zero-PII (Personally Identifiable Information) guarantee**:
- All candidate profiles and resumes are stored in gitignored local files (`config/profile.yaml`, `config/resume.pdf`).
- Automated tests (`tests/test_sanitization.py`) scan every commit to ensure 0 instances of personal names, emails, phone numbers, or credentials enter source control.
- All application artifacts (`.eml` audit files) are written exclusively to gitignored local folders (`execution/artifacts/`).

---

## 📄 License

This project is open-source software licensed under the [MIT License](LICENSE).
Copyright (c) 2026 Open Source Contributors.

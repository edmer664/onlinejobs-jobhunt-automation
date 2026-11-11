# JobHunt OpenSource: Complete Installation & Setup Guide

This guide walks you step-by-step through installing, configuring, validating, seeding, and running **JobHunt OpenSource** on Windows, macOS, or Linux.

---

## 📋 Prerequisites

Before starting, ensure your system meets these requirements:
- **Python**: Version 3.12 or newer (`python --version` or `python3 --version`)
- **Git**: Version 2.30+ (`git --version`)
- **Disk Space**: At least 500 MB (includes optional Playwright browser binaries)
- **Terminal**: PowerShell / Command Prompt (Windows) or Bash / Zsh (Linux / macOS)

---

## 🚀 Step 1: Clone Repository & Virtual Environment

### Linux & macOS
```bash
# Clone the repository
git clone https://github.com/your-username/jobhunt_opensource.git
cd jobhunt_opensource

# Create and activate Python virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Upgrade pip and install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# (Optional) Install Playwright Chromium for form automation & scraper
playwright install chromium
```

### Windows (PowerShell or Command Prompt)
```powershell
# Clone the repository
git clone https://github.com/your-username/jobhunt_opensource.git
cd jobhunt_opensource

# Create and activate Python virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1
# If PowerShell script execution is restricted, run: Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

# Upgrade pip and install dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt

# (Optional) Install Playwright Chromium for form automation & scraper
playwright install chromium
```

---

## ⚙️ Step 2: Configure Environment Variables (`.env`)

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
# Windows: copy .env.example .env
```

Open `.env` in your text editor and review the parameters:

```ini
# ==============================================================================
# OnlineJobs.ph Account Credentials
# (Optional: Public scraping works without credentials)
# ==============================================================================
OJP_EMAIL=your_email@example.com
OJP_PASSWORD=your_password_here

# Local Web Dashboard & REST API
PORT=5050
HOST=0.0.0.0
DEBUG=False

# MCP Server Port (for SSE & Streamable HTTP transports)
MCP_PORT=5055

# Optional Shared Secret for Webhook Scraper Triggers
CRON_SECRET=

# Optional Google Cloud Storage Persistence (leave empty for local disk persistence)
GCS_BUCKET=
GCS_OBJECT=jobs.db

# Application Channel Guardrail
ZERO_CONNECTS_ONLY=true
FROM_EMAIL=your_email@example.com
RESUME_PDF_PATH=config/resume.pdf

# Optional SMTP Dispatch (for Route A Email applications)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@example.com
SMTP_PASSWORD=your_app_specific_password

# Playwright Browser Options
HEADLESS=true
BROWSER_TIMEOUT=30000
```

> **Note**: If you do not configure `SMTP_USER` and `SMTP_PASSWORD`, the email dispatcher will safely draft `.eml` message files in `execution/artifacts/` without sending real outbound emails.

---

## 👤 Step 3: Candidate Profile Customization & Pre-Flight Validation

Your candidate profile is the single source of truth for match scoring and proposal generation.

1. **Copy the Template**:
   ```bash
   cp config/profile.example.yaml config/profile.yaml
   # Windows: copy config\profile.example.yaml config\profile.yaml
   ```

2. **Edit `config/profile.yaml`**:
   Fill in your verified background:
   - `candidate`: Your name, email, contact phone, portfolio URL, LinkedIn URL, and verified degree.
   - `role_categories`: The job titles and target keywords you want to match against.
   - `candidate_skills`: List of your verified technical and administrative skills.
   - `potential_gaps`: Skills you do not possess (used to deduct gap penalties).
   - `verified_experience`: Specific past companies, roles, and quantified metrics.
   - `logistics`: Your workstation equipment, internet connection, and working hours.

3. **Attach Candidate Resume PDF**:
   Place your clean PDF resume at `config/resume.pdf`. Alternatively, generate a formatted PDF resume from your profile using:
   ```bash
   python scripts/generate_resume_pdf.py
   ```

4. **Run the Pre-Flight Profile Validator**:
   ```bash
   python tools/validate_profile.py
   ```
   **Expected Output**:
   ```text
   [VALIDATING] Profile file: .../config/profile.yaml
   [PASS] Schema validation: Passed successfully.
   [PASS] Candidate email check: 'your_email@example.com'
   [PASS] Placeholder audit: 0 unedited placeholder tokens found.
   [SUCCESS] Candidate profile is valid and ready for job matching.
   ```
   *If the validator reports unedited placeholders, edit `config/profile.yaml` to replace the template tokens.*

---

## 💾 Step 4: Database Seeding & Initialization

Initialize the SQLite WAL tables and populate 15 synthetic, sanitized job fixtures across all fit tiers:

```bash
python tools/seed_db.py --seed-file seeds/sample_jobs.json --reset
```

**Expected Output**:
```text
[SEED] Target Database: .../jobs.db
[SEED] Seed Fixtures:    .../seeds/sample_jobs.json
[SEED] Resetting existing jobs and scrape_runs tables...
[SEED SUCCESS] Populated 15 synthetic job fixtures (15 inserted, 0 updated).
  - Excellent Fit (>=80%): 6
  - Good Fit (60-79%):     5
  - Moderate Fit (50-59%): 2
  - Low Fit (<50%):        2
  - Channel Breakdown:     5 Email, 4 Form, 6 Platform
```

---

## 🖥️ Step 5: Launch Services

### Option A: Launch Web Dashboard & MCP Server Together

#### On Windows:
```cmd
scripts\start_all.bat
```

#### On Linux / macOS:
```bash
chmod +x scripts/*.sh
./scripts/start_all.sh
```

- **Web Dashboard**: Open [http://localhost:5050](http://localhost:5050)
- **MCP Server (SSE Transport)**: Active on [http://localhost:5055/sse](http://localhost:5055/sse)

---

### Option B: Run MCP Server in Stdio Mode for AI Coding Agents

If you are using Claude Desktop, Cursor, Antigravity, or Windsurf, configure the MCP server using stdio mode:

#### Configuration for Claude Desktop (`claude_desktop_config.json`)
```json
{
  "mcpServers": {
    "onlinejobs-portal": {
      "command": "python",
      "args": ["src/mcp_server.py", "--transport", "stdio"],
      "cwd": "C:\\path\\to\\jobhunt_opensource"
    }
  }
}
```

#### Configuration for Cursor (`.cursor/mcp.json`)
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

---

### Option C: Configure Regional Peak-Hour Crawlers

To automate background scraping aligned with US, UK, and AU peak hiring windows:

#### On Windows (Task Scheduler):
```powershell
powershell -ExecutionPolicy Bypass -File scripts\register_task_scheduler.ps1
```

#### On Linux / macOS (Crontab):
```bash
./scripts/setup_cron.sh
```

---

## ❓ Troubleshooting & FAQs

### 1. `playwright._impl._errors.Error: Executable doesn't exist`
- **Cause**: Playwright browser binaries are not installed.
- **Fix**: Run `playwright install chromium` inside your active virtual environment.

### 2. `Address already in use: Port 5050 or 5055`
- **Cause**: Another instance of Flask or MCP server is already running.
- **Fix**: On Windows, run `netstat -ano | findstr :5050` and kill the PID with `taskkill /PID <PID> /F`. On Linux/macOS, run `lsof -i :5050` and `kill -9 <PID>`.

### 3. `tools/validate_profile.py fails with Unedited placeholders found`
- **Cause**: `config/profile.yaml` still contains default template strings like `[YOUR FULL NAME]` or `alex.taylor@example.com`.
- **Fix**: Open `config/profile.yaml` and customize every field with your actual details.

### 4. `sqlite3.OperationalError: database is locked`
- **Cause**: Multiple write operations attempted simultaneously without WAL mode.
- **Fix**: The platform automatically enables WAL mode (`PRAGMA journal_mode=WAL;`). If locked by a stalled process, terminate old Python processes and run `python -c "from src.db import init_db; init_db()"`.

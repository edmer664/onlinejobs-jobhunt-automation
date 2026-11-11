FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    TZ=Asia/Manila

WORKDIR /app

# Install system prerequisites and Playwright Chromium dependencies
COPY requirements.txt .
RUN apt-get update && \
    apt-get install -y --no-install-recommends libatomic1 bash && \
    pip install --no-cache-dir -r requirements.txt && \
    playwright install --with-deps chromium && \
    rm -rf /var/lib/apt/lists/*

# Copy application source code
COPY . .

# Ensure scripts have executable permissions and logs directory exists
RUN chmod +x scripts/*.sh skills.sh 2>/dev/null || true && \
    mkdir -p logs

# Auto-seed database if jobs.db does not exist
RUN python tools/seed_db.py --seed-file seeds/sample_jobs.json

EXPOSE 5050 5055

# Healthcheck testing Web UI API
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5050/api/stats')" || exit 1

# Launch both Web UI and MCP SSE Server via start_all.sh
CMD ["./scripts/start_all.sh"]

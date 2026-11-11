FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    TZ=Asia/Manila

WORKDIR /app

# Install system prerequisites and Python dependencies
COPY requirements.txt .
RUN apt-get update && \
    apt-get install -y --no-install-recommends libatomic1 && \
    pip install --no-cache-dir -r requirements.txt && \
    playwright install --with-deps chromium && \
    rm -rf /var/lib/apt/lists/*

# Copy application code
COPY . .

# Auto-seed database if jobs.db does not exist
RUN python tools/seed_db.py --seed-file seeds/sample_jobs.json

EXPOSE 5050 5055

# Default start command launches Flask dashboard
CMD ["python", "src/app.py"]

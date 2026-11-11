#!/usr/bin/env bash
# Sets up Linux/macOS crontab for US, UK, and AU Peak Client Hours (Philippine Time Asia/Manila UTC+8)
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
PYTHON_BIN="$(which python3 || which python)"

CRON_COMMENT="# JobHunt Peak Hours Scraper Schedule"

CRON_JOBS="
$CRON_COMMENT
0 1 * * * cd $ROOT_DIR && $PYTHON_BIN src/scraper.py --pages 10 --region US >> logs/cron.log 2>&1
30 3 * * * cd $ROOT_DIR && $PYTHON_BIN src/scraper.py --pages 10 --region US >> logs/cron.log 2>&1
0 7 * * * cd $ROOT_DIR && $PYTHON_BIN src/scraper.py --pages 10 --region AU >> logs/cron.log 2>&1
30 9 * * * cd $ROOT_DIR && $PYTHON_BIN src/scraper.py --pages 10 --region AU >> logs/cron.log 2>&1
0 17 * * * cd $ROOT_DIR && $PYTHON_BIN src/scraper.py --pages 10 --region UK >> logs/cron.log 2>&1
30 19 * * * cd $ROOT_DIR && $PYTHON_BIN src/scraper.py --pages 10 --region UK >> logs/cron.log 2>&1
0 21 * * * cd $ROOT_DIR && $PYTHON_BIN src/scraper.py --pages 10 --region US >> logs/cron.log 2>&1
30 23 * * * cd $ROOT_DIR && $PYTHON_BIN src/scraper.py --pages 10 --region US >> logs/cron.log 2>&1
"

mkdir -p "$ROOT_DIR/logs"

# Append or install crontab
(crontab -l 2>/dev/null | grep -v "JobHunt" || true; echo "$CRON_JOBS") | crontab -
echo "Cron jobs installed successfully for JobHunt peak scrapers."

#!/usr/bin/env bash
# Sets up Linux/macOS crontab for scheduled scraping across AU, UK, and US Peak Hiring Windows.
#
# Multi-Peak Schedule (UTC reference):
#   - AU Peak: 23:00 UTC (07:00 AWST / 10:00 AEST / 07:00 PHT)
#   - UK Peak: 08:00 UTC (08:00 GMT / 09:00 BST / 16:00 PHT)
#   - US Peak: 14:00 UTC (09:00 EST / 06:00 PST / 22:00 PHT)
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
LOGS_DIR="$ROOT_DIR/logs"

# Resolve Python interpreter
if [ -f "$ROOT_DIR/.venv/bin/python" ]; then
    PYTHON_BIN="$ROOT_DIR/.venv/bin/python"
elif [ -f "$ROOT_DIR/venv/bin/python" ]; then
    PYTHON_BIN="$ROOT_DIR/venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="$(which python3)"
else
    PYTHON_BIN="$(which python)"
fi

CRON_TAG="# JobHunt Multi-Peak Scraper Schedule"

mkdir -p "$LOGS_DIR"

show_help() {
    echo "Usage: ./scripts/setup_cron.sh [ACTION]"
    echo "Actions:"
    echo "  --install    Install or update crontab entries (default)"
    echo "  --list       Display current JobHunt crontab entries"
    echo "  --remove     Remove JobHunt crontab entries"
}

action="${1:---install}"

case "$action" in
    --list)
        echo "=== Current JobHunt Crontab Entries ==="
        crontab -l 2>/dev/null | grep -A 4 "JobHunt" || echo "No JobHunt cron entries installed."
        exit 0
        ;;
    --remove)
        echo "Removing JobHunt crontab entries..."
        (crontab -l 2>/dev/null | grep -v "JobHunt" | grep -v "src/scraper.py" || true) | crontab -
        echo "JobHunt cron entries removed successfully."
        exit 0
        ;;
    --install)
        echo "Installing JobHunt Multi-Peak Crontab Schedule..."
        echo "Root Directory: $ROOT_DIR"
        echo "Python Binary:  $PYTHON_BIN"
        echo "Logs Directory: $LOGS_DIR"

        CRON_ENTRIES="
$CRON_TAG
0 23 * * * cd $ROOT_DIR && $PYTHON_BIN src/scraper.py --pages 5 --region AU >> $LOGS_DIR/cron.log 2>&1
0 8 * * * cd $ROOT_DIR && $PYTHON_BIN src/scraper.py --pages 5 --region UK >> $LOGS_DIR/cron.log 2>&1
0 14 * * * cd $ROOT_DIR && $PYTHON_BIN src/scraper.py --pages 5 --region US >> $LOGS_DIR/cron.log 2>&1
"
        (crontab -l 2>/dev/null | grep -v "JobHunt" | grep -v "src/scraper.py" || true; echo "$CRON_ENTRIES") | crontab -
        echo "Cron jobs installed successfully! Runs daily at:"
        echo "  - 23:00 UTC (AU Peak: 07:00 AWST / 10:00 AEST)"
        echo "  - 08:00 UTC (UK Peak: 08:00 GMT / 09:00 BST)"
        echo "  - 14:00 UTC (US Peak: 09:00 EST / 06:00 PST)"
        echo "Logs will be written to: $LOGS_DIR/cron.log"
        ;;
    *)
        show_help
        exit 1
        ;;
esac

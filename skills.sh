#!/usr/bin/env bash
set -e

# Resolve repository root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$SCRIPT_DIR"

# Resolve python binary
if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
else
    echo "Error: Python 3 is required but was not found in PATH." >&2
    exit 1
fi

show_help() {
    cat <<EOF
skills.sh - Cross-platform skill packager and runner

Usage:
  ./skills.sh install [target_dir]
      Install onlinejobs-proposal-generator skill to target directory
      (auto-detects .agents/skills, .cursor/skills, .claude/skills)

  ./skills.sh test
      Run automated regression tests for packaged skills (0 connects, 0 PII, secret codes)

  ./skills.sh run onlinejobs-proposal-generator [--jd "<text>"] [--config <path>]
      Evaluate job description and generate tailored proposal to stdout

  ./skills.sh --help | -h | help
      Show this help message
EOF
}

COMMAND="${1:-}"

case "$COMMAND" in
    install)
        TARGET_DIR="${2:-}"
        if [ -z "$TARGET_DIR" ]; then
            if [ -d "$ROOT_DIR/.agents/skills" ]; then
                TARGET_DIR="$ROOT_DIR/.agents/skills"
            elif [ -d "$ROOT_DIR/.cursor/skills" ]; then
                TARGET_DIR="$ROOT_DIR/.cursor/skills"
            elif [ -d "$ROOT_DIR/.claude/skills" ]; then
                TARGET_DIR="$ROOT_DIR/.claude/skills"
            else
                TARGET_DIR="$ROOT_DIR/.agents/skills"
            fi
        fi
        DEST_DIR="$TARGET_DIR/onlinejobs-proposal-generator"
        mkdir -p "$DEST_DIR"
        cp -r "$ROOT_DIR/skills/onlinejobs-proposal-generator/"* "$DEST_DIR/"
        echo "[SUCCESS] Installed onlinejobs-proposal-generator to $DEST_DIR"
        exit 0
        ;;
    test)
        "$PYTHON_BIN" "$ROOT_DIR/src/proposal_engine.py" test
        exit $?
        ;;
    run)
        shift
        "$PYTHON_BIN" "$ROOT_DIR/src/proposal_engine.py" run "$@"
        exit $?
        ;;
    --help|-h|help|"")
        show_help
        exit 0
        ;;
    *)
        echo "Error: Unknown command '$COMMAND'" >&2
        show_help >&2
        exit 1
        ;;
esac

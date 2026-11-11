"""
tools/validate_profile.py - Candidate Profile Pre-Flight Validator
Validates candidate profile configuration against config/profile.schema.json,
checks email syntax, and audits for unedited template placeholder tokens.
"""

import argparse
import json
import os
import re
import sys
from typing import Any, Dict, List, Tuple

# Ensure project root is in sys.path
TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(TOOLS_DIR, ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.config_loader import find_profile_file, _load_raw_config, get_config_dir

PLACEHOLDER_PATTERNS = [
    r"\[YOUR FULL NAME\]",
    r"\[YOUR FIRST & LAST NAME\]",
    r"\[your\.email@example\.com\]",
    r"\[\+1-555-0199\]",
    r"\[Your City, Country",
    r"\[https://linkedin\.com/in/your-profile\]",
    r"\[https://your-portfolio\.example\.com\]",
    r"\[https://docs\.google\.com/document/d/your-resume-link/pub\]",
    r"\[Executive Administrative Assistant\]",
    r"\[Global Operations Company\]",
    r"\[Your University / Institution\]",
    r"\[Graduation Year\]",
    r"your_password_here",
]


def validate_profile(config_path: str = None, strict_placeholders: bool = False) -> int:
    """
    Validates profile configuration.
    Returns 0 on success, 1 on validation error.
    """
    schema_path = os.path.join(PROJECT_ROOT, "config", "profile.schema.json")
    if not os.path.exists(schema_path):
        print(f"[ERROR] Schema file not found at {schema_path}", file=sys.stderr)
        return 1

    try:
        with open(schema_path, "r", encoding="utf-8") as sf:
            schema = json.load(sf)
    except Exception as exc:
        print(f"[ERROR] Failed to parse schema file: {exc}", file=sys.stderr)
        return 1

    try:
        resolved_path, is_fallback = find_profile_file(config_path)
    except FileNotFoundError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1

    print(f"[VALIDATING] Profile file: {resolved_path}")
    if is_fallback:
        print(f"[INFO] Using example template profile.")

    try:
        data = _load_raw_config(resolved_path)
    except Exception as exc:
        print(f"[ERROR] Failed to load configuration data: {exc}", file=sys.stderr)
        return 1

    # Validate against JSON schema
    try:
        import jsonschema
        jsonschema.validate(instance=data, schema=schema)
        print("[PASS] Schema validation: Passed successfully.")
    except ImportError:
        print("[WARN] jsonschema package not installed. Skipping deep schema validation.")
    except Exception as exc:
        print(f"[FAIL] Schema validation error: {exc}", file=sys.stderr)
        return 1

    # Email format check
    candidate = data.get("candidate", {})
    email = candidate.get("email", "")
    email_regex = re.compile(r"^[\w\.\+\-]+@[\w\-]+\.[a-zA-Z0-9\.\-]+$")
    if not email_regex.match(email):
        print(f"[FAIL] Invalid candidate email format: '{email}'", file=sys.stderr)
        return 1
    print(f"[PASS] Candidate email check: '{email}'")

    # Placeholder check if strict or custom profile
    if strict_placeholders or (not is_fallback and not resolved_path.endswith(".example.json") and not resolved_path.endswith(".example.yaml")):
        raw_text = json.dumps(data)
        found_placeholders = []
        for pat in PLACEHOLDER_PATTERNS:
            if re.search(pat, raw_text, re.IGNORECASE):
                found_placeholders.append(pat)

        if found_placeholders:
            print(f"[FAIL] Unedited placeholders found in active profile:", file=sys.stderr)
            for p in found_placeholders:
                print(f"  - {p}", file=sys.stderr)
            print("Remediation: Edit config/profile.yaml with your real verified facts before deploying.", file=sys.stderr)
            return 1
        print("[PASS] Placeholder audit: 0 unedited placeholder tokens found.")

    print("[SUCCESS] Candidate profile is valid and ready for job matching.")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Validate candidate profile against schema.")
    parser.add_argument("--config", default=None, help="Path to profile file (.yaml or .json)")
    parser.add_argument("--strict", action="store_true", help="Disallow placeholder tokens even in example templates")
    args = parser.parse_args()
    sys.exit(validate_profile(config_path=args.config, strict_placeholders=args.strict))


if __name__ == "__main__":
    main()

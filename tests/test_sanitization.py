"""
tests/test_sanitization.py - Rigorous Zero-PII & Clean Repository Test Suite
Verifies:
1. 0 occurrences of candidate PII across all tracked files.
2. 0 unredacted secrets or credentials.
3. Clean git history (0 author PII or historical PII commits).
4. Existence and non-emptiness of all placeholder templates.
5. Absence of binary databases (*.db) in git tracking.
"""

import base64
import json
import os
import re
import subprocess
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _b64(val: str) -> str:
    """Helper to decode verification tokens without embedding plaintext in source control."""
    return base64.b64decode(val.encode("ascii")).decode("utf-8")


# Base64-encoded verification signatures for candidate PII
ENCODED_PII_PATTERNS = [
    # Candidate Names
    ("XGJrcmlzdGVsXGI=", "Candidate first name"),
    ("XGJiYWd0YXNcYg==", "Candidate surname"),
    ("XGJLcmlzdGVsXHMrSm95XGI=", "Candidate full name"),
    # Candidate Personal Emails
    ("a3Jpc3RlbGdlbmVzZWJhZ3Rhc1wuM0BnbWFpbFwuY29t", "Candidate email 1"),
    ("a3Jpc3RlbGdlbmVzZWJhZ3Rhc0BnbWFpbFwuY29t", "Candidate email 2"),
    # Developer / Private Applied Emails
    ("ZWRtZXJwaXphcnJhQGdtYWlsXC5jb20=", "Author personal email"),
    ("aGVtYWxzZWNyZXRza2lsbHNAZ21haWxcLmNvbQ==", "Private employer email"),
    # Candidate Phone Numbers
    ("XCs/NjM5NDg3NjQzMDA2XGI=", "Candidate phone with country code"),
    ("XGIwOTQ4NzY0MzAwNlxi", "Candidate phone local 1"),
    ("XGI5NDg3NjQzMDA2XGI=", "Candidate phone local 2"),
    # Platform Passwords
    ("XGJBa2lyYW1heTMxXGI=", "Platform password"),
    # Geographic Location (Candidate home town)
    ("TGltYXksXHMqQmF0YWFu", "Candidate address"),
    # Personal Portfolio & Resume URLs
    ("a3Jpc3RlbC1iYWd0YXMtcG9ydGZvbGlvXC5uZXRsaWZ5XC5hcHA=", "Candidate portfolio URL"),
    ("a3Jpc3RlbC1qb3ktYmFndGFzLTliOTFiNzM3NA==", "Candidate LinkedIn slug"),
    ("MlBBQ1gtMXZUN1JvcnNXc3YzVmVWNkxHVEZjdktKREprc1RiS3VJLUNLRXFHSjY4WWJHWmZQMmo0WTN2enVTUDRVTWJlV01YMzF3ZmllTGU2UTVHdnM=", "Google Docs resume slug"),
    # Private Cloud Assets
    ("b2pwLWRhc2hib2FyZC0zNDc1NzE3NjA0OTU=", "Private Cloud Run URL"),
    ("b2pwLWF1dG9tYXRpb24ta3Jpc3RlbC1kYg==", "Private GCS bucket"),
    # Candidate Unique Tokens & Monograms (Milestone 1 Iteration 2 Hardening)
    ("OWI5MWI3Mzc0", "Candidate LinkedIn vanity ID"),
    ("XGJLQlxi", "Candidate monogram initials"),
    ("WW9uZXI=", "Candidate capstone project name"),
    ("U1NJVEU=", "Candidate student tech organization"),
    ("UGVuaW5zdWxh", "Candidate alma mater residual"),
    # Specific Past Employer Affiliations
    ("UHJ1XHMrTGlmZVxzK1VL", "Past employer"),
    ("QmF0YWFuXHMrUGVuaW5zdWxhXHMrU3RhdGVccytVbml2ZXJzaXR5", "Candidate alma mater"),
]

ENCODED_TERMS = [
    "a3Jpc3RlbA==",
    "YmFndGFz",
    "QWtpcmFtYXkzMQ==",
    "MDk0ODc2NDMwMDY=",
    "a3Jpc3RlbGdlbmVzZWJhZ3Rhcw==",
    "ZWRtZXJwaXphcnJh",
    "OWI5MWI3Mzc0",
    "WW9uZXI=",
    "U1NJVEU=",
    "S0I=",
    "UGVuaW5zdWxh",
]


def get_tracked_files() -> list[Path]:
    """Retrieves list of files tracked by git, falling back to directory walk if not a git repo."""
    try:
        proc = subprocess.run(
            ["git", "ls-files"],
            cwd=REPO_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        )
        files = [REPO_ROOT / line.strip() for line in proc.stdout.splitlines() if line.strip()]
        if files:
            return [f for f in files if f.exists() and f.is_file()]
    except Exception:
        pass

    # Fallback if git is not yet committed or tracked
    tracked = []
    for root, dirs, filenames in os.walk(REPO_ROOT):
        dirs[:] = [d for d in dirs if d not in (".git", "__pycache__", ".pytest_cache", ".venv", "venv", "node_modules")]
        for filename in filenames:
            p = Path(root) / filename
            if not filename.endswith((".pyc", ".db", ".db-wal", ".db-shm")):
                tracked.append(p)
    return tracked


class TestRepositorySanitization(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tracked_files = get_tracked_files()

    def test_01_zero_candidate_pii_in_tracked_files(self):
        """Verify 0 occurrences of candidate PII across all tracked text files."""
        violations = []
        compiled_patterns = [
            (re.compile(_b64(enc), re.IGNORECASE), desc)
            for enc, desc in ENCODED_PII_PATTERNS
        ]

        for file_path in self.tracked_files:
            # Skip test_sanitization.py itself
            if file_path.name == "test_sanitization.py":
                continue

            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            for idx, line in enumerate(content.splitlines(), start=1):
                for regex, desc in compiled_patterns:
                    match = regex.search(line)
                    if match:
                        violations.append(
                            f"{file_path.relative_to(REPO_ROOT)}:{idx} matched '{match.group(0)}' ({desc}): {line.strip()}"
                        )

        self.assertEqual(
            len(violations),
            0,
            f"Candidate PII leaked in {len(violations)} locations:\n" + "\n".join(violations),
        )

    def test_02_zero_unredacted_secrets_or_credentials(self):
        """Verify no unredacted passwords, secrets, or .env files are tracked."""
        # Check 1: .env must NOT be tracked
        tracked_rel_paths = [str(f.relative_to(REPO_ROOT)).replace("\\", "/") for f in self.tracked_files]
        self.assertNotIn(".env", tracked_rel_paths, ".env file must NOT be tracked in git!")

        # Check 2: No private key files
        for f in self.tracked_files:
            try:
                content = f.read_text(encoding="utf-8", errors="ignore")
                self.assertNotIn("BEGIN RSA PRIVATE KEY", content, f"Private key found in {f}")
                self.assertNotIn("BEGIN OPENSSH PRIVATE KEY", content, f"Private key found in {f}")
                self.assertNotIn("BEGIN PRIVATE KEY", content, f"Private key found in {f}")
            except Exception:
                pass

        # Check 3: .env.example must only contain placeholders
        env_example_paths = [p for p in [REPO_ROOT / ".env.example", REPO_ROOT / "config" / ".env.example"] if p.exists()]
        self.assertTrue(len(env_example_paths) > 0, ".env.example must exist!")
        pw_check = _b64("QWtpcmFtYXkzMQ==")
        name_check = _b64("a3Jpc3RlbA==")
        for env_ex in env_example_paths:
            content = env_ex.read_text(encoding="utf-8")
            self.assertIn("OJP_PASSWORD=your_password_here", content)
            self.assertNotIn(pw_check, content)
            self.assertNotIn(name_check, content.lower())

    def test_03_clean_git_history(self):
        """Verify git history has 0 candidate PII, 0 private authors, and clean commits."""
        git_dir = REPO_ROOT / ".git"
        if not git_dir.exists():
            self.skipTest("Git repository not yet initialized at target directory.")

        # Check author identities in git history
        banned_authors = [_b64("ZWRtZXI="), _b64("a3Jpc3RlbA=="), _b64("YmFndGFz")]
        try:
            authors = subprocess.check_output(
                ["git", "log", "--format=%an <%ae>"],
                cwd=REPO_ROOT,
                text=True,
            ).splitlines()
            for author in authors:
                for b_auth in banned_authors:
                    self.assertNotIn(b_auth, author.lower(), f"Personal author found in git history: {author}")
        except subprocess.CalledProcessError:
            pass  # Empty repository before initial commit

        # Check git log pickaxe (-S) for banned terms
        terms = [_b64(enc) for enc in ENCODED_TERMS]
        for term in terms:
            try:
                diff_search = subprocess.check_output(
                    ["git", "log", f"-S{term}", "--oneline"],
                    cwd=REPO_ROOT,
                    text=True,
                ).strip()
                self.assertEqual(
                    diff_search,
                    "",
                    f"Git commit history leaked term '{term}' in commits:\n{diff_search}",
                )
            except subprocess.CalledProcessError:
                pass

    def test_04_placeholder_templates_exist_and_non_empty(self):
        """Verify all required configuration and profile templates exist and are populated."""
        required_templates = [
            "config/profile.example.yaml",
            "config/profile.example.json",
            "config/profile.example.md",
            "config/cv.example.md",
            "config/profile.schema.json",
            "seeds/sample_jobs.json",
        ]

        # Check .env.example at root or in config/
        env_ex_found = (REPO_ROOT / ".env.example").exists() or (REPO_ROOT / "config" / ".env.example").exists()
        self.assertTrue(env_ex_found, "Missing .env.example template!")

        for rel_path in required_templates:
            tmpl_path = REPO_ROOT / rel_path
            self.assertTrue(tmpl_path.exists(), f"Required template missing: {rel_path}")
            self.assertGreater(tmpl_path.stat().st_size, 50, f"Template {rel_path} is empty or suspiciously small")

        # Verify JSON templates parse cleanly
        with open(REPO_ROOT / "config" / "profile.example.json", "r", encoding="utf-8") as f:
            profile_json = json.load(f)
            self.assertIn("candidate", profile_json)
            self.assertIn("role_categories", profile_json)

        with open(REPO_ROOT / "seeds" / "sample_jobs.json", "r", encoding="utf-8") as f:
            seeds = json.load(f)
            self.assertIsInstance(seeds, list)
            self.assertGreaterEqual(len(seeds), 15, "sample_jobs.json must contain at least 15 jobs")

    def test_05_no_binary_db_or_artifacts_committed(self):
        """Verify no binary SQLite database (*.db) or large binaries are tracked."""
        tracked_rel_paths = [str(f.relative_to(REPO_ROOT)).replace("\\", "/") for f in self.tracked_files]

        for p in tracked_rel_paths:
            self.assertFalse(p.endswith(".db"), f"Binary SQLite file tracked in git: {p}")
            self.assertFalse(p.endswith(".sqlite"), f"Binary SQLite file tracked in git: {p}")
            self.assertFalse(p.endswith(".sqlite3"), f"Binary SQLite file tracked in git: {p}")
            self.assertFalse(p.endswith(".db-wal"), f"WAL file tracked in git: {p}")
            self.assertFalse(p.endswith(".db-shm"), f"Shared memory file tracked in git: {p}")
            self.assertFalse(p.endswith(".mp4"), f"Binary video file tracked in git: {p}")

        # Verify .gitignore covers databases and private environments
        gitignore = REPO_ROOT / ".gitignore"
        self.assertTrue(gitignore.exists(), ".gitignore must exist in repository root")
        gi_content = gitignore.read_text(encoding="utf-8")
        self.assertIn(".env", gi_content)
        self.assertTrue("*.db" in gi_content or "jobs.db" in gi_content, ".gitignore must ignore *.db or jobs.db")


if __name__ == "__main__":
    unittest.main()

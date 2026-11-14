"""
tests/test_skills_packaging.py - Comprehensive Unit & Integration Tests for Skill Packaging & Runners

Verifies:
1. skills/onlinejobs-proposal-generator/SKILL.md exists with valid YAML frontmatter.
2. skills-lock.json is valid JSON pointing to the local packaged skill file.
3. skills.sh and skills.ps1 exist and pass syntax validation.
4. Skill installation into a target directory functions correctly.
5. Skill execution ('run' and 'test') produces correct, trap-audited output and exits 0.
6. Zero PII in all skill package files.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import yaml

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.proposal_engine import (
    evaluate_and_generate,
    format_evaluation_and_proposal_markdown,
    generate_tailored_proposal,
    run_skill_regression_tests,
)


class TestSkillsPackagingAndRunners(unittest.TestCase):
    """Automated test suite verifying Milestone 4 Skill Packaging & skills.sh contract."""

    def setUp(self):
        self.skill_dir = os.path.join(PROJECT_ROOT, "skills", "onlinejobs-proposal-generator")
        self.skill_md = os.path.join(self.skill_dir, "SKILL.md")
        self.lock_file = os.path.join(PROJECT_ROOT, "skills-lock.json")
        self.sh_script = os.path.join(PROJECT_ROOT, "skills.sh")
        self.ps1_script = os.path.join(PROJECT_ROOT, "skills.ps1")
        self.scripts_ps1 = os.path.join(PROJECT_ROOT, "scripts", "skills.ps1")
        self.python_bin = sys.executable

    def test_01_skill_md_exists_and_valid_frontmatter(self):
        """Verify skills/onlinejobs-proposal-generator/SKILL.md exists with valid frontmatter."""
        self.assertTrue(os.path.exists(self.skill_md), f"SKILL.md missing at {self.skill_md}")
        self.assertGreater(os.path.getsize(self.skill_md), 0, "SKILL.md is empty")

        with open(self.skill_md, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertTrue(content.startswith("---"), "SKILL.md must start with YAML frontmatter delimiter '---'")
        parts = content.split("---", 2)
        self.assertGreaterEqual(len(parts), 3, "SKILL.md frontmatter delimiters incomplete")

        fm_text = parts[1]
        fm = yaml.safe_load(fm_text)
        self.assertIsInstance(fm, dict, "Frontmatter must parse into a YAML dictionary")

        self.assertEqual(fm.get("name"), "onlinejobs-proposal-generator")
        self.assertTrue(isinstance(fm.get("description"), str) and len(fm["description"]) > 20)
        self.assertEqual(str(fm.get("version")), "1.0.0")

    def test_02_skills_lock_json_integrity(self):
        """Verify skills-lock.json is valid JSON and points to an existing skill file."""
        self.assertTrue(os.path.exists(self.lock_file), f"skills-lock.json missing at {self.lock_file}")

        with open(self.lock_file, "r", encoding="utf-8") as f:
            lock_data = json.load(f)

        self.assertIsInstance(lock_data, dict)
        self.assertEqual(lock_data.get("version"), 1)
        self.assertIn("skills", lock_data)
        self.assertIn("onlinejobs-proposal-generator", lock_data["skills"])

        pkg = lock_data["skills"]["onlinejobs-proposal-generator"]
        self.assertEqual(pkg.get("source"), "local")
        self.assertEqual(pkg.get("sourceType"), "local")
        self.assertEqual(pkg.get("version"), "1.0.0")

        skill_rel_path = pkg.get("skillPath")
        self.assertTrue(skill_rel_path, "skillPath field missing in skills-lock.json")

        target_file = os.path.join(PROJECT_ROOT, skill_rel_path.replace("/", os.sep))
        self.assertTrue(os.path.exists(target_file), f"Target skill file referenced in lock not found: {target_file}")

    def test_03_runners_exist_and_syntax(self):
        """Verify skills.sh, skills.ps1, and scripts/skills.ps1 exist with proper formatting."""
        # Check skills.sh
        self.assertTrue(os.path.exists(self.sh_script), "skills.sh missing at root")
        with open(self.sh_script, "rb") as f:
            sh_bytes = f.read()

        self.assertTrue(sh_bytes.startswith(b"#!/usr/bin/env bash"), "skills.sh must start with '#!/usr/bin/env bash'")
        self.assertIn(b"set -e", sh_bytes, "skills.sh must specify 'set -e'")
        self.assertNotIn(b"\r\n", sh_bytes, "skills.sh must have LF (\\n) line endings, not CRLF (\\r\\n)")

        # Check skills.ps1 and scripts/skills.ps1
        for ps1 in [self.ps1_script, self.scripts_ps1]:
            self.assertTrue(os.path.exists(ps1), f"PowerShell runner missing: {ps1}")
            cmd = f"[System.Management.Automation.Language.Parser]::ParseFile('{ps1}', [ref]$null, [ref]$errors); if ($errors.Count -gt 0) {{ exit 1 }} else {{ exit 0 }}"
            res = subprocess.run(
                ["powershell", "-NoProfile", "-Command", cmd],
                capture_output=True,
                text=True,
                timeout=8,
            )
            self.assertEqual(res.returncode, 0, f"PowerShell syntax error in {ps1}: {res.stderr}")

    def test_04_installation_to_temp_directory(self):
        """Verify installation into a custom target directory via PowerShell runner."""
        tmp_dir = tempfile.mkdtemp(prefix="test_skill_install_")
        try:
            cmd = [
                "powershell",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                self.ps1_script,
                "install",
                tmp_dir,
            ]
            res = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=15)
            self.assertEqual(res.returncode, 0, f"Install command failed: {res.stderr}\n{res.stdout}")
            self.assertIn("[SUCCESS]", res.stdout)

            installed_skill_md = os.path.join(tmp_dir, "onlinejobs-proposal-generator", "SKILL.md")
            self.assertTrue(os.path.exists(installed_skill_md), f"Installed SKILL.md not found at {installed_skill_md}")

            with open(self.skill_md, "r", encoding="utf-8") as orig, open(installed_skill_md, "r", encoding="utf-8") as inst:
                self.assertEqual(orig.read(), inst.read(), "Installed SKILL.md content does not match source")
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_05_skill_execution_test_harness(self):
        """Verify skill 'test' mode executes automated regression harness and exits 0."""
        # 1. Directly via Python
        success = run_skill_regression_tests()
        self.assertTrue(success, "Python run_skill_regression_tests returned False")

        # 2. Via PowerShell runner
        res = subprocess.run(
            ["powershell", "-ExecutionPolicy", "Bypass", "-File", self.ps1_script, "test"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=15,
        )
        self.assertEqual(res.returncode, 0, f"skills.ps1 test failed: {res.stderr}\n{res.stdout}")
        self.assertIn("[SUCCESS] All 5 skill regression tests passed cleanly", res.stdout)

    def test_06_skill_execution_run_with_custom_jd(self):
        """Verify skill 'run' outputs evaluation summary and proposal markdown with trap detection."""
        custom_jd = (
            "Virtual Assistant for busy Executive.\n"
            "Must handle appointments, correspondence, and daily Google Sheets.\n"
            "Special requirement: Start your proposal with the magic phrase 'READY-NOW'.\n"
            "Email your resume directly to team@growthventures.io. 0 connects spent."
        )

        res = subprocess.run(
            [
                "powershell",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                self.ps1_script,
                "run",
                "onlinejobs-proposal-generator",
                "--jd",
                custom_jd,
            ],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=15,
        )
        self.assertEqual(res.returncode, 0, f"skills.ps1 run failed: {res.stderr}\n{res.stdout}")
        stdout = res.stdout

        self.assertIn("# OnlineJobs.ph Job Evaluation & High-Conversion Proposal", stdout)
        self.assertIn("1. Job Description Evaluation Summary", stdout)
        self.assertIn("2. High-Conversion OnlineJobs.ph Proposal", stdout)
        self.assertIn("READY-NOW", stdout)
        self.assertIn("Route A: Direct Email (team@growthventures.io)", stdout)
        self.assertIn("0 Connect Points Spent", stdout)

    def test_07_skill_execution_run_default_sample(self):
        """Verify skill 'run' without arguments defaults to sample JD and exits 0."""
        res = subprocess.run(
            [
                "powershell",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                self.ps1_script,
                "run",
                "onlinejobs-proposal-generator",
            ],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=15,
        )
        self.assertEqual(res.returncode, 0, f"skills.ps1 run default failed: {res.stderr}\n{res.stdout}")
        self.assertIn("# OnlineJobs.ph Job Evaluation & High-Conversion Proposal", res.stdout)
        self.assertIn("BLUEBERRY", res.stdout)

    def test_08_scripts_skills_ps1_parity(self):
        """Verify scripts/skills.ps1 operates with full parity when executed from scripts/."""
        res = subprocess.run(
            [
                "powershell",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                self.scripts_ps1,
                "test",
            ],
            cwd=os.path.join(PROJECT_ROOT, "scripts"),
            capture_output=True,
            text=True,
            timeout=15,
        )
        self.assertEqual(res.returncode, 0, f"scripts/skills.ps1 test failed: {res.stderr}\n{res.stdout}")
        self.assertIn("[SUCCESS]", res.stdout)

    def test_09_runner_help_and_unknown_commands(self):
        """Verify help flags and unknown commands are handled gracefully."""
        # Help flags
        for flag in ["--help", "-h", "help"]:
            res = subprocess.run(
                ["powershell", "-ExecutionPolicy", "Bypass", "-File", self.ps1_script, flag],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=10,
            )
            self.assertEqual(res.returncode, 0)
            self.assertIn("Cross-platform skill packager and runner", res.stdout)

        # Unknown command
        res_err = subprocess.run(
            ["powershell", "-ExecutionPolicy", "Bypass", "-File", self.ps1_script, "invalid_command_xyz"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertNotEqual(res_err.returncode, 0, "Unknown command must return non-zero exit code")

    def test_10_zero_pii_in_all_skill_files(self):
        """Verify zero PII across all files in skills/ directory."""
        import base64
        forbidden_regexes = [
            (base64.b64decode("XGJrcmlzdGVsXGI=").decode("ascii"), "Candidate first name"),
            (base64.b64decode("XGJiYWd0YXNcYg==").decode("ascii"), "Candidate surname"),
            (r"\b09\d{9}\b", "Philippine mobile number '09xxxxxxxxx'"),
            (r"\+63\d{10}\b", "Philippine international number '+63xxxxxxxxxx'"),
            (r"[a-zA-Z0-9_.+-]+@gmail\.com", "Personal Gmail address"),
        ]

        leaks = []
        for root, _, files in os.walk(self.skill_dir):
            for fname in files:
                fpath = os.path.join(root, fname)
                with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                for pat, label in forbidden_regexes:
                    matches = re.findall(pat, content, re.IGNORECASE)
                    if matches:
                        rel = os.path.relpath(fpath, PROJECT_ROOT)
                        leaks.append(f"{label} found in {rel}: {matches}")

        self.assertEqual(len(leaks), 0, f"PII leaks detected in skill files: {leaks}")

    def test_11_skills_sh_execution_if_bash_available(self):
        """Verify skills.sh runs under bash if bash is available on PATH."""
        bash_bin = shutil.which("bash")
        if not bash_bin and os.path.exists(r"C:\Program Files\Git\bin\bash.exe"):
            bash_bin = r"C:\Program Files\Git\bin\bash.exe"

        if not bash_bin:
            self.skipTest("Bash not found in environment")

        # Test help
        res_help = subprocess.run(
            [bash_bin, "skills.sh", "--help"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(res_help.returncode, 0, f"skills.sh --help failed: {res_help.stderr}")
        self.assertIn("skills.sh - Cross-platform skill packager and runner", res_help.stdout)

        # Test test command
        res_test = subprocess.run(
            [bash_bin, "skills.sh", "test"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=15,
        )
        self.assertEqual(res_test.returncode, 0, f"skills.sh test failed: {res_test.stderr}")
        self.assertIn("[SUCCESS] All 5 skill regression tests passed cleanly", res_test.stdout)

        # Test run command
        res_run = subprocess.run(
            [bash_bin, "skills.sh", "run", "onlinejobs-proposal-generator"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=15,
        )
        self.assertEqual(res_run.returncode, 0, f"skills.sh run failed: {res_run.stderr}")
        self.assertIn("# OnlineJobs.ph Job Evaluation & High-Conversion Proposal", res_run.stdout)

    def test_12_unicode_typographical_quotes_secret_codes(self):
        """Verify paired typographical/unicode quote matching for secret codes (Defect 1)."""
        from src.proposal_engine import audit_screening_traps

        # Test double curved quotes (\u201c ... \u201d)
        res_curved_double = audit_screening_traps("Please include the code word \u201cBLUEBERRY\u201d in your subject line.")
        self.assertIn("BLUEBERRY", res_curved_double.get("secret_codes", []), "Failed to extract curved double quoted code")

        # Test single curved quotes (\u2018 ... \u2019)
        res_curved_single = audit_screening_traps("Start your application with magic phrase \u2018READY-NOW\u2019.")
        self.assertIn("READY-NOW", res_curved_single.get("secret_codes", []), "Failed to extract curved single quoted code")

        # Test guillemets (« ... »)
        res_guillemets = audit_screening_traps("Put «PHOENIX» in the subject line.")
        self.assertIn("PHOENIX", res_guillemets.get("secret_codes", []), "Failed to extract guillemet quoted code")

    def test_13_negative_disclaimer_trap_rejection(self):
        """Verify negative phrasing/disclaimer traps are rejected and not inserted into subject (Defect 2)."""
        jd_negative_trap = (
            "Virtual Assistant Wanted\n"
            "Do NOT put the word 'BLUEBERRY' in your subject line. Candidates who include blueberry will be rejected immediately.\n"
            "Send your CV to jobs@agency.org."
        )
        eval_res, prop_res, md = evaluate_and_generate(jd_text=jd_negative_trap)
        codes = prop_res.get("screening_audit", {}).get("secret_codes", [])
        self.assertNotIn("BLUEBERRY", codes, f"Negative trap code incorrectly extracted: {codes}")
        self.assertNotIn("[BLUEBERRY]", prop_res.get("subject_line", ""), "Prohibited code placed in subject line")

        # Also test 'Never include' variant
        jd_never = "Never include 'BLUEBERRY' in your subject line. Apply directly."
        eval_res2, prop_res2, _ = evaluate_and_generate(jd_text=jd_never)
        codes2 = prop_res2.get("screening_audit", {}).get("secret_codes", [])
        self.assertNotIn("BLUEBERRY", codes2, f"'Never include' trap incorrectly extracted: {codes2}")

    def test_14_channel_priority_route_c_over_route_a(self):
        """Verify Route C (External Form) takes precedence over Route A (Direct Email) in proposal markdown (Defect 3)."""
        jd_dual_channel = (
            "Operations Coordinator\n"
            "Please do NOT send emails or resumes to info@agency.org (that inbox is not checked and emails will be discarded).\n"
            "All applicants must fill out the form at https://forms.gle/officialform123.\n"
        )
        eval_res, prop_res, md = evaluate_and_generate(jd_text=jd_dual_channel)
        self.assertIn("Route C: External Form (https://forms.gle/officialform123)", md)
        self.assertNotIn("Route A: Direct Email", md)

    def test_15_powershell_runner_empty_jd_argument(self):
        """Verify PowerShell runner handles empty string argument --jd '' cleanly without crashing (Defect 4)."""
        for script in [self.ps1_script, self.scripts_ps1]:
            cmd = [
                "powershell",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                script,
                "run",
                "onlinejobs-proposal-generator",
                "--jd",
                '""',
            ]
            res = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=15)
            self.assertEqual(res.returncode, 0, f"Runner failed on empty --jd argument with {script}: {res.stderr}\n{res.stdout}")
            self.assertIn("# OnlineJobs.ph Job Evaluation & High-Conversion Proposal", res.stdout)


if __name__ == "__main__":
    unittest.main()

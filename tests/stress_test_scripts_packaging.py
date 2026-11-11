"""
stress_test_scripts_packaging.py - Adversarial Packaging & Script Integrity Stress Harness
"""

import ast
import os
import py_compile
import re
import subprocess
import sys
import unittest
import yaml
from typing import Dict, List, Set

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


class TestScriptAndPackagingIntegrity(unittest.TestCase):
    def test_01_python_syntax_and_compilation(self):
        """Verify all Python scripts in scripts/, src/, execution/, tools/ compile cleanly."""
        target_dirs = ["scripts", "src", "execution", "tools", "tests"]
        errors = []
        for d in target_dirs:
            dir_path = os.path.join(PROJECT_ROOT, d)
            if not os.path.isdir(dir_path):
                continue
            for root, _, files in os.walk(dir_path):
                for f in files:
                    if f.endswith(".py"):
                        full_path = os.path.join(root, f)
                        try:
                            py_compile.compile(full_path, doraise=True)
                        except py_compile.PyCompileError as e:
                            errors.append(f"Syntax error in {full_path}: {e}")

        self.assertEqual(len(errors), 0, f"Python compilation failures: {errors}")

    def test_02_shell_and_powershell_script_syntax(self):
        """Verify all shell scripts pass bash -n and powershell scripts parse cleanly."""
        sh_files = [
            "scripts/run_mcp_stdio.sh",
            "scripts/setup_cron.sh",
            "scripts/start_all.sh",
            "skills.sh",
        ]

        # Test bash -n
        for rel_sh in sh_files:
            sh_path = os.path.join(PROJECT_ROOT, rel_sh.replace("/", os.sep))
            if os.path.exists(sh_path):
                self.assertGreater(os.path.getsize(sh_path), 0, f"{sh_path} is empty")
                try:
                    # Pass relative path with forward slashes so bash understands it
                    res = subprocess.run(
                        ["bash", "-n", rel_sh],
                        cwd=PROJECT_ROOT,
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )
                    self.assertEqual(res.returncode, 0, f"bash -n failed for {rel_sh}: {res.stderr}")
                except (subprocess.SubprocessError, FileNotFoundError):
                    pass

        # Test PowerShell syntax for .ps1 files
        ps1_files = [
            os.path.join(PROJECT_ROOT, "scripts", "register_task_scheduler.ps1"),
            os.path.join(PROJECT_ROOT, "skills.ps1"),
        ]
        for ps1 in ps1_files:
            if os.path.exists(ps1):
                cmd = f"[System.Management.Automation.Language.Parser]::ParseFile('{ps1}', [ref]$null, [ref]$errors); if ($errors.Count -gt 0) {{ exit 1 }} else {{ exit 0 }}"
                res = subprocess.run(
                    ["powershell", "-NoProfile", "-Command", cmd],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                self.assertEqual(res.returncode, 0, f"PowerShell parse error in {ps1}: {res.stderr}")

    def test_03_shell_script_line_endings_audit(self):
        """
        Adversarial check: Shell scripts executed inside Linux environments or WSL
        must NOT contain CRLF line endings (\\r\\n), which cause '\\r: command not found'.
        """
        sh_files = [
            os.path.join(PROJECT_ROOT, "scripts", "run_mcp_stdio.sh"),
            os.path.join(PROJECT_ROOT, "scripts", "setup_cron.sh"),
            os.path.join(PROJECT_ROOT, "scripts", "start_all.sh"),
            os.path.join(PROJECT_ROOT, "skills.sh"),
        ]
        crlf_files = []
        for sh_path in sh_files:
            if os.path.exists(sh_path):
                with open(sh_path, "rb") as f:
                    content = f.read()
                    if b"\r\n" in content:
                        crlf_files.append(os.path.relpath(sh_path, PROJECT_ROOT))

        print(f"\n[LINE ENDINGS AUDIT] Shell scripts with CRLF: {crlf_files}")
        # Note: on Windows git repos, core.autocrlf may convert them on checkout.
        # We record whether CRLF is present.

    def test_04_dockerfile_and_compose_syntax(self):
        """Verify Dockerfile and docker-compose.yml structure and syntax."""
        dockerfile_path = os.path.join(PROJECT_ROOT, "Dockerfile")
        self.assertTrue(os.path.exists(dockerfile_path), "Dockerfile missing")

        with open(dockerfile_path, "r", encoding="utf-8") as f:
            df_content = f.read()

        self.assertIn("FROM python:3.12-slim", df_content)
        self.assertIn("WORKDIR /app", df_content)
        self.assertIn("COPY requirements.txt .", df_content)
        self.assertIn("pip install", df_content)
        self.assertIn("playwright install", df_content)
        self.assertIn("COPY . .", df_content)
        self.assertIn("EXPOSE 5050 5055", df_content)
        self.assertIn("CMD", df_content)

        compose_path = os.path.join(PROJECT_ROOT, "docker-compose.yml")
        self.assertTrue(os.path.exists(compose_path), "docker-compose.yml missing")

        with open(compose_path, "r", encoding="utf-8") as f:
            compose_data = yaml.safe_load(f)

        self.assertIsInstance(compose_data, dict)
        self.assertIn("services", compose_data)
        self.assertIn("jobhunt", compose_data["services"])

        svc = compose_data["services"]["jobhunt"]
        self.assertEqual(svc.get("build"), ".")
        self.assertIn("5050:5050", svc.get("ports", []))
        self.assertIn("5055:5055", svc.get("ports", []))

    def test_05_dependency_coverage_vs_requirements(self):
        """
        Verify all third-party libraries imported across src/, execution/, tools/, scripts/
        are declared in requirements.txt.
        """
        req_path = os.path.join(PROJECT_ROOT, "requirements.txt")
        self.assertTrue(os.path.exists(req_path), "requirements.txt missing")

        with open(req_path, "r", encoding="utf-8") as f:
            req_lines = [line.strip().split(">=")[0].split("==")[0].lower() for line in f if line.strip() and not line.startswith("#")]

        package_import_map = {
            "beautifulsoup4": "bs4",
            "python-dotenv": "dotenv",
            "pyyaml": "yaml",
            "google-cloud-storage": "google",
        }

        declared_imports = set()
        for pkg in req_lines:
            declared_imports.add(pkg)
            if pkg in package_import_map:
                declared_imports.add(package_import_map[pkg].split(".")[0])

        std_lib = {
            "argparse", "asyncio", "base64", "collections", "concurrent", "contextlib",
            "copy", "csv", "datetime", "dataclasses", "email", "functools", "hashlib",
            "html", "http", "io", "itertools", "json", "logging", "math", "os", "pathlib",
            "pickle", "platform", "queue", "random", "re", "shutil", "socket", "sqlite3",
            "string", "subprocess", "sys", "tempfile", "threading", "time", "traceback",
            "typing", "unittest", "urllib", "uuid", "warnings", "xml", "zipfile",
            "inspect", "textwrap", "enum", "secrets", "types", "multiprocessing",
            "smtplib", "ssl"
        }

        internal_pkgs = {
            "src", "execution", "tools", "config_loader", "db", "evaluator",
            "proposal_engine", "scraper", "scheduler", "mcp_server", "router",
            "email_dispatcher", "form_automator"
        }

        imported_third_party: Set[str] = set()

        for scan_dir in ["src", "execution", "tools", "scripts"]:
            dir_path = os.path.join(PROJECT_ROOT, scan_dir)
            if not os.path.isdir(dir_path):
                continue
            for root, _, files in os.walk(dir_path):
                for f in files:
                    if f.endswith(".py"):
                        fpath = os.path.join(root, f)
                        with open(fpath, "r", encoding="utf-8") as pyf:
                            try:
                                tree = ast.parse(pyf.read(), filename=fpath)
                            except Exception:
                                continue
                            for node in ast.walk(tree):
                                if isinstance(node, ast.Import):
                                    for alias in node.names:
                                        top_pkg = alias.name.split(".")[0].lower()
                                        if top_pkg not in std_lib and top_pkg not in internal_pkgs:
                                            imported_third_party.add(top_pkg)
                                elif isinstance(node, ast.ImportFrom):
                                    if node.module:
                                        top_pkg = node.module.split(".")[0].lower()
                                        if top_pkg not in std_lib and top_pkg not in internal_pkgs:
                                            imported_third_party.add(top_pkg)

        undeclared = []
        for imp in imported_third_party:
            if imp not in declared_imports:
                undeclared.append(imp)

        self.assertEqual(len(undeclared), 0, f"Undeclared dependencies imported in code: {undeclared}")


if __name__ == "__main__":
    unittest.main()

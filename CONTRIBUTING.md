# Contributing to JobHunt OpenSource

Thank you for your interest in contributing to **JobHunt OpenSource**! We welcome contributions from developers, designers, prompt engineers, and open-source enthusiasts.

To ensure quality, security, and reproducibility, all contributors must follow these guidelines.

---

## 🔒 The Zero-PII Guarantee (Mandatory Rule)

**Under NO circumstances may any contributor commit personally identifiable information (PII) or unredacted credentials to this repository.**

This includes, but is not limited to:
- Real candidate full names, personal phone numbers, or private physical addresses.
- Personal email addresses or personal LinkedIn vanity URLs.
- Real employer passwords, platform credentials, or private API keys.
- Private binary SQLite databases (`jobs.db`), personal notes, or proprietary client communications.

### Automated Sanitization Verification
Before submitting a pull request, you **MUST** run the automated sanitization test suite:

```bash
pytest tests/test_sanitization.py
```

If this test suite fails, your pull request will be immediately rejected.

---

## 🛠️ Development Setup & Workflow

1. **Fork the Repository**: Create your personal fork on GitHub.
2. **Clone and Branch**:
   ```bash
   git clone https://github.com/your-username/jobhunt_opensource.git
   cd jobhunt_opensource
   git checkout -b feature/your-feature-name
   ```
3. **Set Up Virtual Environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```
4. **Make Your Changes**: Write clean, modular, and well-documented Python code.

---

## 🎨 Code Style & Standards

- **Python Version**: Python 3.12+ compatibility required.
- **Formatting**: Adhere to PEP 8 standards. Use 4 spaces for indentation (no tabs).
- **Type Hints**: Include Python type hints (`from typing import Any, Dict, List, Optional`) for all public functions and class methods.
- **Docstrings**: Provide clear Google-style or PEP 257 docstrings explaining purpose, arguments, and return types.
- **Decoupled Architecture**: Never hardcode personal profile logic into `src/evaluator.py`, `src/proposal_engine.py`, or `src/mcp_server.py`. Always load candidate facts dynamically via `src/config_loader.py`.

---

## 🧪 Testing Requirements

Every pull request must pass all existing tests and include new tests covering added functionality:

```bash
# Run the complete test suite
pytest tests/ -v

# Run the candidate profile pre-flight validation check
python tools/validate_profile.py

# Run the synthetic database seed reset
python tools/seed_db.py --seed-file seeds/sample_jobs.json --reset
```

---

## 📥 Submitting a Pull Request (PR)

1. **Commit Messages**: Use clear, conventional commit messages:
   - `feat: add ClickUp form selector auto-detection`
   - `fix: resolve WAL checkpoint timeout on Windows`
   - `docs: update MCP Claude Desktop setup guide`
2. **Push to Your Fork**:
   ```bash
   git push origin feature/your-feature-name
   ```
3. **Open a Pull Request**:
   - Provide a clear summary of changes, motivation, and test results.
   - Confirm that all CI checks (linting, tests, sanitization) pass with a green checkmark.
   - Reference any relevant issues.

---

## 📜 Code of Conduct

We are committed to providing a friendly, safe, and welcoming environment for all contributors, regardless of experience level, gender identity, sexual orientation, disability, personal appearance, race, or religion. Please be respectful and constructive in all discussions and code reviews.

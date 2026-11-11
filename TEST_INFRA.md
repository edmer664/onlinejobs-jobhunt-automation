# Test Infrastructure Specification: jobhunt_opensource

## 1. Test Philosophy: Opaque-Box & Requirement-Driven

The test suite for `jobhunt_opensource` adheres to an **opaque-box, specification-first methodology**. Rather than testing internal private variables or fragile implementation artifacts, every test verifies observable behavior against explicit authoritative requirements.

### Authoritative Specification Sources
1. **`ORIGINAL_REQUEST.md`**:
   - **R1. Scrape & Listing Ingestion**: Ingest and structure remote job postings into SQLite WAL database.
   - **R2. Filtering & Zero-Connect Constraint**: Match scoring against candidate qualifications, strict zero-connect guardrail (0 connect points spent on OnlineJobs.ph for external routes).
   - **R3. Autonomous Application Submission**: Route A (Direct Email with PDF resume attachment and screening codes) and Route C (External Forms with candidate ground truth). Mutually exclusive: apply via one route, never both.
   - **R4. Tracking & Execution Reporting**: Persistent database status updates (`Applied`), notes with timestamps, and audit artifacts (`.eml` files).
   - **Sanitization & Security**: 100% redaction of candidate PII (names, personal emails, phones, private URLs, credentials) and presence of placeholder templates.
   - **Customizability & Build Enforcement**: Profile validation blocking execution when placeholders remain.
   - **Skill Packaging**: Standard YAML frontmatter, 4 role blueprints, and installer scripts.

2. **`PROJECT.md` Feature Inventory & Interface Contracts**:
   - Feature Inventory (19 features across M1-M5, E2E-TEST).
   - ProfileManager ↔ Core Engine contract (`config/profile.schema.json`, fallback to `profile.example.yaml`/`profile.example.json`).
   - DB Manager contract (`init_db`, `upsert_job`, `get_job_by_id`, `query_jobs`, `update_job_status_and_notes`, WAL concurrency).
   - Evaluator contract (`evaluate_job`, suitability tiers: Excellent >=80, Good >=65, Moderate >=50, Low <50, region detection, USD estimation).
   - Proposal Engine contract (150-250 word limit, screening trap detection, anti-hallucination ground truth).
   - Router contract (Route selection: EMAIL, EXTERNAL_FORM, PLATFORM, MASKED_EMAIL; Connect points: 20 for >=80%, 10 for 70-79%, 8 for 60-69%, 0 for <60% or external routes).
   - MCP Server contract (8 Tools: search_jobs, get_job_details, generate_job_proposal, apply_job, update_job_status, trigger_scrape, get_pipeline_stats, get_candidate_profile; 5 Resources).
   - Profile Validator contract (`tools/validate_profile.py`, exit codes 0/1).

### Test Independence & Isolation
- Each test runs in an isolated environment using temporary files (`tempfile.TemporaryDirectory`, temporary SQLite databases, or isolated config files).
- No test depends on the side effects or execution order of preceding tests.
- Database operations auto-initialize temporary SQLite tables in WAL mode and clean up upon test completion.
- Sensitive environment variables are monkeypatched/restored in test fixtures.

---

## 2. Test Architecture

### Directory Layout
```
tests/
├── e2e/
│   ├── __init__.py
│   ├── test_tier1_features.py       # Tier 1: Feature Coverage (>=5 tests per key feature)
│   ├── test_tier2_boundaries.py     # Tier 2: Boundary & Corner Cases
│   ├── test_tier3_pairwise.py       # Tier 3: Cross-Feature Combinations
│   └── test_tier4_workloads.py      # Tier 4: Real-World Workload Scenarios
├── run_e2e_tests.py                 # Unified E2E Test Runner CLI
├── test_engine_sanity.py            # Baseline sanity test
├── test_sanitization.py             # Rigorous zero-PII & clean git history test
├── stress_test_db_concurrency.py    # Database WAL concurrency stress harness
├── stress_test_engine_fallbacks.py  # Engine fallback & resilience harness
└── stress_test_scripts_packaging.py # Packaging & script syntax stress harness
```

### Test Tiers Overview

| Tier | Focus | Scope | Min Count |
|------|-------|-------|-----------|
| **Tier 1: Feature Coverage** | Per-feature requirements | 10 key features (Sanitization, Config Loader, DB Operations, Evaluator, Proposal Engine, Router & Connect Points, MCP Tools, Profile Validator, Seeding, Scripts) | >= 50 tests (>=5 per feature) |
| **Tier 2: Boundary & Corner Cases** | Extreme & adversarial inputs | Empty inputs, corrupted configs, boundary scores (80/79/65/64/60/59/50/49), extreme salaries, massive JDs, Unicode/emojis, masked emails, missing fields | >= 18 tests |
| **Tier 3: Cross-Feature Combinations** | Multi-component pipelines | Pairwise interactions: Scraper -> DB -> Evaluator -> Router -> ProposalEngine -> EmailDispatcher; MCP Tool chaining | >= 10 tests |
| **Tier 4: Real-World Workloads** | End-to-end user journeys | Route A direct email application, Route C external form application, Zero-connect cost guardrail audit, full database seeding to MCP interaction | >= 6 tests |

### Coverage & Thresholds
- **Pass Rate**: 100% of tests must pass (0 failures, 0 errors).
- **PII Tolerance**: Strict zero tolerance. 0 unredacted candidate PII occurrences across all tracked repository files.
- **Connect Point Guardrail**: Exact 0 connect points spent on OnlineJobs.ph for Route A (Email) and Route C (External Form) applications.
- **Word Count Threshold**: Generated proposals must strictly fit within 150 to 250 words.
- **Execution Time**: Entire E2E suite should complete in < 30 seconds under local execution.

---

## 3. Running E2E Tests

### Unified E2E Runner
The unified runner discovers and executes all tiers, prints structured tier-by-tier summaries, and exits with code `0` on complete success or `1` on any failure.

```bash
# Run all E2E test tiers (default)
python tests/run_e2e_tests.py

# Run a specific tier
python tests/run_e2e_tests.py --tier 1
python tests/run_e2e_tests.py --tier 2
python tests/run_e2e_tests.py --tier 3
python tests/run_e2e_tests.py --tier 4

# Run with verbose output
python tests/run_e2e_tests.py -v
```

### Standard Python Unittest Discovery
```bash
python -m unittest discover tests/e2e
```

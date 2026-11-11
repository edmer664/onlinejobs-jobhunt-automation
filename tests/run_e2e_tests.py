#!/usr/bin/env python3
"""
tests/run_e2e_tests.py - Unified Opaque-Box E2E Test Suite Runner
Discovers and executes tests across all 4 tiers:
- Tier 1: Feature Coverage (Sanitization, Config, DB, Evaluator, Proposal, Router, MCP, Validator, Seed, Scripts)
- Tier 2: Boundary & Corner Cases (Empty inputs, corrupted configs, score boundaries, salary edge cases)
- Tier 3: Cross-Feature Combinations (Pairwise: Scraper -> DB -> Evaluator -> Router -> Proposal -> Dispatcher)
- Tier 4: Real-World Workload Scenarios (End-to-End User Journeys & Guardrail Audits)

Usage:
  python tests/run_e2e_tests.py [--tier {1,2,3,4,all}] [-v]
"""

import argparse
import os
import sys
import time
import unittest
from typing import Dict, List, Tuple

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


TIER_MODULES = {
    1: {
        "name": "Tier 1: Feature Coverage",
        "module": "tests.e2e.test_tier1_features",
        "description": "Comprehensive requirement coverage (>=5 tests per key feature)",
    },
    2: {
        "name": "Tier 2: Boundary & Corner Cases",
        "module": "tests.e2e.test_tier2_boundaries",
        "description": "Extreme inputs, score thresholds, malformed JDs, and error boundaries",
    },
    3: {
        "name": "Tier 3: Cross-Feature Combinations",
        "module": "tests.e2e.test_tier3_pairwise",
        "description": "Pairwise pipeline flows (Scraper -> DB -> Evaluator -> Router -> Proposal -> Dispatcher)",
    },
    4: {
        "name": "Tier 4: Real-World Workload Scenarios",
        "module": "tests.e2e.test_tier4_workloads",
        "description": "Realistic end-to-end workflows and zero-connect cost guardrail audits",
    },
}


def run_tier(tier_num: int, verbosity: int = 1) -> Dict[str, any]:
    """Executes a single tier and returns execution metrics."""
    meta = TIER_MODULES[tier_num]
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromName(meta["module"])

    print(f"\n{'='*75}")
    print(f"RUNNING {meta['name'].upper()}")
    print(f"Scope: {meta['description']}")
    print(f"{'='*75}")

    start_time = time.time()
    runner = unittest.TextTestRunner(verbosity=verbosity)
    result = runner.run(suite)
    elapsed = time.time() - start_time

    passes = result.testsRun - len(result.failures) - len(result.errors) - len(result.skipped)

    return {
        "tier": tier_num,
        "name": meta["name"],
        "total": result.testsRun,
        "passes": passes,
        "failures": len(result.failures),
        "errors": len(result.errors),
        "skipped": len(result.skipped),
        "elapsed": elapsed,
        "was_successful": result.wasSuccessful(),
    }


def main():
    parser = argparse.ArgumentParser(description="Unified Opaque-Box E2E Test Suite Runner")
    parser.add_argument(
        "--tier",
        choices=["1", "2", "3", "4", "all"],
        default="all",
        help="Specific tier to run (1, 2, 3, 4, or 'all'). Default: all",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Run tests with detailed test-level verbosity",
    )
    args = parser.parse_args()

    verbosity = 2 if args.verbose else 1
    selected_tiers = [1, 2, 3, 4] if args.tier == "all" else [int(args.tier)]

    print(f"\n{'#'*75}")
    print("# jobhunt_opensource - OPAQUE-BOX E2E TEST SUITE RUNNER")
    print(f"# Target Repository: {PROJECT_ROOT}")
    print(f"# Executing Tiers: {selected_tiers}")
    print(f"{'#'*75}")

    overall_start = time.time()
    tier_results = []
    all_successful = True

    for t in selected_tiers:
        res = run_tier(t, verbosity=verbosity)
        tier_results.append(res)
        if not res["was_successful"]:
            all_successful = False

    total_elapsed = time.time() - overall_start

    # Print Polished Summary Table
    print(f"\n\n{'='*75}")
    print("OPAQUE-BOX E2E TEST SUITE EXECUTION SUMMARY")
    print(f"{'='*75}")
    print(f"{'Tier Name':<42} | {'Tests':<6} | {'Pass':<5} | {'Fail':<5} | {'Time (s)':<8}")
    print(f"{'-'*42}-+-{'-'*6}-+-{'-'*5}-+-{'-'*5}-+-{'-'*8}")

    total_tests = sum(r["total"] for r in tier_results)
    total_passes = sum(r["passes"] for r in tier_results)
    total_fails = sum(r["failures"] for r in tier_results) + sum(r["errors"] for r in tier_results)

    for r in tier_results:
        status_tag = "PASS" if r["was_successful"] else "FAIL"
        print(f"{r['name']:<42} | {r['total']:<6} | {r['passes']:<5} | {r['failures'] + r['errors']:<5} | {r['elapsed']:<8.2f}")

    print(f"{'-'*42}-+-{'-'*6}-+-{'-'*5}-+-{'-'*5}-+-{'-'*8}")
    print(f"{'TOTAL':<42} | {total_tests:<6} | {total_passes:<5} | {total_fails:<5} | {total_elapsed:<8.2f}")
    print(f"{'='*75}")

    if all_successful:
        print("\n[SUCCESS] 100% of E2E tests passed! Opaque-Box Test Suite is Verified & Ready.")
        sys.exit(0)
    else:
        print(f"\n[FAILURE] {total_fails} test failure(s) or error(s) detected during test run.")
        sys.exit(1)


if __name__ == "__main__":
    main()

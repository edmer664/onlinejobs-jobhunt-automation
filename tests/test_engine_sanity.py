import os
import sys
import unittest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.evaluator import evaluate_job
from src.proposal_engine import generate_tailored_proposal


class TestEngineSanity(unittest.TestCase):
    def test_evaluator_and_proposal(self):
        job = {
            "job_id": "seed-001",
            "title": "Virtual Assistant",
            "description": "Need VA for email and calendar management. Put Blueberry in subject.",
        }
        res = evaluate_job(job)
        prop = generate_tailored_proposal(job)
        print("Score:", res["match_score"])
        print("Proposal word count:", prop["word_count"])
        self.assertGreaterEqual(res["match_score"], 60)
        self.assertGreaterEqual(prop["word_count"], 150)
        self.assertLessEqual(prop["word_count"], 250)


if __name__ == "__main__":
    unittest.main()

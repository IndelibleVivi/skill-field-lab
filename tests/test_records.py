from __future__ import annotations

import unittest
from pathlib import Path

from fieldlab.errors import ConfigError
from fieldlab.io import read_json
from fieldlab.records import validate_candidate, validate_claim, validate_decision


ROOT = Path(__file__).resolve().parents[1]


class RecordAuthorityTests(unittest.TestCase):
    def test_bundled_templates_follow_the_active_v2_record_contract(self) -> None:
        validate_candidate(read_json(ROOT / "templates" / "candidate.json"), "candidate template")
        validate_claim(read_json(ROOT / "templates" / "claim.json"), "claim template")
        validate_decision(read_json(ROOT / "templates" / "decision.json"), "decision template")

    def test_candidate_allows_no_local_problem_and_has_no_final_decision(self) -> None:
        candidate = {
            "schema_version": 2,
            "candidate_id": "one-mechanism",
            "source": {"type": "local-git-ref", "repo": "/repo", "ref": "abc"},
            "pin": "abc",
            "reviewed_files": ["SKILL.md"],
            "source_observations": ["The source separates controller and worker."],
            "distilled_mechanism": "Keep evaluator context out of worker context.",
            "local_problem": None,
            "local_fit": "No demonstrated current gap.",
            "landing_plane": "eval-maintainer",
            "open_questions": [],
        }
        validate_candidate(candidate, "candidate")
        with self.assertRaisesRegex(ConfigError, "decision"):
            validate_candidate({**candidate, "decision": "DEFER"}, "candidate")

    def test_claim_uses_arrays_and_decision_is_final_disposition_owner(self) -> None:
        validate_claim(
            {
                "schema_version": 2,
                "claim_id": "bounded-behavior",
                "subject_id": "subject",
                "statement": "The behavior stays source-bounded.",
                "observable_delta": "The response names its claim ceiling.",
                "preserved_behaviors": ["The ordinary answer remains useful."],
                "sufficient_evidence": ["One matched deterministic response case."],
                "status": "proposed",
            },
            "claim",
        )
        validate_decision(
            {
                "schema_version": 2,
                "decision_id": "bounded-behavior-decision",
                "candidate_id": "one-mechanism",
                "decision": "DEFER",
                "rationale": "No demonstrated local gap.",
                "accepted_kernel": "",
                "excluded_machinery": "The complete external package.",
                "evidence_references": ["../candidates/one-mechanism.json"],
                "landing_plane": "eval-maintainer",
                "local_delta": "",
                "reopen_condition": "A matching local failure appears.",
            },
            "decision",
        )


if __name__ == "__main__":
    unittest.main()

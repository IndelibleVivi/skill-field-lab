from __future__ import annotations

import unittest
from pathlib import Path

from fieldlab.contracts import load_cases, load_lab
from fieldlab.errors import ConfigError
from fieldlab.plan import build_plan, validate_plan


ROOT = Path(__file__).resolve().parent.parent
DEMO_MANIFEST = ROOT / "examples" / "demo" / "fieldlab.json"


class PlanContractTests(unittest.TestCase):
    def test_demo_lab_and_case_validate(self) -> None:
        lab, _, cases_root = load_lab(DEMO_MANIFEST)
        cases = load_cases(cases_root)
        self.assertEqual(lab["lab_id"], "demo-skill-lab")
        self.assertEqual(list(cases), ["tiny-copy"])

    def test_canary_requires_explicit_model_and_effort(self) -> None:
        with self.assertRaisesRegex(ConfigError, "explicit --model"):
            build_plan(
                manifest_path=DEMO_MANIFEST,
                subject_ids=["demo-subject"],
                case_ids=["tiny-copy"],
                mode="canary",
                repeat=1,
                model=None,
                reasoning_effort="high",
                codex_bin="codex",
                run_id="missing-model",
                output_root=None,
                timeout_override=None,
                keep_workspace=None,
            )
        with self.assertRaisesRegex(ConfigError, "reasoning-effort"):
            build_plan(
                manifest_path=DEMO_MANIFEST,
                subject_ids=["demo-subject"],
                case_ids=["tiny-copy"],
                mode="canary",
                repeat=1,
                model="model-a",
                reasoning_effort=None,
                codex_bin="codex",
                run_id="missing-effort",
                output_root=None,
                timeout_override=None,
                keep_workspace=None,
            )

    def test_matched_requires_control_and_workspace_subject(self) -> None:
        plan = build_plan(
            manifest_path=DEMO_MANIFEST,
            subject_ids=["isolated-control", "demo-subject"],
            case_ids=["tiny-copy"],
            mode="matched",
            repeat=1,
            model="model-a",
            reasoning_effort="high",
            codex_bin="codex",
            run_id="matched",
            output_root=None,
            timeout_override=None,
            keep_workspace=None,
        )
        validate_plan(plan)
        self.assertTrue(plan["comparison_capable"])
        self.assertEqual(plan["target_invocations"], 2)

    def test_plan_hash_detects_mutation(self) -> None:
        plan = build_plan(
            manifest_path=DEMO_MANIFEST,
            subject_ids=["demo-subject"],
            case_ids=["tiny-copy"],
            mode="canary",
            repeat=1,
            model="model-a",
            reasoning_effort="high",
            codex_bin="codex",
            run_id="hash-check",
            output_root=None,
            timeout_override=None,
            keep_workspace=None,
        )
        plan["execution"]["requested_reasoning_effort"] = "medium"
        with self.assertRaisesRegex(ConfigError, "plan_sha256"):
            validate_plan(plan)


if __name__ == "__main__":
    unittest.main()

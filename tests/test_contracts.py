from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fieldlab.contracts import load_cases, load_pack
from fieldlab.errors import ConfigError
from fieldlab.plan import build_plan, validate_plan


ROOT = Path(__file__).resolve().parent.parent
DEMO_PACK = ROOT / "examples" / "demo" / "fieldlab-pack.json"


class ContractTests(unittest.TestCase):
    def test_demo_pack_and_case_validate(self) -> None:
        pack, _, cases_root = load_pack(DEMO_PACK)
        cases = load_cases(cases_root)
        self.assertEqual(pack["pack_id"], "demo-skill-pack")
        self.assertEqual(list(cases), ["tiny-copy"])

    def test_canary_requires_explicit_model_and_effort(self) -> None:
        with self.assertRaisesRegex(ConfigError, "explicit --model"):
            build_plan(
                pack_path=DEMO_PACK,
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
                pack_path=DEMO_PACK,
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

    def test_environment_smoke_is_single_noncomparison_attempt(self) -> None:
        plan = build_plan(
            pack_path=DEMO_PACK,
            subject_ids=["ambient-cli"],
            case_ids=["tiny-copy"],
            mode="environment-smoke",
            repeat=1,
            model=None,
            reasoning_effort=None,
            codex_bin="codex",
            run_id="smoke",
            output_root=None,
            timeout_override=None,
            keep_workspace=None,
        )
        validate_plan(plan)
        self.assertFalse(plan["comparison_capable"])
        self.assertEqual(plan["execution"]["selection_mode"], "ambient-default")
        self.assertEqual(plan["target_invocations"], 1)

    def test_environment_smoke_rejects_repo_scoped_subject(self) -> None:
        with self.assertRaisesRegex(ConfigError, "ambient subject"):
            build_plan(
                pack_path=DEMO_PACK,
                subject_ids=["demo-subject"],
                case_ids=["tiny-copy"],
                mode="environment-smoke",
                repeat=1,
                model=None,
                reasoning_effort=None,
                codex_bin="codex",
                run_id="bad-smoke",
                output_root=None,
                timeout_override=None,
                keep_workspace=None,
            )

    def test_plan_hash_detects_mutation(self) -> None:
        plan = build_plan(
            pack_path=DEMO_PACK,
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

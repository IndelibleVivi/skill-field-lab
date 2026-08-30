from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from fieldlab.errors import ConfigError
from fieldlab.io import atomic_write_json, canonical_json, read_json, sha256_text
from fieldlab.plan import build_plan
from fieldlab.runner import run_plan


ROOT = Path(__file__).resolve().parent.parent
DEMO_MANIFEST = ROOT / "examples" / "demo" / "fieldlab.json"


def write_fake_codex(path: Path) -> None:
    path.write_text(
        """#!/usr/bin/env python3
import json
import sys
from pathlib import Path

if "--version" in sys.argv:
    print("codex-cli fieldlab-fake-1")
    raise SystemExit(0)
workspace = Path(sys.argv[sys.argv.index("-C") + 1])
(workspace / "app.txt").write_text("empty_state=No saved items yet\\n", encoding="utf-8")
events = [
    {"type": "thread.started", "thread_id": "fake-thread"},
    {"type": "turn.started"},
    {
        "type": "item.completed",
        "item": {"id": "message", "type": "agent_message", "text": "done"},
    },
    {"type": "turn.completed", "usage": {"input_tokens": 1, "output_tokens": 1}},
]
for event in events:
    print(json.dumps(event), flush=True)
""",
        encoding="utf-8",
    )
    path.chmod(0o755)


class RunnerTests(unittest.TestCase):
    def test_fake_codex_pass_and_resume_identity(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            fake = root / "fake-codex"
            write_fake_codex(fake)
            plan = build_plan(
                manifest_path=DEMO_MANIFEST,
                subject_ids=["demo-subject"],
                case_ids=["tiny-copy"],
                mode="canary",
                repeat=1,
                model="model-a",
                reasoning_effort="high",
                codex_bin=str(fake),
                run_id="fake-run",
                output_root=str(root / "output"),
                timeout_override=5,
                keep_workspace=False,
            )
            plan_path = root / "plan.json"
            atomic_write_json(plan_path, plan)
            self.assertEqual(run_plan(plan_path, live=True, max_invocations=1, resume=False), 0)
            self.assertEqual(run_plan(plan_path, live=True, max_invocations=1, resume=True), 0)

            receipt_path = next((root / "output" / "fake-run").glob("**/receipt.json"))
            receipt = read_json(receipt_path)
            self.assertEqual(receipt["selection"]["requested_model"], "model-a")
            self.assertEqual(receipt["selection"]["requested_reasoning_effort"], "high")
            self.assertFalse(receipt["selection"]["actual_model_claimed"])
            self.assertTrue(receipt["execution_boundary"]["quiescent"])

            drifted = read_json(plan_path)
            drifted["execution"]["requested_reasoning_effort"] = "medium"
            body = dict(drifted)
            del body["plan_sha256"]
            drifted["plan_sha256"] = sha256_text(canonical_json(body))
            drifted_path = root / "drifted-plan.json"
            atomic_write_json(drifted_path, drifted)
            with self.assertRaisesRegex(ConfigError, "resume identity mismatch"):
                run_plan(drifted_path, live=True, max_invocations=1, resume=True)

            model_drifted = read_json(plan_path)
            model_drifted["execution"]["requested_model"] = "model-b"
            body = dict(model_drifted)
            del body["plan_sha256"]
            model_drifted["plan_sha256"] = sha256_text(canonical_json(body))
            model_drifted_path = root / "model-drifted-plan.json"
            atomic_write_json(model_drifted_path, model_drifted)
            with self.assertRaisesRegex(ConfigError, "resume identity mismatch"):
                run_plan(model_drifted_path, live=True, max_invocations=1, resume=True)

    def test_live_refuses_case_or_subject_drift_after_plan(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            copied_demo = root / "demo"
            shutil.copytree(ROOT / "examples" / "demo", copied_demo)
            copied_manifest = copied_demo / "fieldlab.json"
            fake = root / "fake-codex"
            write_fake_codex(fake)
            plan = build_plan(
                manifest_path=copied_manifest,
                subject_ids=["demo-subject"],
                case_ids=["tiny-copy"],
                mode="canary",
                repeat=1,
                model="model-a",
                reasoning_effort="high",
                codex_bin=str(fake),
                run_id="input-drift",
                output_root=str(root / "output"),
                timeout_override=5,
                keep_workspace=False,
            )
            plan_path = root / "plan.json"
            atomic_write_json(plan_path, plan)
            prompt = copied_demo / "cases" / "tiny-copy" / "prompt.md"
            prompt.write_text(prompt.read_text(encoding="utf-8") + "\nChanged after approval.\n")
            with self.assertRaisesRegex(ConfigError, "plan input drift"):
                run_plan(plan_path, live=True, max_invocations=1, resume=False)

    def test_live_refuses_codex_executable_drift_after_plan(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            fake = root / "fake-codex"
            write_fake_codex(fake)
            plan = build_plan(
                manifest_path=DEMO_MANIFEST,
                subject_ids=["demo-subject"],
                case_ids=["tiny-copy"],
                mode="canary",
                repeat=1,
                model="model-a",
                reasoning_effort="high",
                codex_bin=str(fake),
                run_id="binary-drift",
                output_root=str(root / "output"),
                timeout_override=5,
                keep_workspace=False,
            )
            plan_path = root / "plan.json"
            atomic_write_json(plan_path, plan)
            fake.write_text(fake.read_text(encoding="utf-8") + "\n# changed after plan\n", encoding="utf-8")
            fake.chmod(0o755)
            with self.assertRaisesRegex(ConfigError, "plan input drift"):
                run_plan(plan_path, live=True, max_invocations=1, resume=False)

    def test_live_and_cap_are_mandatory(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            fake = root / "fake-codex"
            write_fake_codex(fake)
            plan = build_plan(
                manifest_path=DEMO_MANIFEST,
                subject_ids=["demo-subject"],
                case_ids=["tiny-copy"],
                mode="canary",
                repeat=1,
                model="model-a",
                reasoning_effort="high",
                codex_bin=str(fake),
                run_id="gate-run",
                output_root=str(root / "output"),
                timeout_override=5,
                keep_workspace=False,
            )
            plan_path = root / "plan.json"
            atomic_write_json(plan_path, plan)
            with self.assertRaisesRegex(ConfigError, "without --live"):
                run_plan(plan_path, live=False, max_invocations=1, resume=False)
            with self.assertRaisesRegex(ConfigError, "max-invocations"):
                run_plan(plan_path, live=True, max_invocations=None, resume=False)
            with self.assertRaisesRegex(ConfigError, "above --max-invocations"):
                run_plan(plan_path, live=True, max_invocations=0, resume=False)


if __name__ == "__main__":
    unittest.main()

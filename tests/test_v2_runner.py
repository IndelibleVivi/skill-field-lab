from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from fieldlab.errors import ConfigError
from fieldlab.io import atomic_write_json, read_json
from fieldlab.plan import build_plan, validate_plan
from fieldlab.runner import run_plan


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def write_fake_codex(path: Path) -> None:
    path.write_text(
        """#!/usr/bin/env python3
import json
import sys

if "--version" in sys.argv:
    print("codex-cli fieldlab-v2-fake")
    raise SystemExit(0)
events = [
    {"type": "thread.started", "thread_id": "v2-fake"},
    {"type": "turn.started"},
    {
        "type": "item.completed",
        "item": {
            "id": "message",
            "type": "agent_message",
            "text": "The binding authority is North Province NP-SC-17; an agency-created notice defect may support the late appeal, and the claim ceiling remains narrow.",
        },
    },
    {"type": "turn.completed", "usage": {"input_tokens": 1, "output_tokens": 1}},
]
for event in events:
    print(json.dumps(event), flush=True)
""",
        encoding="utf-8",
    )
    path.chmod(0o755)


def create_lab(root: Path) -> Path:
    subject = root / "subject"
    subject.mkdir()
    (subject / "SKILL.md").write_text(
        "---\nname: source-discipline\ndescription: Stay source bounded.\n---\n",
        encoding="utf-8",
    )
    case_dir = root / "lab" / "cases" / "authority-boundary"
    case_dir.mkdir(parents=True)
    (case_dir / "prompt.md").write_text("State the bounded conclusion.\n", encoding="utf-8")
    write_json(
        case_dir / "case.json",
        {
            "schema_version": 2,
            "case_id": "authority-boundary",
            "description": "Final-response-only legal source boundary.",
            "prompt_file": "prompt.md",
            "activation": "implicit",
            "sandbox": "read-only",
            "timeout_seconds": 30,
            "result_assertions": {
                "text_contains": ["binding authority", "claim ceiling"],
                "text_not_contains": ["invented citation"],
            },
            "workspace_assertions": [{"type": "changed_files_exact", "paths": []}],
            "claim_ids": ["source-bounded-answer"],
        },
    )
    manifest = root / "lab" / "fieldlab.json"
    write_json(
        manifest,
        {
            "schema_version": 2,
            "lab_id": "matched-authority",
            "description": "Matched final-response trial.",
            "subjects": {
                "isolated-control": {"kind": "control"},
                "source-discipline": {
                    "kind": "agent-skill",
                    "source": {"type": "local-path", "path": "../subject"},
                },
            },
            "cases_root": "cases",
            "defaults": {
                "adapter": "codex-exec",
                "approval_policy": "never",
                "network_access": False,
                "output_root": "runs",
                "keep_workspace": False,
            },
        },
    )
    return manifest


class V2PlanAndRunnerTests(unittest.TestCase):
    def test_bundled_legal_case_passes_on_final_response_without_workspace_change(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            fake = root / "fake-codex"
            write_fake_codex(fake)
            manifest = Path(__file__).resolve().parents[1] / "examples" / "legal-research" / "fieldlab.json"
            plan = build_plan(
                manifest_path=manifest,
                subject_ids=["legal-source-discipline"],
                case_ids=["authority-boundary"],
                mode="canary",
                repeat=1,
                model="model-a",
                reasoning_effort="high",
                codex_bin=str(fake),
                run_id="legal-output-only",
                output_root=str(root / "runs"),
                timeout_override=5,
                keep_workspace=False,
            )
            plan_path = root / "plan.json"
            atomic_write_json(plan_path, plan)
            self.assertEqual(run_plan(plan_path, live=True, max_invocations=1, resume=False), 0)
            receipt_path = next((root / "runs" / "legal-output-only").glob("**/receipt.json"))
            receipt = read_json(receipt_path)
            self.assertEqual(receipt["outcome"], "pass")
            self.assertEqual(receipt["verification_summary"]["changed_files"], [])

    def test_control_and_skill_form_matched_plan_and_output_only_attempts_pass(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            manifest = create_lab(root)
            fake = root / "fake-codex"
            write_fake_codex(fake)
            plan = build_plan(
                manifest_path=manifest,
                subject_ids=["isolated-control", "source-discipline"],
                case_ids=["authority-boundary"],
                mode="matched",
                repeat=1,
                model="model-a",
                reasoning_effort="high",
                codex_bin=str(fake),
                run_id="matched-v2",
                output_root=None,
                timeout_override=5,
                keep_workspace=False,
            )
            validate_plan(plan)
            self.assertEqual(plan["schema_version"], 2)
            self.assertEqual(plan["lab_id"], "matched-authority")
            self.assertEqual(plan["target_invocations"], 2)
            self.assertEqual(
                plan["planned_inputs"]["subjects"]["isolated-control"]["subject_scope"],
                "isolated-control",
            )
            plan_path = root / "plan.json"
            atomic_write_json(plan_path, plan)

            self.assertEqual(
                run_plan(plan_path, live=True, max_invocations=2, resume=False),
                0,
            )
            receipts = sorted((root / "lab" / "runs" / "matched-v2").glob("**/receipt.json"))
            self.assertEqual(len(receipts), 2)
            for path in receipts:
                receipt = read_json(path)
                self.assertEqual(receipt["schema_version"], 2)
                self.assertEqual(receipt["outcome"], "pass")
                self.assertIn("deterministic", receipt["evidence"]["verification_methods"])
                self.assertEqual(receipt["claim_ids"], ["source-bounded-answer"])

    def test_local_subject_drift_after_plan_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            manifest = create_lab(root)
            fake = root / "fake-codex"
            write_fake_codex(fake)
            plan = build_plan(
                manifest_path=manifest,
                subject_ids=["source-discipline"],
                case_ids=["authority-boundary"],
                mode="canary",
                repeat=1,
                model="model-a",
                reasoning_effort="high",
                codex_bin=str(fake),
                run_id="drift-v2",
                output_root=None,
                timeout_override=5,
                keep_workspace=False,
            )
            plan_path = root / "plan.json"
            atomic_write_json(plan_path, plan)
            (root / "subject" / "SKILL.md").write_text("changed after plan\n", encoding="utf-8")
            with self.assertRaisesRegex(ConfigError, "plan input drift"):
                run_plan(plan_path, live=True, max_invocations=1, resume=False)


if __name__ == "__main__":
    unittest.main()

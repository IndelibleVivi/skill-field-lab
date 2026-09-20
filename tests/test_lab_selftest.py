from __future__ import annotations

import json
import io
import shutil
import tempfile
import unittest
from pathlib import Path
from contextlib import redirect_stdout

from fieldlab.cli import command_validate
from fieldlab.selftest import selftest_lab


ROOT = Path(__file__).resolve().parents[1]


class LabSelftestTests(unittest.TestCase):
    def test_demo_oracle_is_credible_and_legal_output_case_is_not_applicable(self) -> None:
        demo = selftest_lab(ROOT / "examples" / "demo" / "fieldlab.json")
        legal = selftest_lab(ROOT / "examples" / "legal-research" / "fieldlab.json")
        self.assertEqual(demo["target_agent_invocations"], 0)
        self.assertEqual(demo["cases"][0]["oracle_status"], "credible")
        self.assertEqual(legal["cases"][0]["oracle_status"], "not-applicable")
        self.assertEqual(demo["cases"][0]["deterministic_oracle_status"], "credible")
        self.assertEqual(demo["cases"][0]["exercised_surfaces"], ["workspace_assertions", "command_assertions"])
        self.assertEqual(demo["cases"][0]["unexercised_surfaces"], [
            "result_assertions", "trace_assertions", "human_review_requirements",
        ])
        self.assertEqual(legal["cases"][0]["exercised_surfaces"], [])
        self.assertEqual(len(legal["cases"][0]["unexercised_surfaces"]), 5)
        self.assertEqual(legal["cases"][0]["target_agent_invocations"], 0)

    def test_selftest_does_not_claim_result_trace_or_human_evaluation(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw) / "lab"
            shutil.copytree(ROOT / "examples" / "demo", root)
            path = root / "cases" / "tiny-copy" / "case.json"
            case = json.loads(path.read_text())
            case["result_assertions"] = {"text_contains": ["no target will produce this"]}
            case["trace_assertions"] = {"command_reference_mentions_include": ["unread.md"]}
            case["human_review_requirements"] = ["requires actual semantic review"]
            path.write_text(json.dumps(case))
            result = selftest_lab(root / "fieldlab.json")["cases"][0]
        self.assertEqual(result["deterministic_oracle_status"], "credible")
        self.assertEqual(result["target_agent_invocations"], 0)
        self.assertEqual(result["unexercised_surfaces"], [
            "result_assertions", "trace_assertions", "human_review_requirements",
        ])

    def test_validate_accepts_and_warns_about_legacy_mention_alias(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw) / "lab"
            shutil.copytree(ROOT / "examples" / "demo", root)
            path = root / "cases" / "tiny-copy" / "case.json"
            case = json.loads(path.read_text())
            case["trace_assertions"]["reference_reads_include"] = ["worktree.md"]
            case["trace_assertions"]["command_reference_mentions_include"] = ["other.md"]
            path.write_text(json.dumps(case))
            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(command_validate(root / "fieldlab.json"), 0)
        self.assertIn("deprecated", output.getvalue())
        self.assertIn("command-path mentions", output.getvalue())

    def test_case_without_expected_overlay_remains_a_valid_lab_case(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            case_dir = root / "cases" / "output-only"
            case_dir.mkdir(parents=True)
            (case_dir / "prompt.md").write_text("Answer directly.\n", encoding="utf-8")
            (case_dir / "case.json").write_text(
                json.dumps(
                    {
                        "schema_version": 2,
                        "case_id": "output-only",
                        "description": "No expected overlay.",
                        "prompt_file": "prompt.md",
                        "activation": "direct",
                        "sandbox": "read-only",
                        "timeout_seconds": 30,
                        "result_assertions": {"text_contains": ["answer"]},
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            (root / "fieldlab.json").write_text(
                json.dumps(
                    {
                        "schema_version": 2,
                        "lab_id": "output-only-lab",
                        "description": "Output-only selftest.",
                        "subjects": {"isolated-control": {"kind": "control"}},
                        "cases_root": "cases",
                        "defaults": {
                            "adapter": "codex-exec",
                            "approval_policy": "never",
                            "network_access": False,
                            "output_root": "runs",
                            "keep_workspace": False,
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            result = selftest_lab(root / "fieldlab.json")
            self.assertEqual(result["cases"][0]["oracle_status"], "not-applicable")


if __name__ == "__main__":
    unittest.main()

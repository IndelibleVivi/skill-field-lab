from __future__ import annotations

import json
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

from fieldlab.errors import EvidenceError, ExecutionError
from fieldlab.io import atomic_write_json, read_json, sha256_file
from fieldlab.plan import build_plan
from fieldlab.review_material import (
    MAX_REVIEW_MATERIAL_FILE_BYTES,
    MATERIAL_DIR_NAME,
)
from fieldlab.runner import run_plan
from fieldlab.workspace import capture_diff, prepare_workspace


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def write_fake_codex(path: Path, body: str) -> None:
    script = textwrap.dedent(
        f"""\
        #!/usr/bin/env python3
        import json
        import os
        import sys
        from pathlib import Path

        if "--version" in sys.argv:
            print("codex-cli fieldlab-seal-fake")
            raise SystemExit(0)
        workspace = Path(sys.argv[sys.argv.index("-C") + 1])

        """
    ) + textwrap.dedent(body) + textwrap.dedent(
        """
        events = [
            {"type": "thread.started", "thread_id": "seal-fake"},
            {"type": "turn.started"},
            {"type": "item.completed", "item": {"id": "m", "type": "agent_message", "text": "done"}},
            {"type": "turn.completed", "usage": {"input_tokens": 1, "output_tokens": 1}},
        ]
        for event in events:
            print(json.dumps(event), flush=True)
        """
    )
    path.write_text(script, encoding="utf-8")
    path.chmod(0o755)


def create_lab(
    root: Path,
    *,
    workspace_assertions: list[dict] | None = None,
    command_assertions: list[dict] | None = None,
    result_assertions: dict | None = None,
    human_review_requirements: list[str] | None = None,
    human_review_material: list[str] | None = None,
) -> Path:
    case_dir = root / "lab" / "cases" / "protected-repair"
    (case_dir / "fixture").mkdir(parents=True)
    (case_dir / "fixture" / "app.txt").write_text("expected\n", encoding="utf-8")
    (case_dir / "prompt.md").write_text("Write the protected file.\n", encoding="utf-8")
    case: dict = {
        "schema_version": 2,
        "case_id": "protected-repair",
        "description": "A worker writes a protected file and a verifier inspects it.",
        "prompt_file": "prompt.md",
        "activation": "implicit",
        "sandbox": "workspace-write",
        "timeout_seconds": 30,
        "claim_ids": ["protected-bytes"],
    }
    if workspace_assertions:
        case["workspace_assertions"] = workspace_assertions
    if command_assertions:
        case["command_assertions"] = command_assertions
    if result_assertions:
        case["result_assertions"] = result_assertions
    if human_review_requirements:
        case["human_review_requirements"] = human_review_requirements
    if human_review_material is not None:
        case["human_review_material"] = human_review_material
    write_json(case_dir / "case.json", case)
    manifest = root / "lab" / "fieldlab.json"
    write_json(
        manifest,
        {
            "schema_version": 2,
            "lab_id": "sealing-lab",
            "description": "Evidence sealing regression lab.",
            "subjects": {"isolated-control": {"kind": "control"}},
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


def run_case(
    root: Path,
    manifest: Path,
    *,
    run_id: str,
    worker_body: str,
    keep_workspace: bool | None = None,
) -> tuple[int, Path]:
    fake = root / "fake-codex"
    write_fake_codex(fake, worker_body)
    plan = build_plan(
        manifest_path=manifest,
        subject_ids=["isolated-control"],
        case_ids=["protected-repair"],
        mode="canary",
        repeat=1,
        model="model-a",
        reasoning_effort="high",
        codex_bin=str(fake),
        run_id=run_id,
        output_root=None,
        timeout_override=5,
        keep_workspace=keep_workspace,
    )
    plan_path = root / "plan.json"
    atomic_write_json(plan_path, plan)
    code = run_plan(plan_path, live=True, max_invocations=1, resume=False)
    attempt = next((root / "lab" / "runs" / run_id).glob("**/attempt-001"))
    return code, attempt


WRITE_BROKEN = '(workspace / "app.txt").write_text("broken\\n", encoding="utf-8")\n'
WRITE_CHANGED = '(workspace / "app.txt").write_text("changed\\n", encoding="utf-8")\n'


class VerifierIsolationTests(unittest.TestCase):
    def test_verifier_repair_cannot_support_worker_completion(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            manifest = create_lab(
                root,
                workspace_assertions=[
                    {"type": "file_equals", "path": "app.txt", "value": "expected\n"}
                ],
                command_assertions=[
                    {"argv": ["sh", "-c", "printf 'verifier-fixed\\n' > app.txt"]}
                ],
            )
            code, attempt = run_case(
                root, manifest, run_id="repair-run", worker_body=WRITE_BROKEN
            )
            self.assertEqual(code, 1)
            receipt = read_json(attempt / "receipt.json")
            verification = read_json(attempt / "verification.json")

            self.assertEqual(receipt["outcome"], "fail")
            summary = receipt["verification_summary"]
            self.assertFalse(summary["passed"])
            self.assertFalse(summary["worker_completion_supported"])
            self.assertEqual(summary["changed_files"], ["app.txt"])
            self.assertEqual(summary["worker_final"]["changed_files"], ["app.txt"])

            sealed_result = verification["workspace_assertions"][0]
            self.assertEqual(sealed_result["details"]["actual"], "broken\n")
            self.assertFalse(sealed_result["passed"])
            self.assertTrue(verification["command_assertions"][0]["passed"])

            self.assertTrue(verification["verifier"]["fresh_copy_per_command"])
            self.assertTrue(verification["verifier"]["mutated_worker_output"])
            command = verification["verifier"]["commands"][0]
            self.assertEqual(command["derived_changed_files"], ["app.txt"])
            self.assertEqual(command["diff"], "verifier-diff-000.patch")

            diff = (attempt / "diff.patch").read_text(encoding="utf-8")
            self.assertIn("-expected", diff)
            self.assertIn("+broken", diff)
            verifier_diff = (attempt / "verifier-diff-000.patch").read_text(encoding="utf-8")
            self.assertIn("+verifier-fixed", verifier_diff)
            self.assertNotIn("+verifier-fixed", diff)
            self.assertIn("verifier-diff-000.patch", receipt["artifacts"])

            self.assertFalse((attempt / "verifier-workspace").exists())

    def test_each_command_assertion_gets_a_fresh_copy(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            manifest = create_lab(
                root,
                command_assertions=[
                    # Command 0 repairs app.txt inside its own copy.
                    {"argv": ["sh", "-c", "printf 'restored\\n' > app.txt"]},
                    # Command 1 must still observe the worker's original bytes.
                    {"argv": ["sh", "-c", "test \"$(cat app.txt)\" = broken"]},
                ],
            )
            code, attempt = run_case(
                root, manifest, run_id="fresh-copy", worker_body=WRITE_BROKEN
            )
            self.assertEqual(code, 1)
            receipt = read_json(attempt / "receipt.json")
            verification = read_json(attempt / "verification.json")

            self.assertTrue(verification["command_assertions"][0]["passed"])
            self.assertTrue(verification["command_assertions"][1]["passed"])
            self.assertEqual(receipt["outcome"], "inconclusive")
            commands = verification["verifier"]["commands"]
            self.assertTrue(commands[0]["mutated_worker_output"])
            self.assertEqual(commands[0]["derived_changed_files"], ["app.txt"])
            self.assertFalse(commands[1]["mutated_worker_output"])
            self.assertEqual(commands[1]["derived_changed_files"], [])
            self.assertFalse(receipt["verification_summary"]["worker_completion_supported"])


class ReviewMaterialTests(unittest.TestCase):
    def test_declared_material_is_sealed_without_retaining_the_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            manifest = create_lab(
                root,
                result_assertions={"text_contains": ["done"]},
                human_review_requirements=["coverage: inspect the declared material"],
                human_review_material=["app.txt"],
            )
            code, attempt = run_case(
                root, manifest, run_id="material-run", worker_body=WRITE_CHANGED
            )
            self.assertEqual(code, 0)
            receipt = read_json(attempt / "receipt.json")
            verification = read_json(attempt / "verification.json")
            summary = receipt["verification_summary"]

            self.assertEqual(receipt["outcome"], "pass")
            material = summary["review_material"]
            self.assertEqual(material["status"], "sealed")
            self.assertEqual([item["path"] for item in material["files"]], ["app.txt"])
            manifest_path = attempt / MATERIAL_DIR_NAME / "manifest.json"
            self.assertTrue(manifest_path.is_file())
            self.assertEqual(material["manifest_sha256"], sha256_file(manifest_path))
            self.assertEqual(material["manifest"], "review-material/manifest.json")
            self.assertEqual(
                (attempt / MATERIAL_DIR_NAME / "app.txt").read_text(encoding="utf-8"),
                "changed\n",
            )
            self.assertEqual(verification["review_material"]["status"], "sealed")
            self.assertIn("review-material/manifest.json", receipt["artifacts"])
            self.assertIn("review-material/app.txt", receipt["artifacts"])

            self.assertFalse(summary["retention"]["workspace_retained"])
            self.assertEqual(summary["retention"]["reason"], "not-retained")
            self.assertFalse((attempt / "workspace").exists())

    def test_keep_workspace_is_the_only_whole_workspace_retention_switch(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            manifest = create_lab(
                root,
                result_assertions={"text_contains": ["done"]},
                human_review_requirements=["coverage: inspect the declared material"],
                human_review_material=["app.txt"],
            )
            code, attempt = run_case(
                root,
                manifest,
                run_id="keep-run",
                worker_body=WRITE_CHANGED,
                keep_workspace=True,
            )
            self.assertEqual(code, 0)
            receipt = read_json(attempt / "receipt.json")
            self.assertTrue(receipt["verification_summary"]["retention"]["workspace_retained"])
            self.assertEqual(
                receipt["verification_summary"]["retention"]["reason"], "keep-workspace"
            )
            self.assertTrue((attempt / "workspace").is_dir())

    def test_review_requirement_without_material_keeps_only_attempt_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            manifest = create_lab(
                root,
                result_assertions={"text_contains": ["done"]},
                human_review_requirements=["coverage: read the sealed diff"],
            )
            code, attempt = run_case(
                root, manifest, run_id="artifacts-only", worker_body=WRITE_CHANGED
            )
            self.assertEqual(code, 0)
            receipt = read_json(attempt / "receipt.json")
            self.assertEqual(receipt["outcome"], "pass")
            self.assertEqual(
                receipt["verification_summary"]["review_material"]["status"], "not-declared"
            )
            self.assertFalse(receipt["verification_summary"]["retention"]["workspace_retained"])
            self.assertFalse((attempt / "workspace").exists())
            self.assertFalse((attempt / MATERIAL_DIR_NAME).exists())
            for name in ("case.json", "prompt.md", "trace.jsonl", "final-output.md", "diff.patch"):
                self.assertIn(name, receipt["artifacts"])

    def test_invalid_declared_material_fails_closed_without_partial_set(self) -> None:
        cases = {
            "missing": (
                'pass\n',
                ["absent.txt"],
            ),
            "directory": (
                '(workspace / "material-dir").mkdir()\n',
                ["material-dir"],
            ),
            "symlink": (
                '(workspace / "link.txt").symlink_to(workspace / "app.txt")\n',
                ["link.txt"],
            ),
            "symlinked-ancestor": (
                '(workspace / "real").mkdir()\n'
                '(workspace / "real" / "note.txt").write_text("hi\\n", encoding="utf-8")\n'
                '(workspace / "linked").symlink_to(workspace / "real", target_is_directory=True)\n',
                ["linked/note.txt"],
            ),
            "over-limit": (
                f'(workspace / "big.txt").write_text("x" * {MAX_REVIEW_MATERIAL_FILE_BYTES + 1}, encoding="utf-8")\n',
                ["big.txt"],
            ),
        }
        for name, (worker_body, material) in cases.items():
            with self.subTest(variant=name), tempfile.TemporaryDirectory() as raw:
                root = Path(raw)
                manifest = create_lab(
                    root,
                    result_assertions={"text_contains": ["done"]},
                    human_review_requirements=["coverage: inspect the declared material"],
                    human_review_material=material,
                )
                with self.assertRaises(EvidenceError):
                    run_case(root, manifest, run_id="bad-material", worker_body=worker_body)
                attempt = next(
                    (root / "lab" / "runs" / "bad-material").glob("**/attempt-001")
                )
                self.assertFalse((attempt / "receipt.json").exists())
                self.assertFalse((attempt / MATERIAL_DIR_NAME).exists())
                self.assertFalse(list(attempt.glob(".review-material-staging-*")))
                self.assertFalse((attempt / "workspace").exists())
                metadata = read_json(attempt / "metadata.json")
                self.assertEqual(metadata["state"], "evidence-failed")
                self.assertEqual(metadata["outcome"], "error")
                self.assertTrue(metadata["error"])
                self.assertLessEqual(len(metadata["error"]), 500)
                summary = read_json(
                    root / "lab" / "runs" / "bad-material" / "summary.json"
                )
                # The worker process was already quiescent; this is not a
                # process-termination failure.
                self.assertEqual(summary["state"], "evidence-failed")
                self.assertNotEqual(summary["state"], "termination-failed")
                self.assertTrue(summary["attempts"] == [])

    def test_run_state_separates_evidence_failure_from_termination_failure(self) -> None:
        from unittest import mock

        for error_type, expected_state in (
            (EvidenceError, "evidence-failed"),
            (ExecutionError, "termination-failed"),
        ):
            with self.subTest(error=error_type.__name__), tempfile.TemporaryDirectory() as raw:
                root = Path(raw)
                manifest = create_lab(
                    root,
                    result_assertions={"text_contains": ["done"]},
                    human_review_requirements=["coverage: inspect the sealed diff"],
                )
                fake = root / "fake-codex"
                write_fake_codex(fake, WRITE_CHANGED)
                plan = build_plan(
                    manifest_path=manifest,
                    subject_ids=["isolated-control"],
                    case_ids=["protected-repair"],
                    mode="canary",
                    repeat=1,
                    model="model-a",
                    reasoning_effort="high",
                    codex_bin=str(fake),
                    run_id="state-run",
                    output_root=None,
                    timeout_override=5,
                    keep_workspace=False,
                )
                plan_path = root / "plan.json"
                atomic_write_json(plan_path, plan)
                with mock.patch(
                    "fieldlab.runner.run_attempt",
                    side_effect=error_type("synthetic failure"),
                ):
                    with self.assertRaises(error_type):
                        run_plan(plan_path, live=True, max_invocations=1, resume=False)
                summary = read_json(root / "lab" / "runs" / "state-run" / "summary.json")
                self.assertEqual(summary["state"], expected_state)

    def test_case_contract_rejects_bad_material_declarations(self) -> None:
        from fieldlab.contracts import load_case
        from fieldlab.errors import ConfigError

        variants = {
            "glob": ["*.txt"],
            "absolute": ["/etc/passwd"],
            "escape": ["../secret.txt"],
            "directory": ["sub/"],
            "duplicate": ["app.txt", "app.txt"],
            "without-requirements": ["app.txt"],
            "not-a-list": {"app.txt": True},
        }
        for name, material in variants.items():
            with self.subTest(variant=name), tempfile.TemporaryDirectory() as raw:
                root = Path(raw)
                manifest = create_lab(
                    root,
                    result_assertions={"text_contains": ["done"]},
                    human_review_requirements=None
                    if name == "without-requirements"
                    else ["coverage: inspect"],
                    human_review_material=None,
                )
                case_dir = root / "lab" / "cases" / "protected-repair"
                case = read_json(case_dir / "case.json")
                case["human_review_material"] = material
                if name == "without-requirements":
                    case.pop("human_review_requirements", None)
                write_json(case_dir / "case.json", case)
                with self.assertRaises(ConfigError):
                    load_case(case_dir)
                del manifest


class DiffIndexTests(unittest.TestCase):
    def test_capture_diff_does_not_mutate_the_real_index(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            case_dir = root / "case"
            fixture = case_dir / "fixture"
            fixture.mkdir(parents=True)
            (fixture / "app.txt").write_text("baseline\n", encoding="utf-8")
            workspace = root / "workspace"
            prepare_workspace(
                case_dir=case_dir,
                subject={"kind": "control"},
                lab_root=root,
                workspace=workspace,
            )
            (workspace / "app.txt").write_text("worker-change\n", encoding="utf-8")
            (workspace / "untracked.txt").write_text("new file\n", encoding="utf-8")

            def git(*args: str) -> str:
                return subprocess.run(
                    ["git", "-C", str(workspace), *args],
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                ).stdout

            index_path = workspace / ".git" / "index"
            before_index = index_path.read_bytes()
            before_cached = git("diff", "--cached", "--binary", "HEAD", "--")

            diff = capture_diff(workspace)

            self.assertIn("diff --git a/app.txt b/app.txt", diff)
            self.assertIn("diff --git a/untracked.txt b/untracked.txt", diff)
            self.assertEqual(index_path.read_bytes(), before_index)
            self.assertEqual(git("diff", "--cached", "--binary", "HEAD", "--"), before_cached)
            self.assertEqual(before_cached, "")


if __name__ == "__main__":
    unittest.main()

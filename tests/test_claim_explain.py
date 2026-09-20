from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from fieldlab.cli import main
from fieldlab.io import sha256_bytes, sha256_file
from fieldlab.receipts import human_review_record


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def create_lab(root: Path) -> Path:
    lab_root = root / "lab"
    (lab_root / "cases").mkdir(parents=True)
    manifest = lab_root / "fieldlab.json"
    write_json(
        manifest,
        {
            "schema_version": 2,
            "lab_id": "explain-lab",
            "description": "Read-only evidence explanation lab.",
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
    write_json(
        lab_root / "claims" / "claim-a.json",
        {
            "schema_version": 2,
            "claim_id": "claim-a",
            "subject_id": "isolated-control",
            "statement": "The worker writes the protected bytes.",
            "observable_delta": "The sealed diff shows the written bytes.",
            "preserved_behaviors": [],
            "sufficient_evidence": ["One sealed attempt receipt."],
            # A stale hand-maintained status must not become evidence.
            "status": "verified",
        },
    )
    return manifest


def write_attempt(
    root: Path,
    *,
    run_id: str,
    requirement: str,
    with_missing_artifact: bool = True,
    with_worker_final: bool = True,
    with_review_material: bool = False,
) -> Path:
    lab_root = root / "lab"
    attempt = (
        lab_root
        / "runs"
        / run_id
        / "isolated-control"
        / "case-a"
        / "repeat-001"
        / "attempt-001"
    )
    attempt.mkdir(parents=True)
    diff = attempt / "diff.patch"
    diff.write_text("--- a/app.txt\n+++ b/app.txt\n", encoding="utf-8")
    artifacts = {
        "diff.patch": {"sha256": sha256_file(diff), "bytes": diff.stat().st_size},
    }
    if with_missing_artifact:
        artifacts["verification.json"] = {"sha256": "c" * 64, "bytes": 1}

    summary: dict = {
        "passed": True,
        "worker_completion_supported": True,
        "changed_files": ["app.txt"],
        "verifier": {
            "command_assertions": 0,
            "isolated_copy": False,
            "fresh_copy_per_command": True,
            "mutated_worker_output": False,
            "derived_changed_files": [],
        },
        "retention": {"workspace_retained": False, "reason": "not-retained"},
        "human_review": {
            "required": True,
            "requirements": [requirement],
            "status": "pending",
        },
    }
    if with_worker_final:
        summary["worker_final"] = {
            "changed_files": ["app.txt"],
            "tree_sha256": "d" * 64,
            "diff_sha256": sha256_file(diff),
        }
    if with_review_material:
        material_dir = attempt / "review-material"
        material_dir.mkdir()
        (material_dir / "app.txt").write_text("changed\n", encoding="utf-8")
        material_manifest = material_dir / "manifest.json"
        write_json(
            material_manifest,
            {
                "schema_version": 2,
                "status": "sealed",
                "files": [
                    {
                        "path": "app.txt",
                        "sha256": sha256_file(material_dir / "app.txt"),
                        "bytes": (material_dir / "app.txt").stat().st_size,
                    }
                ],
            },
        )
        summary["review_material"] = {
            "status": "sealed",
            "directory": "review-material",
            "manifest": "review-material/manifest.json",
            "manifest_sha256": sha256_file(material_manifest),
            "files": [
                {
                    "path": "app.txt",
                    "sha256": sha256_file(material_dir / "app.txt"),
                    "bytes": (material_dir / "app.txt").stat().st_size,
                }
            ],
        }
        artifacts["review-material/manifest.json"] = {
            "sha256": sha256_file(material_manifest),
            "bytes": material_manifest.stat().st_size,
        }
        artifacts["review-material/app.txt"] = {
            "sha256": sha256_file(material_dir / "app.txt"),
            "bytes": (material_dir / "app.txt").stat().st_size,
        }
    write_json(
        lab_root / "runs" / run_id / "summary.json",
        {
            "schema_version": 2,
            "state": "completed",
            "run_id": run_id,
            "identity": {
                "identity_sha256": "a" * 64,
                "subjects": {
                    "isolated-control": {
                        "subject_scope": "isolated-control",
                        "source": {"type": "control"},
                        "mount": None,
                    }
                },
            },
        },
    )
    write_json(
        attempt / "receipt.json",
        {
            "schema_version": 2,
            "receipt_type": "attempt",
            "created_at": "2026-09-18T00:00:00+00:00",
            "run_id": run_id,
            "attempt_id": "attempt-001",
            "lab_id": "explain-lab",
            "case_id": "case-a",
            "claim_ids": ["claim-a"],
            "subject_id": "isolated-control",
            "evidence": {
                "origin": "synthetic",
                "subject_scope": "isolated-control",
                "comparison": "single",
                "verification_methods": ["deterministic"],
                "independence": "implementer-run",
                "comparison_capable": True,
                "exclusive_subject_claimed": False,
            },
            "identity_sha256": "a" * 64,
            "inputs": {"case_sha256": "b" * 64},
            "outcome": "pass",
            "verification_summary": summary,
            "artifacts": artifacts,
        },
    )
    return attempt / "receipt.json"


def explain(manifest: Path, claim: str, *, as_json: bool = False) -> tuple[int, str]:
    arguments = ["explain", str(manifest), "--claim", claim]
    if as_json:
        arguments.append("--json")
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        code = main(arguments)
    return code, buffer.getvalue()


def write_review(
    root: Path,
    receipt_path: Path,
    *,
    review_id: str,
    judgment: str,
    requirement: str,
    requirement_status: str,
) -> None:
    review = human_review_record(
        review_id=review_id,
        receipt_path=receipt_path,
        independence="separate-agent",
        judgment=judgment,
        rationale="Recorded for the explanation regression.",
        requirement_outcomes={requirement: requirement_status},
    )
    write_json(root / "lab" / "reviews" / f"{review_id}.json", review)


def lab_files(root: Path) -> set[str]:
    return {path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()}


class ClaimExplainTests(unittest.TestCase):
    def test_old_receipt_does_not_acquire_delivery_or_selection_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            manifest = create_lab(root)
            write_attempt(root, run_id="legacy-delivery", requirement="semantic check",
                          with_missing_artifact=False)
            _, output = explain(manifest, "claim-a", as_json=True)
            entry = json.loads(output)["receipts"][0]
            self.assertEqual(entry["subject_delivery"], {"status": "unknown"})
            self.assertEqual(entry["host_selection"], {"status": "unknown"})
            self.assertEqual(entry["content_application"]["status"], "requires-semantic-review")
            _, text = explain(manifest, "claim-a", as_json=False)
            self.assertIn("command-path mentions", text)
            self.assertIn("subject delivery: {'status': 'unknown'}", text)

    def test_explain_derives_from_receipts_and_not_declared_status(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            manifest = create_lab(root)
            before = lab_files(root)
            code, output = explain(manifest, "claim-a", as_json=True)
            self.assertEqual(code, 0)
            self.assertEqual(lab_files(root), before)
            view = json.loads(output)
            self.assertEqual(view["declared_status"], "verified")
            self.assertTrue(view["declared_status_is_not_evidence"])
            self.assertEqual(view["derived_verdict"], "inconclusive")
            self.assertEqual(view["counts"]["receipts"], 0)
            self.assertEqual(view["target_agent_invocations"], 0)
            self.assertIn("No receipt binds", view["next_gap"])

    def test_explain_reports_pending_requirement_and_drift(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            manifest = create_lab(root)
            write_attempt(
                root,
                run_id="run-a",
                requirement="coverage: inspect the sealed diff",
                with_review_material=True,
            )
            code, output = explain(manifest, "claim-a")
            self.assertEqual(code, 0)
            self.assertIn("Pending review requirement", output)
            self.assertIn("coverage: inspect the sealed diff", output)
            self.assertIn("missing or digest-drifted", output.lower())
            self.assertIn("boundary: sealed-before-verifier", output)
            self.assertIn("review material:", output)
            self.assertIn("verifier:", output)
            self.assertIn("retention:", output)
            self.assertIn("Target-agent invocations: 0", output)

    def test_explain_becomes_supported_only_for_sealed_receipts(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            manifest = create_lab(root)
            requirement = "coverage: inspect the sealed diff"
            receipt_path = write_attempt(
                root,
                run_id="run-a",
                requirement=requirement,
                with_missing_artifact=False,
            )
            write_review(
                root,
                receipt_path,
                review_id="claim-a-review",
                judgment="supported",
                requirement=requirement,
                requirement_status="supported",
            )
            code, output = explain(manifest, "claim-a", as_json=True)
            self.assertEqual(code, 0)
            view = json.loads(output)
            self.assertEqual(view["derived_verdict"], "supported")
            self.assertEqual(view["counts"]["pending_requirements"], 0)
            self.assertEqual(view["counts"]["supported"], 1)
            self.assertEqual(view["receipts"][0]["reviews"][0]["judgment"], "supported")
            self.assertEqual(view["receipts"][0]["boundary"], "sealed-before-verifier")
            self.assertIn("matched isolated-control comparison", view["next_gap"])

    def test_duplicate_receipt_copies_are_one_piece_of_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            manifest = create_lab(root)
            requirement = "coverage: inspect the sealed diff"
            receipt_path = write_attempt(
                root,
                run_id="run-a",
                requirement=requirement,
                with_missing_artifact=False,
            )
            promoted = root / "lab" / "receipts" / "promoted-attempt.json"
            promoted.parent.mkdir(parents=True, exist_ok=True)
            promoted.write_bytes(receipt_path.read_bytes())

            code, output = explain(manifest, "claim-a", as_json=True)
            self.assertEqual(code, 0)
            view = json.loads(output)
            self.assertEqual(view["counts"]["receipts"], 1)
            entry = view["receipts"][0]
            self.assertEqual(len(entry["locations"]), 2)
            self.assertEqual(entry["receipt_sha256"], sha256_file(receipt_path))

    def test_conflicting_bound_reviews_make_the_receipt_and_claim_mixed(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            manifest = create_lab(root)
            requirement = "coverage: inspect the sealed diff"
            receipt_path = write_attempt(
                root,
                run_id="run-a",
                requirement=requirement,
                with_missing_artifact=False,
            )
            write_review(
                root,
                receipt_path,
                review_id="review-support",
                judgment="supported",
                requirement=requirement,
                requirement_status="supported",
            )
            write_review(
                root,
                receipt_path,
                review_id="review-reject",
                judgment="not-supported",
                requirement=requirement,
                requirement_status="not-supported",
            )
            code, output = explain(manifest, "claim-a", as_json=True)
            self.assertEqual(code, 0)
            view = json.loads(output)
            self.assertEqual(view["derived_verdict"], "mixed")
            self.assertEqual(view["counts"]["mixed"], 1)
            self.assertEqual(view["counts"]["supported"], 0)
            self.assertEqual(view["receipts"][0]["assessment"], "mixed")
            self.assertTrue(view["receipts"][0]["conflicting"])
            self.assertIn("Conflicting bound reviews", view["next_gap"])
            self.assertEqual(
                [review["independence"] for review in view["receipts"][0]["reviews"]],
                ["separate-agent", "separate-agent"],
            )

    def test_legacy_attempt_receipt_is_labeled_ambiguous(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            manifest = create_lab(root)
            requirement = "coverage: inspect the sealed diff"
            receipt_path = write_attempt(
                root,
                run_id="run-a",
                requirement=requirement,
                with_missing_artifact=False,
                with_worker_final=False,
            )
            write_review(
                root,
                receipt_path,
                review_id="legacy-review",
                judgment="supported",
                requirement=requirement,
                requirement_status="supported",
            )
            code, output = explain(manifest, "claim-a")
            self.assertEqual(code, 0)
            self.assertIn("legacy-ambiguous", output)
            self.assertNotIn("boundary: sealed-before-verifier", output)
            code, output = explain(manifest, "claim-a", as_json=True)
            view = json.loads(output)
            self.assertEqual(view["receipts"][0]["boundary"], "legacy-ambiguous")
            self.assertEqual(view["counts"]["legacy_ambiguous_receipts"], 1)
            self.assertEqual(view["counts"]["supported"], 1)
            # A legacy receipt stays readable but cannot be presented as sealed.
            self.assertEqual(view["derived_verdict"], "inconclusive")
            self.assertIn("legacy receipts", view["next_gap"])

    def test_digest_mismatched_review_does_not_contribute(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            manifest = create_lab(root)
            requirement = "coverage: inspect the sealed diff"
            receipt_path = write_attempt(
                root,
                run_id="run-a",
                requirement=requirement,
                with_missing_artifact=False,
            )
            write_review(
                root,
                receipt_path,
                review_id="drifted-review",
                judgment="supported",
                requirement=requirement,
                requirement_status="supported",
            )
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            receipt["verification_summary"]["changed_files"] = ["app.txt", "other.txt"]
            write_json(receipt_path, receipt)

            code, output = explain(manifest, "claim-a", as_json=True)
            self.assertEqual(code, 0)
            view = json.loads(output)
            self.assertEqual(view["derived_verdict"], "inconclusive")
            self.assertEqual(len(view["stale_reviews"]), 1)
            self.assertEqual(view["stale_reviews"][0]["review_id"], "drifted-review")
            self.assertEqual(view["receipts"][0]["reviews"], [])
            self.assertEqual(view["counts"]["pending_requirements"], 1)

    def test_human_review_binds_the_exact_validated_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            receipt_path = root / "receipt.json"
            payload = (
                json.dumps(
                    {
                        "schema_version": 2,
                        "receipt_type": "attempt",
                        "outcome": "pass",
                        "verification_summary": {
                            "human_review": {"required": False, "requirements": []}
                        },
                    }
                )
                + "\n"
            )
            receipt_path.write_text(payload, encoding="utf-8")
            review = human_review_record(
                review_id="exact-bytes",
                receipt_path=receipt_path,
                independence="separate-agent",
                judgment="supported",
                rationale="Binds the bytes that were validated.",
            )
            self.assertEqual(
                review["receipt"]["sha256"],
                sha256_bytes(payload.encode("utf-8")),
            )
            self.assertEqual(review["receipt"]["sha256"], sha256_file(receipt_path))


if __name__ == "__main__":
    unittest.main()

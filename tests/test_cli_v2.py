from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from fieldlab.cli import main
from fieldlab.io import read_json, sha256_file


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


class V2CliTests(unittest.TestCase):
    def test_init_validate_and_claim_only_observe(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            lab_root = root / "source-study"
            self.assertEqual(main(["init", str(lab_root)]), 0)
            manifest = lab_root / "fieldlab.json"
            self.assertTrue(manifest.is_file())
            self.assertEqual(main(["validate", str(manifest)]), 0)
            claim = {
                "schema_version": 2,
                "claim_id": "ordinary-work-supports-claim",
                "subject_id": "isolated-control",
                "statement": "Ordinary work already demonstrates the bounded behavior.",
                "observable_delta": "The evidence names the claim ceiling.",
                "preserved_behaviors": [],
                "sufficient_evidence": ["A source-bounded review artifact."],
                "status": "observed",
            }
            write_json(lab_root / "claims" / "ordinary-work-supports-claim.json", claim)
            artifact = root / "review.md"
            artifact.write_text("The claim ceiling is narrow.\n", encoding="utf-8")

            self.assertEqual(
                main(
                    [
                        "observe",
                        str(manifest),
                        "--subject",
                        "isolated-control",
                        "--claim",
                        "ordinary-work-supports-claim",
                        "--outcome",
                        "supported",
                        "--artifact",
                        f"review={artifact}",
                        "--note",
                        "Observed during ordinary source review.",
                    ]
                ),
                0,
            )
            receipts = sorted((lab_root / "receipts").glob("observed-*.json"))
            self.assertEqual(len(receipts), 1)
            receipt = read_json(receipts[0])
            self.assertEqual(receipt["claim_ids"], ["ordinary-work-supports-claim"])
            self.assertNotIn("case_id", receipt)
            self.assertEqual(receipt["claim_assessment"], "supported")

    def test_migrate_v1_preserves_source_and_writes_snapshot_manifest_and_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source = root / "v1"
            case_dir = source / "cases" / "tiny"
            fixture = case_dir / "fixture"
            expected = case_dir / "expected"
            subject = source / "subject" / "scope"
            fixture.mkdir(parents=True)
            expected.mkdir()
            subject.mkdir(parents=True)
            (fixture / "value.txt").write_text("old\n", encoding="utf-8")
            (expected / "value.txt").write_text("new\n", encoding="utf-8")
            (subject / "SKILL.md").write_text("scope\n", encoding="utf-8")
            (case_dir / "prompt.md").write_text("Change the value.\n", encoding="utf-8")
            write_json(
                case_dir / "case.json",
                {
                    "schema_version": 1,
                    "case_id": "tiny",
                    "description": "Tiny migration case.",
                    "prompt_file": "prompt.md",
                    "sandbox": "workspace-write",
                    "timeout_seconds": 30,
                    "assertions": [{"type": "file_equals", "path": "value.txt", "value": "new\n"}],
                },
            )
            pack = source / "fieldlab-pack.json"
            write_json(
                pack,
                {
                    "schema_version": 1,
                    "pack_id": "legacy-pack",
                    "description": "Legacy pack.",
                    "cases_root": "cases",
                    "subjects": {
                        "legacy-subject": {
                            "label": "Legacy subject",
                            "attribution": "repo_scoped",
                            "overlays": [
                                {"source": "subject", "target": ".agents/skills"}
                            ],
                        }
                    },
                    "defaults": {
                        "adapter": "codex-exec",
                        "approval_policy": "never",
                        "network_access": False,
                        "output_root": ".fieldlab",
                        "keep_workspace": False,
                    },
                },
            )
            before = sha256_file(pack)
            output = root / "v2" / "fieldlab.json"
            self.assertEqual(
                main(["migrate-v1", str(pack), "--output", str(output)]),
                0,
            )
            self.assertEqual(sha256_file(pack), before)
            migrated = read_json(output)
            migrated_subject = migrated["subjects"]["legacy-subject"]
            self.assertEqual(migrated_subject["source"]["type"], "snapshot")
            self.assertEqual(migrated_subject["mount"], ".")
            self.assertEqual(
                read_json(root / "v2" / "cases" / "tiny" / "case.json")["schema_version"],
                2,
            )
            self.assertTrue((root / "v2" / "subjects" / "legacy-subject" / ".agents" / "skills" / "scope" / "SKILL.md").is_file())
            self.assertEqual(len(list((root / "v2" / "receipts").glob("migration-v1-*.json"))), 1)
            self.assertTrue(pack.is_file())

    def test_promote_copies_records_but_not_runtime_plans_or_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            lab_root = root / "lab"
            self.assertEqual(main(["init", str(lab_root)]), 0)
            write_json(
                lab_root / "claims" / "promoted-claim.json",
                {
                    "schema_version": 2,
                    "claim_id": "promoted-claim",
                    "subject_id": "isolated-control",
                    "statement": "The promoted record stays bounded.",
                    "observable_delta": "Only selected evidence records move.",
                    "preserved_behaviors": [],
                    "sufficient_evidence": ["One collision-free promotion receipt."],
                    "status": "observed",
                },
            )
            (lab_root / "runs" / "private.txt").write_text("run\n", encoding="utf-8")
            (lab_root / "plans" / "plan.json").write_text("{}\n", encoding="utf-8")
            destination = root / "subject-evidence"
            self.assertEqual(
                main(["promote", "--from", str(lab_root), "--to", str(destination)]),
                0,
            )
            self.assertTrue((destination / "claims" / "promoted-claim.json").is_file())
            self.assertFalse((destination / "fieldlab.json").exists())
            self.assertFalse((destination / "runs").exists())
            self.assertFalse((destination / "plans").exists())


if __name__ == "__main__":
    unittest.main()

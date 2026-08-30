from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from fieldlab.contracts import load_case, load_cases, load_lab
from fieldlab.errors import ConfigError


ROOT = Path(__file__).resolve().parents[1]


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def minimal_manifest() -> dict[str, object]:
    return {
        "schema_version": 2,
        "lab_id": "contract-lab",
        "description": "A contract test lab.",
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


class V2ContractTests(unittest.TestCase):
    def test_empty_external_lab_is_valid_before_any_case_exists(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "cases").mkdir()
            manifest_path = root / "fieldlab.json"
            write_json(manifest_path, minimal_manifest())

            lab, lab_root, cases_root = load_lab(manifest_path)

            self.assertEqual(lab["lab_id"], "contract-lab")
            self.assertEqual(lab["schema_version"], 2)
            self.assertEqual(lab_root, root.resolve())
            self.assertEqual(load_cases(cases_root, allow_empty=True), {})

    def test_v1_manifest_is_not_an_active_runtime_surface(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            manifest = Path(raw) / "fieldlab-pack.json"
            write_json(manifest, {"schema_version": 1})
            with self.assertRaisesRegex(ConfigError, "migrate legacy packs"):
                load_lab(manifest)

    def test_v2_output_only_case_needs_no_fixture_or_expected_tree(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            case_dir = Path(raw) / "output-only"
            case_dir.mkdir()
            (case_dir / "prompt.md").write_text("Answer from the sources.\n", encoding="utf-8")
            write_json(
                case_dir / "case.json",
                {
                    "schema_version": 2,
                    "case_id": "output-only",
                    "description": "Verify only the final response.",
                    "prompt_file": "prompt.md",
                    "activation": "implicit",
                    "sandbox": "read-only",
                    "timeout_seconds": 30,
                    "result_assertions": {
                        "text_contains": ["binding authority"],
                        "text_not_contains": ["invented citation"],
                    },
                },
            )

            case = load_case(case_dir)

            self.assertEqual(case["activation"], "implicit")
            self.assertFalse((case_dir / "fixture").exists())
            self.assertEqual(case["workspace_assertions"], [])

    def test_v2_rejects_reserved_hermetic_scope(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "cases").mkdir()
            subject = root / "subject"
            subject.mkdir()
            manifest = minimal_manifest()
            manifest["subjects"] = {
                "subject": {
                    "kind": "agent-skill",
                    "subject_scope": "hermetic",
                    "source": {"type": "local-path", "path": "subject"},
                }
            }
            manifest_path = root / "fieldlab.json"
            write_json(manifest_path, manifest)
            with self.assertRaisesRegex(ConfigError, "hermetic"):
                load_lab(manifest_path)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from fieldlab.contracts import load_lab
from fieldlab.errors import ConfigError
from fieldlab.subjects import materialize_subject, subject_identity


def git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return completed.stdout.strip()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def manifest(subjects: dict[str, object]) -> dict[str, object]:
    return {
        "schema_version": 2,
        "lab_id": "subject-lab",
        "description": "Subject materialization test.",
        "subjects": subjects,
        "cases_root": "cases",
        "defaults": {
            "adapter": "codex-exec",
            "approval_policy": "never",
            "network_access": False,
            "output_root": "runs",
            "keep_workspace": False,
        },
    }


class SubjectMaterializationTests(unittest.TestCase):
    def test_external_local_path_is_read_only_and_pinned(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            repo = root / "subject-repo"
            repo.mkdir()
            git(repo, "init", "-q")
            git(repo, "config", "user.name", "Field Lab Test")
            git(repo, "config", "user.email", "fieldlab@example.invalid")
            skill = repo / "skills" / "scope"
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_text("version one\n", encoding="utf-8")
            git(repo, "add", "--all")
            git(repo, "commit", "--no-gpg-sign", "-q", "-m", "one")

            lab_root = root / "lab"
            (lab_root / "cases").mkdir(parents=True)
            manifest_path = lab_root / "fieldlab.json"
            write_json(
                manifest_path,
                manifest(
                    {
                        "scope": {
                            "kind": "agent-skill",
                            "source": {
                                "type": "local-path",
                                "path": "../subject-repo/skills/scope",
                            },
                        }
                    }
                ),
            )
            lab, resolved_root, _ = load_lab(manifest_path)
            before_head = git(repo, "rev-parse", "HEAD")
            before_status = git(repo, "status", "--porcelain=v1", "--untracked-files=all")

            identity = subject_identity("scope", lab["subjects"]["scope"], resolved_root)
            workspace = root / "workspace"
            workspace.mkdir()
            materialize_subject(
                subject_id="scope",
                subject=lab["subjects"]["scope"],
                lab_root=resolved_root,
                workspace=workspace,
            )

            self.assertEqual(identity["subject_scope"], "workspace-scoped")
            self.assertEqual(identity["source"]["type"], "local-path")
            self.assertEqual(
                (workspace / ".agents" / "skills" / "scope" / "SKILL.md").read_text(),
                "version one\n",
            )
            self.assertEqual(git(repo, "rev-parse", "HEAD"), before_head)
            self.assertEqual(
                git(repo, "status", "--porcelain=v1", "--untracked-files=all"),
                before_status,
            )

    def test_local_git_ref_materializes_pinned_commit_not_working_tree(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            repo = root / "repo"
            repo.mkdir()
            git(repo, "init", "-q")
            git(repo, "config", "user.name", "Field Lab Test")
            git(repo, "config", "user.email", "fieldlab@example.invalid")
            skill = repo / "skill"
            skill.mkdir()
            (skill / "SKILL.md").write_text("old\n", encoding="utf-8")
            git(repo, "add", "--all")
            git(repo, "commit", "--no-gpg-sign", "-q", "-m", "old")
            old = git(repo, "rev-parse", "HEAD")
            (skill / "SKILL.md").write_text("new\n", encoding="utf-8")
            git(repo, "commit", "--no-gpg-sign", "-q", "-am", "new")

            lab_root = root / "lab"
            (lab_root / "cases").mkdir(parents=True)
            manifest_path = lab_root / "fieldlab.json"
            write_json(
                manifest_path,
                manifest(
                    {
                        "pinned": {
                            "kind": "agent-skill",
                            "source": {
                                "type": "local-git-ref",
                                "repo": "../repo",
                                "ref": old,
                                "subpath": "skill",
                            },
                        }
                    }
                ),
            )
            lab, resolved_root, _ = load_lab(manifest_path)
            workspace = root / "workspace"
            workspace.mkdir()
            materialize_subject(
                subject_id="pinned",
                subject=lab["subjects"]["pinned"],
                lab_root=resolved_root,
                workspace=workspace,
            )
            self.assertEqual(
                (workspace / ".agents" / "skills" / "pinned" / "SKILL.md").read_text(),
                "old\n",
            )

    def test_control_has_no_overlay_and_snapshot_must_stay_in_lab(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            workspace = root / "workspace"
            workspace.mkdir()
            control = {"kind": "control"}
            identity = subject_identity("control", control, root)
            materialize_subject(
                subject_id="control",
                subject=control,
                lab_root=root,
                workspace=workspace,
            )
            self.assertEqual(identity["subject_scope"], "isolated-control")
            self.assertFalse((workspace / ".agents").exists())
            with self.assertRaisesRegex(ConfigError, "snapshot"):
                subject_identity(
                    "escape",
                    {
                        "kind": "agent-skill",
                        "source": {"type": "snapshot", "path": "../outside"},
                    },
                    root,
                )


if __name__ == "__main__":
    unittest.main()

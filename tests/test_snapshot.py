from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from fieldlab.snapshot import snapshot_git_tree


def git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return completed.stdout.strip()


class GitSnapshotTests(unittest.TestCase):
    def test_snapshot_materializes_exact_old_subject_tree_without_model(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            repo = root / "repo"
            repo.mkdir()
            git(repo, "init", "-q")
            git(repo, "config", "user.name", "Field Lab Test")
            git(repo, "config", "user.email", "fieldlab@example.invalid")
            skill = repo / "skills" / "scope"
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_text("version one\n", encoding="utf-8")
            git(repo, "add", "--all")
            git(repo, "commit", "--no-gpg-sign", "-q", "-m", "one")
            first = git(repo, "rev-parse", "HEAD")
            (skill / "SKILL.md").write_text("version two\n", encoding="utf-8")
            git(repo, "commit", "--no-gpg-sign", "-q", "-am", "two")

            output = root / "baseline-skills"
            metadata = snapshot_git_tree(
                repo=repo,
                ref=first,
                source_path="skills",
                output=output,
                replace=False,
            )
            self.assertEqual((output / "scope" / "SKILL.md").read_text(), "version one\n")
            self.assertEqual(metadata["resolved_commit"], first)
            snapshot_metadata = json.loads(
                (root / "baseline-skills.snapshot.json").read_text(encoding="utf-8")
            )
            self.assertEqual(snapshot_metadata["resolved_commit"], first)


if __name__ == "__main__":
    unittest.main()

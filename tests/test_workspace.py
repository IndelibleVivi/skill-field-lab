from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from fieldlab.errors import ConfigError
from fieldlab.workspace import prepare_workspace


class WorkspaceBoundaryTests(unittest.TestCase):
    @unittest.skipUnless(hasattr(os, "symlink"), "symlinks unavailable")
    def test_fixture_symlink_cannot_escape_disposable_tree(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            case_dir = root / "case"
            fixture = case_dir / "fixture"
            fixture.mkdir(parents=True)
            secret = root / "secret.txt"
            secret.write_text("secret\n", encoding="utf-8")
            (fixture / "escape.txt").symlink_to(Path("..") / ".." / "secret.txt")
            with self.assertRaisesRegex(ConfigError, "symlink escapes"):
                prepare_workspace(
                    case_dir=case_dir,
                    subject={"kind": "control"},
                    lab_root=root,
                    workspace=root / "workspace",
                )

    @unittest.skipUnless(hasattr(os, "symlink"), "symlinks unavailable")
    def test_internal_relative_symlink_is_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            case_dir = root / "case"
            fixture = case_dir / "fixture"
            fixture.mkdir(parents=True)
            (fixture / "target.txt").write_text("value\n", encoding="utf-8")
            (fixture / "link.txt").symlink_to("target.txt")
            workspace = root / "workspace"
            prepare_workspace(
                case_dir=case_dir,
                subject={"kind": "control"},
                lab_root=root,
                workspace=workspace,
            )
            self.assertTrue((workspace / "link.txt").is_symlink())
            self.assertEqual((workspace / "link.txt").read_text(), "value\n")


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import json
import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
INSTALLER_SPEC = importlib.util.spec_from_file_location(
    "fieldlab_installer_test_module",
    ROOT / "scripts" / "install.py",
)
assert INSTALLER_SPEC is not None and INSTALLER_SPEC.loader is not None
INSTALLER = importlib.util.module_from_spec(INSTALLER_SPEC)
INSTALLER_SPEC.loader.exec_module(INSTALLER)


def write_fake_codex(path: Path) -> None:
    path.write_text("#!/bin/sh\necho codex-cli-doctor-fake\n", encoding="utf-8")
    path.chmod(0o755)


class UnifiedInstallerTests(unittest.TestCase):
    def test_cli_only_leaves_controller_discovery_path_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            skills = root / "skills"
            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "install.py"),
                    "--app-dir",
                    str(root / "app"),
                    "--bin-dir",
                    str(root / "bin"),
                    "--skills-dir",
                    str(skills),
                    "--backup-dir",
                    str(root / "backups"),
                    "--cli-only",
                ],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertFalse(skills.exists())
            self.assertTrue((root / "app" / "skills" / "pattern-intake" / "SKILL.md").is_file())

    def test_install_doctor_and_transactional_replace_with_backup(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            app = root / "app"
            bin_dir = root / "bin"
            skills = root / "skills"
            backups = root / "backups"
            command = [
                sys.executable,
                str(ROOT / "scripts" / "install.py"),
                "--app-dir",
                str(app),
                "--bin-dir",
                str(bin_dir),
                "--skills-dir",
                str(skills),
                "--backup-dir",
                str(backups),
            ]
            subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            self.assertTrue((app / ".skill-field-lab-install").is_file())
            self.assertTrue((app / "installation-receipt.json").is_file())
            self.assertTrue((skills / "pattern-intake" / "SKILL.md").is_file())
            self.assertTrue((skills / "skill-eval" / "SKILL.md").is_file())
            help_result = subprocess.run(
                [str(bin_dir / "fieldlab"), "--help"],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertIn("Study before you install", help_result.stdout)
            fake_codex = root / "codex"
            write_fake_codex(fake_codex)
            doctor = subprocess.run(
                [
                    str(bin_dir / "fieldlab"),
                    "doctor",
                    "--skills-dir",
                    str(skills),
                    "--codex-bin",
                    str(fake_codex),
                    "--json",
                ],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            report = json.loads(doctor.stdout)
            self.assertTrue(report["recognized_install"])
            self.assertTrue(report["ok"])

            (app / "old-install-sentinel.txt").write_text("old\n", encoding="utf-8")
            subprocess.run(
                [*command, "--replace"],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertFalse((app / "old-install-sentinel.txt").exists())
            backup_apps = list(backups.glob("*/app/old-install-sentinel.txt"))
            self.assertEqual(len(backup_apps), 1)

    def test_replace_refuses_unrecognized_application_directory(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            app = root / "app"
            app.mkdir()
            (app / "unrelated.txt").write_text("mine\n", encoding="utf-8")
            completed = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "install.py"),
                    "--app-dir",
                    str(app),
                    "--bin-dir",
                    str(root / "bin"),
                    "--skills-dir",
                    str(root / "skills"),
                    "--backup-dir",
                    str(root / "backups"),
                    "--replace",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("unrecognized", completed.stderr + completed.stdout)
            self.assertTrue((app / "unrelated.txt").is_file())

    def test_transaction_restores_prior_targets_after_mid_commit_failure(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            first_target = root / "first"
            first_target.mkdir()
            (first_target / "value.txt").write_text("old-first\n", encoding="utf-8")
            second_target = root / "second"
            second_target.write_text("old-second\n", encoding="utf-8")
            first_stage = root / "first-stage"
            first_stage.mkdir()
            (first_stage / "value.txt").write_text("new-first\n", encoding="utf-8")
            second_stage = root / "second-stage"
            second_stage.write_text("new-second\n", encoding="utf-8")
            real_replace = os.replace

            def replace(source: str | Path, destination: str | Path) -> None:
                if Path(source) == second_stage and Path(destination) == second_target:
                    raise OSError("injected second-target failure")
                real_replace(source, destination)

            with mock.patch.object(INSTALLER.os, "replace", side_effect=replace):
                with self.assertRaisesRegex(OSError, "injected"):
                    INSTALLER._commit_transaction(
                        [(first_stage, first_target), (second_stage, second_target)]
                    )
            self.assertEqual((first_target / "value.txt").read_text(), "old-first\n")
            self.assertEqual(second_target.read_text(), "old-second\n")


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class LocalCliInstallerTests(unittest.TestCase):
    def test_installer_creates_working_dependency_free_launcher(self) -> None:
        project_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            app_dir = root / "app"
            bin_dir = root / "bin"
            subprocess.run(
                [
                    sys.executable,
                    str(project_root / "scripts" / "install_cli.py"),
                    "--app-dir",
                    str(app_dir),
                    "--bin-dir",
                    str(bin_dir),
                ],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            completed = subprocess.run(
                [str(bin_dir / "fieldlab"), "--help"],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertIn("Evolve and evaluate reusable agent skills", completed.stdout)
            self.assertTrue((app_dir / ".skill-field-lab-install").is_file())
            self.assertTrue((app_dir / "fieldlab" / "cli.py").is_file())


if __name__ == "__main__":
    unittest.main()

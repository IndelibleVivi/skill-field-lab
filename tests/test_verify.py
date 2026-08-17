from __future__ import annotations

import os
import tempfile
import time
import unittest
from pathlib import Path

from fieldlab.verify import evaluate_file_assertions
from fieldlab.workspace import prepare_workspace


@unittest.skipUnless(os.name == "posix", "v0.1 live execution is POSIX-only")
class CommandAssertionIsolationTests(unittest.TestCase):
    def test_timed_command_assertion_cannot_leave_late_child(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            case_dir = root / "case"
            fixture = case_dir / "fixture"
            fixture.mkdir(parents=True)
            sentinel = root / "command-late.txt"
            command = fixture / "check.sh"
            command.write_text(
                """#!/bin/sh
sentinel="$1"
(sleep 1.4; printf late > "$sentinel"; sleep 60) &
sleep 60
""",
                encoding="utf-8",
            )
            command.chmod(0o755)
            workspace = root / "workspace"
            prepare_workspace(
                case_dir=case_dir,
                subject={"overlays": []},
                pack_dir=root,
                workspace=workspace,
            )
            case = {
                "assertions": [
                    {
                        "type": "command",
                        "argv": ["./check.sh", str(sentinel)],
                        "timeout_seconds": 1,
                    }
                ]
            }
            results = evaluate_file_assertions(case, workspace, root / "artifacts")
            sealed_stdout = root / "artifacts" / "command-000" / "stdout.log"
            sealed_size = sealed_stdout.stat().st_size
            time.sleep(1.6)
            self.assertFalse(results[0]["passed"])
            self.assertTrue(results[0]["details"]["execution"]["quiescent"])
            self.assertFalse(sentinel.exists())
            self.assertEqual(sealed_stdout.stat().st_size, sealed_size)


if __name__ == "__main__":
    unittest.main()

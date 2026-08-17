from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fieldlab.adapters.codex_exec import CodexExecAdapter
from fieldlab.process import ProcessResult


def write_fake(path: Path) -> None:
    path.write_text(
        """#!/bin/sh
if [ "$1" = "--version" ]; then
  echo codex-cli-adapter-fake
  exit 0
fi
exit 0
""",
        encoding="utf-8",
    )
    path.chmod(0o755)


class AdapterCommandTests(unittest.TestCase):
    def test_repo_scoped_command_has_explicit_identity_and_current_flags(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            fake = root / "codex"
            write_fake(fake)
            adapter = CodexExecAdapter(str(fake))
            command = adapter.command(
                workspace=root,
                prompt="do the task",
                subject={"attribution": "repo_scoped"},
                execution={
                    "approval_policy": "never",
                    "sandbox": "workspace-write",
                    "network_access": False,
                    "selection_mode": "explicit",
                    "requested_model": "model-a",
                    "requested_reasoning_effort": "high",
                },
            )
        self.assertEqual(command[1:4], ["--ask-for-approval", "never", "exec"])
        self.assertIn("--ignore-user-config", command)
        self.assertIn("--ephemeral", command)
        self.assertIn("--json", command)
        self.assertEqual(command[command.index("--model") + 1], "model-a")
        self.assertIn('model_reasoning_effort="high"', command)
        self.assertIn("sandbox_workspace_write.network_access=false", command)

    def test_repo_scoped_execution_isolates_home_but_preserves_codex_home(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            fake = root / "codex"
            write_fake(fake)
            adapter = CodexExecAdapter(str(fake))
            workspace = root / "workspace"
            workspace.mkdir()
            attempt = root / "attempt"
            trace = attempt / "trace.jsonl"
            stderr = attempt / "stderr.log"
            auth_home = root / "codex-auth"
            auth_home.mkdir()
            result = ProcessResult(
                command=[str(fake)],
                return_code=0,
                timed_out=False,
                elapsed_seconds=0.01,
                termination_reason="exited",
                graceful_termination=False,
                forced_termination=False,
                quiescent=True,
                orphan_descendants=False,
                termination_error=None,
            )
            with mock.patch.dict(os.environ, {"CODEX_HOME": str(auth_home)}), mock.patch(
                "fieldlab.adapters.codex_exec.run_bounded_process",
                return_value=result,
            ) as bounded:
                adapter.execute(
                    workspace=workspace,
                    prompt="do the task",
                    subject={"attribution": "repo_scoped"},
                    execution={
                        "approval_policy": "never",
                        "sandbox": "workspace-write",
                        "network_access": False,
                        "selection_mode": "explicit",
                        "requested_model": "model-a",
                        "requested_reasoning_effort": "high",
                        "timeout_seconds": 30,
                    },
                    trace_path=trace,
                    stderr_path=stderr,
                )
            env = bounded.call_args.kwargs["env"]
            expected_home = attempt / "worker-home"
            self.assertEqual(Path(env["HOME"]), expected_home)
            self.assertEqual(Path(env["USERPROFILE"]), expected_home)
            self.assertEqual(Path(env["CODEX_HOME"]), auth_home.resolve())
            self.assertTrue(expected_home.is_dir())
            self.assertNotEqual(Path(env["HOME"]), Path.home())


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from ..errors import ConfigError, ExecutionError
from ..io import sha256_file
from ..process import ProcessResult, run_bounded_process


class CodexExecAdapter:
    name = "codex-exec"

    def __init__(self, executable: str) -> None:
        discovered = shutil.which(executable)
        if not discovered:
            raise ConfigError(f"Codex CLI not found: {executable}")
        self.path = Path(discovered).expanduser().resolve()

    def identity(self) -> dict[str, Any]:
        try:
            completed = subprocess.run(
                [str(self.path), "--version"],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=15,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise ExecutionError(f"could not read Codex version: {exc}") from exc
        identity: dict[str, Any] = {
            "adapter": self.name,
            "codex_path": str(self.path),
            "codex_version": completed.stdout.strip(),
        }
        if self.path.is_file():
            try:
                identity["codex_executable_sha256"] = sha256_file(self.path)
            except OSError:
                identity["codex_executable_sha256"] = None
        return identity

    def command(
        self,
        *,
        workspace: Path,
        prompt: str,
        subject: dict[str, Any],
        execution: dict[str, Any],
    ) -> list[str]:
        command = [
            str(self.path),
            "--ask-for-approval",
            execution["approval_policy"],
            "exec",
            "--json",
            "--ephemeral",
            "--color",
            "never",
        ]
        command.append("--ignore-user-config")
        command.extend(["--sandbox", execution["sandbox"]])
        if execution["sandbox"] == "workspace-write":
            network = "true" if execution["network_access"] else "false"
            command.extend(["-c", f"sandbox_workspace_write.network_access={network}"])
        if execution["selection_mode"] == "explicit":
            command.extend(["--model", execution["requested_model"]])
            command.extend(
                [
                    "-c",
                    "model_reasoning_effort=" + json.dumps(execution["requested_reasoning_effort"]),
                ]
            )
        command.extend(["-C", str(workspace), prompt])
        return command

    def execute(
        self,
        *,
        workspace: Path,
        prompt: str,
        subject: dict[str, Any],
        execution: dict[str, Any],
        trace_path: Path,
        stderr_path: Path,
    ) -> ProcessResult:
        command = self.command(
            workspace=workspace,
            prompt=prompt,
            subject=subject,
            execution=execution,
        )
        env = os.environ.copy()
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        # Keep Codex authentication in the operator's CODEX_HOME while hiding
        # user Skill discovery under HOME. --ignore-user-config handles config
        # separately. This is workspace-scoped, not hermetic, isolation.
        operator_home = Path.home().resolve()
        codex_home = Path(
            env.get("CODEX_HOME", str(operator_home / ".codex"))
        ).expanduser().resolve()
        worker_home = trace_path.parent / "worker-home"
        worker_home.mkdir(parents=True, exist_ok=True)
        env["HOME"] = str(worker_home)
        env["USERPROFILE"] = str(worker_home)
        env["CODEX_HOME"] = str(codex_home)
        return run_bounded_process(
            command,
            cwd=workspace,
            stdout_path=trace_path,
            stderr_path=stderr_path,
            timeout_seconds=float(execution["timeout_seconds"]),
            env=env,
        )

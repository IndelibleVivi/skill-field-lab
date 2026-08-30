from __future__ import annotations

import os
import signal
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .errors import ExecutionError


@dataclass(frozen=True)
class ProcessResult:
    command: list[str]
    return_code: int | None
    timed_out: bool
    elapsed_seconds: float
    termination_reason: str
    graceful_termination: bool
    forced_termination: bool
    quiescent: bool
    orphan_descendants: bool
    termination_error: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _group_alive(pgid: int) -> bool:
    """Return whether the process group still has a non-zombie member.

    A killed orphan may remain briefly as a zombie owned by init. Zombies cannot
    mutate artifacts, hold file descriptors, consume model quota, or execute work,
    so a zombie-only group is quiescent even before the OS reaps its process table
    entry. `ps -eo` is available on the supported macOS/Linux surface; fall back to
    killpg probing if it is unavailable.
    """
    try:
        os.killpg(pgid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    try:
        completed = subprocess.run(
            ["ps", "-eo", "pgid=,stat="],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=1,
        )
    except (OSError, subprocess.SubprocessError):
        return True
    for raw_line in completed.stdout.splitlines():
        fields = raw_line.split(None, 1)
        if len(fields) != 2:
            continue
        try:
            member_pgid = int(fields[0])
        except ValueError:
            continue
        state = fields[1].strip()
        if member_pgid == pgid and state and not state.startswith("Z"):
            return True
    return False


def _wait_group_gone(pgid: int, timeout_seconds: float) -> bool:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if not _group_alive(pgid):
            return True
        time.sleep(0.025)
    return not _group_alive(pgid)


def _reap_parent(process: subprocess.Popen[bytes], timeout_seconds: float = 1.0) -> None:
    if process.poll() is not None:
        process.wait()
        return
    try:
        process.wait(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        return


def _terminate_group(
    process: subprocess.Popen[bytes],
    pgid: int,
    *,
    grace_seconds: float,
    kill_seconds: float,
) -> tuple[bool, bool, bool, str | None]:
    graceful = False
    forced = False
    error: str | None = None
    try:
        if _group_alive(pgid):
            os.killpg(pgid, signal.SIGTERM)
            graceful = True
        _reap_parent(process, min(grace_seconds, 1.0))
        if _wait_group_gone(pgid, grace_seconds):
            return graceful, forced, True, None
        if _group_alive(pgid):
            os.killpg(pgid, signal.SIGKILL)
            forced = True
        _reap_parent(process, min(kill_seconds, 1.0))
        if _wait_group_gone(pgid, kill_seconds):
            return graceful, forced, True, None
        error = f"process group {pgid} remained alive after SIGKILL"
    except (OSError, subprocess.SubprocessError) as exc:
        error = f"process-group cleanup failed: {exc}"
    return graceful, forced, False, error


def run_bounded_process(
    command: list[str],
    *,
    cwd: Path,
    stdout_path: Path,
    stderr_path: Path,
    timeout_seconds: float,
    env: dict[str, str] | None = None,
    grace_seconds: float = 2.0,
    kill_seconds: float = 2.0,
    post_exit_grace_seconds: float = 0.2,
) -> ProcessResult:
    """Run a command in a dedicated POSIX session and seal only after group quiescence.

    Field Lab v0.2 intentionally fails closed on non-POSIX hosts. A clean parent exit
    is insufficient: surviving descendants are terminated and the result is marked
    `orphan-descendants` so it cannot masquerade as a normal successful attempt.
    """

    if os.name != "posix":
        raise ExecutionError(
            "live bounded execution is supported on POSIX hosts only in v0.2; "
            "Windows needs a Job Object adapter before it can claim quiescence"
        )
    if timeout_seconds <= 0:
        raise ExecutionError("timeout_seconds must be positive")
    stdout_path.parent.mkdir(parents=True, exist_ok=True)
    stderr_path.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    timed_out = False
    termination_reason = "exited"
    orphan_descendants = False
    graceful = False
    forced = False
    quiescent = False
    termination_error: str | None = None
    return_code: int | None = None

    with stdout_path.open("wb") as stdout_handle, stderr_path.open("wb") as stderr_handle:
        process = subprocess.Popen(
            command,
            cwd=cwd,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=stdout_handle,
            stderr=stderr_handle,
            start_new_session=True,
        )
        pgid = process.pid
        try:
            return_code = process.wait(timeout=timeout_seconds)
            if _wait_group_gone(pgid, post_exit_grace_seconds):
                quiescent = True
            else:
                orphan_descendants = True
                termination_reason = "orphan-descendants"
                graceful, forced, quiescent, termination_error = _terminate_group(
                    process,
                    pgid,
                    grace_seconds=grace_seconds,
                    kill_seconds=kill_seconds,
                )
        except subprocess.TimeoutExpired:
            timed_out = True
            termination_reason = "timeout"
            graceful, forced, quiescent, termination_error = _terminate_group(
                process,
                pgid,
                grace_seconds=grace_seconds,
                kill_seconds=kill_seconds,
            )
            return_code = process.poll()
        except KeyboardInterrupt:
            termination_reason = "keyboard-interrupt"
            graceful, forced, quiescent, termination_error = _terminate_group(
                process,
                pgid,
                grace_seconds=grace_seconds,
                kill_seconds=kill_seconds,
            )
            if not quiescent:
                raise ExecutionError(termination_error or "interrupt cleanup did not quiesce")
            raise

    return ProcessResult(
        command=command,
        return_code=return_code,
        timed_out=timed_out,
        elapsed_seconds=round(time.monotonic() - started, 3),
        termination_reason=termination_reason,
        graceful_termination=graceful,
        forced_termination=forced,
        quiescent=quiescent,
        orphan_descendants=orphan_descendants,
        termination_error=termination_error,
    )

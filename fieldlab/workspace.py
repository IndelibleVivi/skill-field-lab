from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from .errors import ConfigError, ExecutionError
from .io import safe_relative
from .subjects import materialize_subject
from .trees import validate_tree_symlinks


def _run_git(
    argv: list[str],
    cwd: Path,
    *,
    timeout: int = 120,
    env_overrides: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    if env_overrides:
        env.update(env_overrides)
    try:
        return subprocess.run(
            argv,
            cwd=cwd,
            env=env,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise ExecutionError(f"command failed in {cwd}: {' '.join(argv)}: {exc}") from exc


def prepare_workspace(
    *,
    case_dir: Path,
    subject: dict,
    lab_root: Path,
    subject_id: str = "subject",
    workspace: Path,
) -> None:
    if workspace.exists():
        shutil.rmtree(workspace)
    fixture = case_dir / "fixture"
    if fixture.is_dir():
        validate_tree_symlinks(fixture, "fixture")
        shutil.copytree(fixture, workspace, symlinks=True)
    else:
        workspace.mkdir(parents=True)
    materialize_subject(
        subject_id=subject_id,
        subject=subject,
        lab_root=lab_root,
        workspace=workspace,
    )

    _run_git(["git", "init", "-q"], workspace)
    _run_git(["git", "config", "user.name", "Skill Field Lab"], workspace)
    _run_git(["git", "config", "user.email", "fieldlab@example.invalid"], workspace)
    _run_git(["git", "add", "--all"], workspace)
    _run_git(
        ["git", "commit", "--allow-empty", "--no-gpg-sign", "-q", "-m", "fieldlab baseline"],
        workspace,
    )


def changed_files(workspace: Path) -> list[str]:
    result = _run_git(
        ["git", "status", "--porcelain=v1", "-z", "--untracked-files=all"],
        workspace,
    )
    fields = result.stdout.split("\0")
    paths: list[str] = []
    index = 0
    while index < len(fields):
        entry = fields[index]
        if not entry:
            index += 1
            continue
        if len(entry) < 4 or entry[2] != " ":
            raise ExecutionError("git status returned an invalid porcelain v1 record")
        status = entry[:2]
        paths.append(entry[3:])
        index += 2 if "R" in status or "C" in status else 1
    return sorted(set(paths))


def capture_diff(workspace: Path) -> str:
    """Return the binary working-tree diff without mutating the real index.

    `git add -N` is needed so untracked files appear in `git diff HEAD`. It runs
    against a disposable copy of the index selected through `GIT_INDEX_FILE`, so
    the workspace's own index bytes and cached diff are never touched.
    """
    with tempfile.TemporaryDirectory(prefix="fieldlab-diff-index-") as raw:
        index = Path(raw) / "index"
        real_index = workspace / ".git" / "index"
        overrides = {"GIT_INDEX_FILE": str(index)}
        if real_index.is_file():
            shutil.copy2(real_index, index)
        else:
            _run_git(["git", "read-tree", "HEAD"], workspace, env_overrides=overrides)
        _run_git(["git", "add", "-N", "--all"], workspace, env_overrides=overrides)
        result = _run_git(
            ["git", "diff", "--binary", "--no-ext-diff", "HEAD", "--"],
            workspace,
            env_overrides=overrides,
        )
    return result.stdout


def copy_workspace(source: Path, target: Path) -> None:
    """Copy a sealed worker workspace into a disposable verifier copy.

    Verifier commands run against this copy so a command assertion cannot
    rewrite the frozen worker-final bytes that the receipt seals.
    """
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(source, target, symlinks=True)


def apply_expected(expected: Path, workspace: Path) -> None:
    if not expected.is_dir():
        raise ConfigError(f"expected/ directory is required for deterministic pack selftest: {expected}")
    copied = 0
    for source in sorted(expected.rglob("*")):
        if source.is_symlink():
            raise ConfigError(f"expected overlay refuses symlinks: {source}")
        if not source.is_file():
            continue
        relative = source.relative_to(expected).as_posix()
        target = safe_relative(workspace, relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        copied += 1
    if copied == 0:
        raise ConfigError(f"expected overlay is empty: {expected}")

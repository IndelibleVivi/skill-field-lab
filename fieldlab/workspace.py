from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from .errors import ConfigError, ExecutionError
from .io import safe_relative


def _run_git(argv: list[str], cwd: Path, *, timeout: int = 30) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
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


def _validate_tree_symlinks(root: Path, label: str) -> None:
    root_resolved = root.resolve()
    for path in root.rglob("*"):
        if not path.is_symlink():
            continue
        raw_target = Path(os.readlink(path))
        if raw_target.is_absolute():
            raise ConfigError(f"{label} refuses absolute symlink: {path}")
        resolved_target = (path.parent / raw_target).resolve(strict=False)
        try:
            resolved_target.relative_to(root_resolved)
        except ValueError as exc:
            raise ConfigError(f"{label} symlink escapes its tree: {path} -> {raw_target}") from exc


def _copy_overlay(source: Path, target: Path) -> None:
    if source.is_dir():
        if target.exists() and not target.is_dir():
            raise ConfigError(f"overlay directory target is not a directory: {target}")
        shutil.copytree(source, target, dirs_exist_ok=True, symlinks=True)
        return
    if source.is_file():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target, follow_symlinks=False)
        return
    raise ConfigError(f"overlay source does not exist: {source}")


def prepare_workspace(
    *,
    case_dir: Path,
    subject: dict,
    pack_dir: Path,
    workspace: Path,
) -> None:
    if workspace.exists():
        shutil.rmtree(workspace)
    fixture = case_dir / "fixture"
    _validate_tree_symlinks(fixture, "fixture")
    shutil.copytree(fixture, workspace, symlinks=True)
    for overlay in subject.get("overlays", []):
        source = safe_relative(pack_dir, overlay["source"])
        if source.is_dir():
            _validate_tree_symlinks(source, "subject overlay")
        target = safe_relative(workspace, overlay["target"])
        _copy_overlay(source, target)

    _run_git(["git", "init", "-q"], workspace)
    _run_git(["git", "config", "user.name", "Skill Field Lab"], workspace)
    _run_git(["git", "config", "user.email", "fieldlab@example.invalid"], workspace)
    _run_git(["git", "add", "--all"], workspace)
    _run_git(["git", "commit", "--no-gpg-sign", "-q", "-m", "fieldlab baseline"], workspace)


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
    _run_git(["git", "add", "-N", "--all"], workspace)
    result = _run_git(
        ["git", "diff", "--binary", "--no-ext-diff", "HEAD", "--"],
        workspace,
    )
    return result.stdout


def apply_expected(expected: Path, workspace: Path) -> None:
    if not expected.is_dir():
        raise ConfigError(f"expected/ directory is required for deterministic pack selftest: {expected}")
    copied = 0
    for source in sorted(expected.rglob("*")):
        if source.is_symlink():
            raise ConfigError(f"expected overlay refuses symlinks in v0.1: {source}")
        if not source.is_file():
            continue
        relative = source.relative_to(expected).as_posix()
        target = safe_relative(workspace, relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        copied += 1
    if copied == 0:
        raise ConfigError(f"expected overlay is empty: {expected}")

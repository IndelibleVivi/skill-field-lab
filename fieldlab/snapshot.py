from __future__ import annotations

import io
import os
import shutil
import subprocess
import tarfile
from pathlib import Path, PurePosixPath
from typing import Any

from .errors import ConfigError, ExecutionError
from .io import atomic_write_json, safe_relative, tree_digest, utc_now


def _git(repo: Path, argv: list[str], *, binary: bool = False) -> subprocess.CompletedProcess[Any]:
    try:
        return subprocess.run(
            ["git", "-C", str(repo), *argv],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=not binary,
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise ExecutionError(f"git {' '.join(argv)} failed in {repo}: {exc}") from exc


def _safe_member_relative(member_name: str, source_path: str) -> Path | None:
    member = PurePosixPath(member_name)
    prefix = PurePosixPath(source_path)
    if member.is_absolute() or ".." in member.parts:
        raise ExecutionError(f"unsafe path in git archive: {member_name}")
    try:
        relative = member.relative_to(prefix)
    except ValueError:
        raise ExecutionError(f"archive member escaped requested source path: {member_name}")
    if not relative.parts:
        return None
    return Path(*relative.parts)


def snapshot_git_tree(
    *,
    repo: Path,
    ref: str,
    source_path: str,
    output: Path,
    replace: bool,
) -> dict[str, Any]:
    repo = repo.expanduser().resolve()
    output = output.expanduser().resolve()
    if not (repo / ".git").exists():
        # Worktrees may have a .git file rather than directory.
        if not (repo / ".git").is_file():
            raise ConfigError(f"not a Git repository or worktree: {repo}")
    if not ref or ref.startswith("-"):
        raise ConfigError("ref must be a non-option Git revision")
    source = PurePosixPath(source_path)
    if source.is_absolute() or not source.parts or ".." in source.parts:
        raise ConfigError("source path must be a safe repository-relative path")
    if output.exists():
        if not replace:
            raise ConfigError(f"snapshot output exists; pass --replace to replace it: {output}")
        if output.is_dir():
            shutil.rmtree(output)
        else:
            output.unlink()
    output.mkdir(parents=True)

    commit = _git(repo, ["rev-parse", "--verify", f"{ref}^{{commit}}"])
    resolved_commit = commit.stdout.strip()
    archive = _git(repo, ["archive", "--format=tar", resolved_commit, source.as_posix()], binary=True)
    with tarfile.open(fileobj=io.BytesIO(archive.stdout), mode="r:") as tar:
        for member in tar.getmembers():
            relative = _safe_member_relative(member.name, source.as_posix())
            if relative is None:
                continue
            target = safe_relative(output, relative.as_posix())
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            if not member.isfile():
                raise ExecutionError(
                    f"snapshot refuses symlink, hardlink, device, or special archive member: {member.name}"
                )
            extracted = tar.extractfile(member)
            if extracted is None:
                raise ExecutionError(f"could not read archive member: {member.name}")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(extracted.read())
            target.chmod(member.mode & 0o777)

    if not any(output.rglob("*")):
        shutil.rmtree(output)
        raise ExecutionError(f"Git snapshot was empty: {ref}:{source_path}")
    metadata = {
        "schema_version": 1,
        "created_at": utc_now(),
        "source_ref": ref,
        "resolved_commit": resolved_commit,
        "source_path": source.as_posix(),
        "tree_sha256": tree_digest(output),
    }
    atomic_write_json(output.parent / f"{output.name}.snapshot.json", metadata)
    return metadata

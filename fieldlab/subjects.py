from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
from typing import Any

from .contracts import resolve_local_path, safe_mount
from .errors import ConfigError, ExecutionError
from .io import safe_relative, tree_digest
from .snapshot import materialize_git_tree
from .trees import copy_tree_source


def _git(repo: Path, *args: str) -> str:
    try:
        completed = subprocess.run(
            ["git", "-C", str(repo), *args],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise ExecutionError(f"git {' '.join(args)} failed in {repo}: {exc}") from exc
    return completed.stdout.strip()


def declared_subject_scope(subject: dict[str, Any]) -> str:
    if subject.get("kind") == "control":
        return "isolated-control"
    if subject.get("kind") == "agent-skill":
        return "workspace-scoped"
    raise ConfigError("subject kind must be agent-skill or control")


def _git_context(path: Path) -> dict[str, Any] | None:
    try:
        root = Path(_git(path, "rev-parse", "--show-toplevel")).resolve()
        head = _git(path, "rev-parse", "HEAD")
    except ExecutionError:
        return None
    try:
        relative = path.resolve().relative_to(root).as_posix()
    except ValueError:
        relative = None
    return {"repo_root": str(root), "head": head, "source_relpath": relative}


def _source_path(subject: dict[str, Any], lab_root: Path) -> Path:
    source = subject["source"]
    if source["type"] == "local-path":
        return resolve_local_path(lab_root, source["path"])
    if source["type"] == "snapshot":
        try:
            return safe_relative(lab_root, source["path"])
        except ConfigError as exc:
            raise ConfigError("snapshot source must stay inside the lab") from exc
    raise ConfigError("local-git-ref does not have a mutable source path")


def subject_identity(
    subject_id: str,
    subject: dict[str, Any],
    lab_root: Path,
) -> dict[str, Any]:
    if subject.get("kind") == "control":
        return {
            "subject_scope": "isolated-control",
            "source": {"type": "control"},
            "mount": None,
        }
    source = subject["source"]
    mount = subject.get("mount", f".agents/skills/{subject_id}")
    if source["type"] in {"local-path", "snapshot"}:
        path = _source_path(subject, lab_root)
        if not path.is_dir():
            raise ConfigError(f"subject source does not exist: {path}")
        identity: dict[str, Any] = {
            "type": source["type"],
            "resolved_path": str(path),
            "tree_sha256": tree_digest(path),
        }
        if source["type"] == "local-path":
            identity["git"] = _git_context(path)
        return {
            "subject_scope": "workspace-scoped",
            "source": identity,
            "mount": mount,
        }

    repo = resolve_local_path(lab_root, source["repo"])
    with tempfile.TemporaryDirectory(prefix="fieldlab-subject-identity-") as raw:
        materialized = Path(raw) / "tree"
        metadata = materialize_git_tree(
            repo=repo,
            ref=source["ref"],
            source_path=source["subpath"],
            output=materialized,
            replace=False,
        )
    return {
        "subject_scope": "workspace-scoped",
        "source": {
            "type": "local-git-ref",
            "repo": str(repo),
            "requested_ref": source["ref"],
            "resolved_commit": metadata["resolved_commit"],
            "subpath": source["subpath"],
            "tree_sha256": metadata["tree_sha256"],
        },
        "mount": mount,
    }


def materialize_subject(
    *,
    subject_id: str,
    subject: dict[str, Any],
    lab_root: Path,
    workspace: Path,
) -> None:
    if subject.get("kind") == "control":
        return
    mount = safe_mount(workspace, subject.get("mount", f".agents/skills/{subject_id}"))
    source = subject["source"]
    if source["type"] in {"local-path", "snapshot"}:
        copy_tree_source(_source_path(subject, lab_root), mount, "subject source")
        return
    repo = resolve_local_path(lab_root, source["repo"])
    with tempfile.TemporaryDirectory(prefix="fieldlab-subject-materialize-") as raw:
        staged = Path(raw) / "tree"
        materialize_git_tree(
            repo=repo,
            ref=source["ref"],
            source_path=source["subpath"],
            output=staged,
            replace=False,
        )
        copy_tree_source(staged, mount, "subject source")

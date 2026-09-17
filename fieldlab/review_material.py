from __future__ import annotations

import os
import shutil
import uuid
from pathlib import Path
from typing import Any

from .errors import ConfigError, EvidenceError
from .io import atomic_write_json, sha256_file, utc_now


MAX_REVIEW_MATERIAL_FILES = 32
MAX_REVIEW_MATERIAL_FILE_BYTES = 1_048_576
MAX_REVIEW_MATERIAL_TOTAL_BYTES = 4_194_304
MATERIAL_DIR_NAME = "review-material"
MANIFEST_NAME = "manifest.json"
MANIFEST_REFERENCE = f"{MATERIAL_DIR_NAME}/{MANIFEST_NAME}"
LIMITS = {
    "max_files": MAX_REVIEW_MATERIAL_FILES,
    "max_file_bytes": MAX_REVIEW_MATERIAL_FILE_BYTES,
    "max_total_bytes": MAX_REVIEW_MATERIAL_TOTAL_BYTES,
}


def material_path_shape_error(relative: object) -> str | None:
    """Return why one declared material path is not an exact workspace file."""
    if not isinstance(relative, str) or not relative:
        return "must be a non-empty string"
    if "\\" in relative:
        return "must use POSIX separators"
    if any(token in relative for token in ("*", "?", "[")):
        return "must be an exact path, not a glob"
    if any(part in {"", ".", ".."} for part in relative.split("/")):
        return "must be a workspace-relative file path without '.' or '..'"
    return None


def validate_declared_material(declared: object, label: str) -> list[str]:
    if not isinstance(declared, list) or not declared:
        raise ConfigError(f"{label} must be a non-empty list of workspace-relative file paths")
    seen: set[str] = set()
    for index, item in enumerate(declared):
        error = material_path_shape_error(item)
        if error is not None:
            raise ConfigError(f"{label}[{index}] {error}")
        if item in seen:
            raise ConfigError(f"{label} must contain unique paths")
        seen.add(item)
    if len(declared) > MAX_REVIEW_MATERIAL_FILES:
        raise ConfigError(f"{label} declares more than {MAX_REVIEW_MATERIAL_FILES} files")
    return list(declared)


def _checked_source(workspace: Path, relative: str) -> Path:
    root = workspace.resolve()
    parts = relative.split("/")
    current = workspace
    for part in parts[:-1]:
        current = current / part
        if current.is_symlink():
            raise EvidenceError(
                f"review material {relative!r} has a symlinked ancestor: {part!r}"
            )
    source = workspace.joinpath(*parts)
    if source.is_symlink():
        raise EvidenceError(f"review material {relative!r} is a symlink")
    if not source.exists():
        raise EvidenceError(f"review material {relative!r} is missing")
    if not source.is_file():
        raise EvidenceError(f"review material {relative!r} is not a regular file")
    try:
        source.resolve().relative_to(root)
    except ValueError as exc:
        raise EvidenceError(
            f"review material {relative!r} escapes the worker workspace"
        ) from exc
    return source


def seal_review_material(
    *,
    workspace: Path,
    attempt_dir: Path,
    declared: list[str],
) -> dict[str, Any]:
    """Atomically capture declared worker-final files into attempt-owned material.

    Any shape, existence, symlink, readability, or bound failure removes the
    staging tree and the installed material directory, so a failed capture can
    never leave a partial review-material set behind.
    """
    if len(declared) > MAX_REVIEW_MATERIAL_FILES:
        raise EvidenceError(
            f"declared review material exceeds {MAX_REVIEW_MATERIAL_FILES} files"
        )
    staging = attempt_dir / f".review-material-staging-{uuid.uuid4().hex}"
    staging.mkdir(parents=True)
    files: list[dict[str, Any]] = []
    total_bytes = 0
    try:
        for relative in declared:
            shape_error = material_path_shape_error(relative)
            if shape_error is not None:
                raise EvidenceError(f"review material {relative!r} {shape_error}")
            source = _checked_source(workspace, relative)
            size = source.stat().st_size
            if size > MAX_REVIEW_MATERIAL_FILE_BYTES:
                raise EvidenceError(
                    f"review material {relative!r} is {size} bytes, above the "
                    f"{MAX_REVIEW_MATERIAL_FILE_BYTES}-byte per-file bound"
                )
            total_bytes += size
            if total_bytes > MAX_REVIEW_MATERIAL_TOTAL_BYTES:
                raise EvidenceError(
                    "declared review material is above the "
                    f"{MAX_REVIEW_MATERIAL_TOTAL_BYTES}-byte aggregate bound"
                )
            target = staging.joinpath(*relative.split("/"))
            target.parent.mkdir(parents=True, exist_ok=True)
            try:
                shutil.copyfile(source, target)
            except OSError as exc:
                raise EvidenceError(
                    f"review material {relative!r} could not be read: {exc}"
                ) from exc
            files.append(
                {"path": relative, "sha256": sha256_file(target), "bytes": size}
            )
        manifest = {
            "schema_version": 2,
            "status": "sealed",
            "created_at": utc_now(),
            "source": "worker-final-workspace",
            "declared": list(declared),
            "limits": dict(LIMITS),
            "files": files,
            "total_bytes": total_bytes,
        }
        atomic_write_json(staging / MANIFEST_NAME, manifest)
        os.replace(staging, attempt_dir / MATERIAL_DIR_NAME)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        shutil.rmtree(attempt_dir / MATERIAL_DIR_NAME, ignore_errors=True)
        raise
    manifest_path = attempt_dir / MATERIAL_DIR_NAME / MANIFEST_NAME
    return {
        "status": "sealed",
        "directory": MATERIAL_DIR_NAME,
        "manifest": MANIFEST_REFERENCE,
        "manifest_sha256": sha256_file(manifest_path),
        "files": files,
        "total_bytes": total_bytes,
        "limits": dict(LIMITS),
    }

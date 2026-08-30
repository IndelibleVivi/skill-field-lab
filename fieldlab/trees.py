from __future__ import annotations

import os
import shutil
from pathlib import Path

from .errors import ConfigError


def validate_tree_symlinks(root: Path, label: str) -> None:
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


def copy_tree_source(source: Path, target: Path, label: str) -> None:
    if source.is_dir():
        validate_tree_symlinks(source, label)
        if target.exists() and not target.is_dir():
            raise ConfigError(f"{label} target is not a directory: {target}")
        shutil.copytree(source, target, dirs_exist_ok=True, symlinks=True)
        return
    if source.is_file():
        if source.is_symlink():
            raise ConfigError(f"{label} refuses a top-level symlink: {source}")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target, follow_symlinks=False)
        return
    raise ConfigError(f"{label} does not exist: {source}")

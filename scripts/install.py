#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
import shutil
import stat
import subprocess
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


MARKER = ".skill-field-lab-install"
CONTROLLERS = ("pattern-intake", "skill-eval")
LEGACY_CONTROLLER_DIGESTS = {
    "pattern-intake": "6d48e4133cd1f036168b25ba14c40c3abb8bb6eefc9bc453a7f3b74beda7a7b9",
    "skill-eval": "189a5f20e838d64eb16bb347814d16867d41941bd2213e93ff00349bd1e1bc86",
}


def _default_skills_dir() -> Path:
    override = os.environ.get("FIELDLAB_SKILLS_DIR")
    if override:
        return Path(override)
    codex_home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
    return codex_home / "skills"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Transactionally install Skill Field Lab and its controller Skills."
    )
    parser.add_argument(
        "--app-dir",
        type=Path,
        default=Path(os.environ.get("FIELDLAB_HOME", "~/.local/share/skill-field-lab")),
    )
    parser.add_argument(
        "--bin-dir",
        type=Path,
        default=Path(os.environ.get("FIELDLAB_BIN_DIR", "~/.local/bin")),
    )
    parser.add_argument("--skills-dir", type=Path, default=_default_skills_dir())
    parser.add_argument(
        "--backup-dir",
        type=Path,
        default=Path(os.environ["FIELDLAB_BACKUP_DIR"])
        if "FIELDLAB_BACKUP_DIR" in os.environ
        else None,
    )
    parser.add_argument("--replace", action="store_true")
    parser.add_argument(
        "--cli-only",
        action="store_true",
        help="Install only the app and launcher; leave controller discovery paths unchanged.",
    )
    return parser


def _tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
        relative_path = path.relative_to(root)
        if ".git" in relative_path.parts or "__pycache__" in relative_path.parts:
            continue
        relative = relative_path.as_posix().encode("utf-8")
        if path.is_symlink():
            kind = b"symlink"
            payload = os.readlink(path).encode("utf-8")
        elif path.is_file():
            kind = b"executable" if path.stat().st_mode & 0o111 else b"file"
            payload = path.read_bytes()
        else:
            continue
        digest.update(kind + b"\0" + relative + b"\0")
        digest.update(len(payload).to_bytes(8, "big") + payload)
    return digest.hexdigest()


def _python_source_digest(root: Path) -> str:
    digest = hashlib.sha256()
    paths = sorted(root.rglob("*.py"), key=lambda item: item.relative_to(root).as_posix())
    if not paths:
        raise SystemExit(f"no Python source found in {root}")
    for path in paths:
        if "__pycache__" in path.relative_to(root).parts:
            continue
        relative = path.relative_to(root).as_posix().encode("utf-8")
        payload = path.read_bytes()
        digest.update(b"python\0" + relative + b"\0")
        digest.update(len(payload).to_bytes(8, "big") + payload)
    return digest.hexdigest()


def _git_head(source_root: Path) -> str | None:
    try:
        completed = subprocess.run(
            ["git", "-C", str(source_root), "rev-parse", "HEAD"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return completed.stdout.strip() or None


def _read_receipt(app_dir: Path) -> dict[str, Any] | None:
    path = app_dir / "installation-receipt.json"
    if not path.is_file():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _recognized_app(path: Path) -> bool:
    return path.is_dir() and (path / MARKER).is_file()


def _recognized_launcher(path: Path, app_dir: Path) -> bool:
    if not path.is_file() or path.is_symlink():
        return False
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return False
    return str(app_dir / "launcher.py") in text and "python3" in text


def _receipt_controller_digest(receipt: dict[str, Any] | None, name: str) -> str | None:
    if not receipt:
        return None
    controllers = receipt.get("source", {}).get("controllers", {})
    record = controllers.get(name) if isinstance(controllers, dict) else None
    return record.get("tree_sha256") if isinstance(record, dict) else None


def _recognized_controller(
    path: Path,
    *,
    name: str,
    current_digest: str,
    prior_receipt: dict[str, Any] | None,
) -> bool:
    if not path.is_dir():
        return False
    actual = _tree_digest(path)
    recognized = {
        current_digest,
        LEGACY_CONTROLLER_DIGESTS[name],
        _receipt_controller_digest(prior_receipt, name),
    }
    return actual in {value for value in recognized if value}


def _preflight_target(
    path: Path,
    *,
    replace: bool,
    label: str,
    recognizer: Callable[[Path], bool],
) -> None:
    if not path.exists() and not path.is_symlink():
        return
    if not replace:
        raise SystemExit(f"refusing to overwrite existing {label}: {path}; use --replace")
    if not recognizer(path):
        raise SystemExit(f"refusing to replace unrecognized {label}: {path}")


def _copy_source_tree(source: Path, destination: Path) -> None:
    shutil.copytree(
        source,
        destination,
        dirs_exist_ok=True,
        symlinks=True,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"),
    )


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _backup_existing(
    *,
    backup_root: Path,
    app_dir: Path,
    launcher: Path,
    controller_targets: dict[str, Path],
) -> bool:
    existing = [app_dir, launcher, *controller_targets.values()]
    if not any(path.exists() or path.is_symlink() for path in existing):
        return False
    backup_root.mkdir(parents=True, exist_ok=False)
    copied: list[dict[str, str]] = []
    mappings = [
        (app_dir, backup_root / "app"),
        (launcher, backup_root / "bin" / launcher.name),
        *(
            (path, backup_root / "skills" / name)
            for name, path in controller_targets.items()
        ),
    ]
    for source, destination in mappings:
        if not source.exists() and not source.is_symlink():
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir() and not source.is_symlink():
            shutil.copytree(source, destination, symlinks=True)
        else:
            shutil.copy2(source, destination, follow_symlinks=False)
        copied.append({"source": str(source), "backup": str(destination)})
    _write_json(
        backup_root / "backup-manifest.json",
        {
            "schema_version": 1,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "files": copied,
        },
    )
    return True


def _remove_path(path: Path) -> None:
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    elif path.exists() or path.is_symlink():
        path.unlink()


def _commit_transaction(staged_targets: list[tuple[Path, Path]]) -> None:
    transaction_id = uuid.uuid4().hex
    applied: list[tuple[Path, Path | None]] = []
    try:
        for staged, target in staged_targets:
            rollback: Path | None = None
            if target.exists() or target.is_symlink():
                rollback = target.with_name(f".{target.name}.fieldlab-old-{transaction_id}")
                if rollback.exists() or rollback.is_symlink():
                    raise RuntimeError(f"unexpected rollback collision: {rollback}")
                os.replace(target, rollback)
            try:
                os.replace(staged, target)
            except BaseException:
                if rollback is not None:
                    os.replace(rollback, target)
                raise
            applied.append((target, rollback))
    except BaseException:
        for target, rollback in reversed(applied):
            _remove_path(target)
            if rollback is not None and (rollback.exists() or rollback.is_symlink()):
                os.replace(rollback, target)
        raise
    for _, rollback in applied:
        if rollback is not None:
            _remove_path(rollback)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    source_root = Path(__file__).resolve().parent.parent
    app_dir = args.app_dir.expanduser().resolve()
    bin_dir = args.bin_dir.expanduser().resolve()
    skills_dir = args.skills_dir.expanduser().resolve()
    backup_parent = (
        args.backup_dir.expanduser().resolve()
        if args.backup_dir is not None
        else (app_dir.parent / "skill-field-lab-backups").resolve()
    )
    launcher = bin_dir / "fieldlab"
    controller_sources = {name: source_root / "skills" / name for name in CONTROLLERS}
    controller_targets = (
        {} if args.cli_only else {name: skills_dir / name for name in CONTROLLERS}
    )
    controller_digests = {
        name: _tree_digest(source) for name, source in controller_sources.items()
    }
    prior_receipt = _read_receipt(app_dir) if _recognized_app(app_dir) else None

    _preflight_target(
        app_dir,
        replace=args.replace,
        label="application directory",
        recognizer=_recognized_app,
    )
    _preflight_target(
        launcher,
        replace=args.replace,
        label="launcher",
        recognizer=lambda path: _recognized_launcher(path, app_dir),
    )
    for name, target in controller_targets.items():
        _preflight_target(
            target,
            replace=args.replace,
            label=f"controller Skill {name}",
            recognizer=lambda path, name=name: _recognized_controller(
                path,
                name=name,
                current_digest=controller_digests[name],
                prior_receipt=prior_receipt,
            ),
        )

    app_dir.parent.mkdir(parents=True, exist_ok=True)
    bin_dir.mkdir(parents=True, exist_ok=True)
    if controller_targets:
        skills_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    backup_root = backup_parent / f"{timestamp}-{uuid.uuid4().hex[:8]}"
    backup_created = _backup_existing(
        backup_root=backup_root,
        app_dir=app_dir,
        launcher=launcher,
        controller_targets=controller_targets,
    )

    stages: list[Path] = []
    try:
        app_stage = Path(tempfile.mkdtemp(prefix=".fieldlab-app-stage-", dir=app_dir.parent))
        stages.append(app_stage)
        for name in ("fieldlab", "skills", "schemas", "templates"):
            _copy_source_tree(source_root / name, app_stage / name)
        for name in ("VERSION", "LICENSE", "LICENSING.md"):
            source = source_root / name
            if source.is_file():
                shutil.copy2(source, app_stage / name)
        (app_stage / MARKER).write_text("skill-field-lab owned install\n", encoding="utf-8")
        (app_stage / "launcher.py").write_text(
            """from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fieldlab.cli import main

raise SystemExit(main())
""",
            encoding="utf-8",
        )
        version = (source_root / "VERSION").read_text(encoding="utf-8").strip()
        receipt = {
            "schema_version": 2,
            "installed_at": datetime.now(timezone.utc).isoformat(),
            "version": version,
            "source": {
                "git_head": _git_head(source_root),
                "fieldlab_source_sha256": _python_source_digest(source_root / "fieldlab"),
                "controllers": {
                    name: {"tree_sha256": digest}
                    for name, digest in controller_digests.items()
                },
                "schemas_tree_sha256": _tree_digest(source_root / "schemas"),
                "templates_tree_sha256": _tree_digest(source_root / "templates"),
            },
            "installation": {
                "app_dir": str(app_dir),
                "launcher": str(launcher),
                "skills_dir": None if args.cli_only else str(skills_dir),
                "cli_only": bool(args.cli_only),
                "backup": str(backup_root) if backup_created else None,
            },
        }
        _write_json(app_stage / "installation-receipt.json", receipt)

        launcher_fd, launcher_raw = tempfile.mkstemp(
            prefix=".fieldlab-launcher-stage-",
            dir=bin_dir,
            text=True,
        )
        os.close(launcher_fd)
        launcher_stage = Path(launcher_raw)
        stages.append(launcher_stage)
        launcher_stage.write_text(
            f"#!/bin/sh\nexec python3 {shlex.quote(str(app_dir / 'launcher.py'))} \"$@\"\n",
            encoding="utf-8",
        )
        launcher_stage.chmod(
            launcher_stage.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
        )

        staged_targets: list[tuple[Path, Path]] = [(app_stage, app_dir), (launcher_stage, launcher)]
        for name, target in controller_targets.items():
            skill_stage = Path(
                tempfile.mkdtemp(prefix=f".fieldlab-{name}-stage-", dir=skills_dir)
            )
            stages.append(skill_stage)
            _copy_source_tree(controller_sources[name], skill_stage)
            staged_targets.append((skill_stage, target))
        _commit_transaction(staged_targets)
    except BaseException:
        for stage in stages:
            _remove_path(stage)
        raise

    print(f"installed Field Lab app -> {app_dir}")
    print(f"installed launcher -> {launcher}")
    if args.cli_only:
        print("controller Skills unchanged (--cli-only)")
    else:
        for name, target in controller_targets.items():
            print(f"installed {name} -> {target}")
    if backup_created:
        print(f"recoverable backup -> {backup_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

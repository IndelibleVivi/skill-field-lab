#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import shutil
import shlex
import stat
import tempfile
from pathlib import Path


MARKER = ".skill-field-lab-install"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Install the dependency-free Field Lab CLI without a Python build backend."
    )
    parser.add_argument(
        "--app-dir",
        type=Path,
        default=Path(os.environ.get("FIELDLAB_HOME", "~/.local/share/skill-field-lab")),
        help="Private application directory (default: FIELDLAB_HOME or ~/.local/share/skill-field-lab)",
    )
    parser.add_argument(
        "--bin-dir",
        type=Path,
        default=Path(os.environ.get("FIELDLAB_BIN_DIR", "~/.local/bin")),
        help="Directory for the fieldlab launcher (default: FIELDLAB_BIN_DIR or ~/.local/bin)",
    )
    parser.add_argument("--replace", action="store_true", help="Replace an existing Field Lab install")
    return parser


def _is_owned_install(path: Path) -> bool:
    return (path / MARKER).is_file()


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    source_root = Path(__file__).resolve().parent.parent
    source_package = source_root / "fieldlab"
    app_dir = args.app_dir.expanduser().resolve()
    bin_dir = args.bin_dir.expanduser().resolve()
    launcher = bin_dir / "fieldlab"

    if app_dir.exists():
        if not args.replace:
            raise SystemExit(f"refusing to overwrite existing app directory: {app_dir}")
        if not _is_owned_install(app_dir):
            raise SystemExit(f"refusing to replace unrecognized directory: {app_dir}")
    if launcher.exists() and not args.replace:
        raise SystemExit(f"refusing to overwrite existing launcher: {launcher}")

    app_dir.parent.mkdir(parents=True, exist_ok=True)
    bin_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="fieldlab-install-", dir=app_dir.parent) as raw:
        staging = Path(raw) / app_dir.name
        shutil.copytree(
            source_package,
            staging / "fieldlab",
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
        (staging / MARKER).write_text("skill-field-lab local install\n", encoding="utf-8")
        (staging / "launcher.py").write_text(
            """from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fieldlab.cli import main

raise SystemExit(main())
""",
            encoding="utf-8",
        )
        if app_dir.exists():
            shutil.rmtree(app_dir)
        os.replace(staging, app_dir)

    launcher_text = f'''#!/bin/sh
exec python3 {shlex.quote(str(app_dir / "launcher.py"))} "$@"
'''
    temporary_launcher = launcher.with_name(f".{launcher.name}.tmp")
    temporary_launcher.write_text(launcher_text, encoding="utf-8")
    temporary_launcher.chmod(
        temporary_launcher.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
    )
    os.replace(temporary_launcher, launcher)
    print(f"installed Field Lab app -> {app_dir}")
    print(f"installed launcher -> {launcher}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
from __future__ import annotations

import compileall
import subprocess
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    forbidden = (
        root / "scripts" / "install_cli.py",
        root / "scripts" / "install_skills.py",
        root / "softpowers-companion",
        root / "examples" / "demo" / "fieldlab-pack.json",
        root / "examples" / "legal-research" / "fieldlab-pack.json",
    )
    present = [str(path.relative_to(root)) for path in forbidden if path.exists()]
    if present:
        raise SystemExit(f"superseded v0.1 surfaces remain: {present}")
    if not compileall.compile_dir(root / "fieldlab", quiet=1):
        raise SystemExit("Python compilation failed")
    for manifest in (
        root / "examples" / "demo" / "fieldlab.json",
        root / "examples" / "legal-research" / "fieldlab.json",
    ):
        subprocess.run(
            [sys.executable, "-m", "fieldlab", "validate", str(manifest)],
            cwd=root,
            check=True,
        )
        subprocess.run(
            [sys.executable, "-m", "fieldlab", "selftest", str(manifest)],
            cwd=root,
            check=True,
        )
    subprocess.run(
        [
            sys.executable,
            "-m",
            "unittest",
            "discover",
            "-s",
            "tests",
            "-p",
            "test*.py",
            "-v",
        ],
        cwd=root,
        check=True,
    )
    print("Bundle check passed. Target-agent invocations: 0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

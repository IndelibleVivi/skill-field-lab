#!/usr/bin/env python3
from __future__ import annotations

import compileall
import subprocess
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    if not compileall.compile_dir(root / "fieldlab", quiet=1):
        raise SystemExit("Python compilation failed")
    for pack in (
        root / "examples" / "demo" / "fieldlab-pack.json",
        root / "examples" / "legal-research" / "fieldlab-pack.json",
    ):
        subprocess.run(
            [sys.executable, "-m", "fieldlab", "validate", str(pack)],
            cwd=root,
            check=True,
        )
        subprocess.run(
            [sys.executable, "-m", "fieldlab", "selftest-pack", str(pack)],
            cwd=root,
            check=True,
        )
    subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
        cwd=root,
        check=True,
    )
    print("Bundle check passed. Target-agent invocations: 0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

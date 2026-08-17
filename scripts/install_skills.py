#!/usr/bin/env python3
from __future__ import annotations

import os
import shutil
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    source = root / "skills"
    target = Path(
        os.environ.get("FIELDLAB_SKILLS_DIR", Path.home() / ".agents" / "skills")
    ).expanduser()
    target.mkdir(parents=True, exist_ok=True)
    for skill in sorted(source.iterdir()):
        if not skill.is_dir():
            continue
        destination = target / skill.name
        if destination.exists():
            raise SystemExit(f"refusing to overwrite existing skill: {destination}")
        shutil.copytree(skill, destination)
        print(f"installed {skill.name} -> {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

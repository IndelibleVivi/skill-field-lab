from __future__ import annotations

import os
import platform
import shutil
import sys
from pathlib import Path
from typing import Any

from . import __version__
from .io import python_source_digest, read_json, tree_digest


def default_skills_dir() -> Path:
    override = os.environ.get("FIELDLAB_SKILLS_DIR")
    if override:
        return Path(override).expanduser().resolve()
    codex_home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")).expanduser()
    return (codex_home / "skills").resolve()


def doctor_report(
    *,
    skills_dir: Path | None = None,
    codex_bin: str = "codex",
) -> dict[str, Any]:
    package_root = Path(__file__).resolve().parent.parent
    selected_skills = (skills_dir or default_skills_dir()).expanduser().resolve()
    source_skills = package_root / "skills"
    controllers: dict[str, Any] = {}
    for name in ("pattern-intake", "skill-eval"):
        source = source_skills / name
        installed = selected_skills / name
        source_digest = tree_digest(source) if source.is_dir() else None
        installed_digest = tree_digest(installed) if installed.is_dir() else None
        controllers[name] = {
            "source_sha256": source_digest,
            "installed_sha256": installed_digest,
            "installed": installed_digest is not None,
            "matches_source": source_digest is not None and source_digest == installed_digest,
        }
    marker = package_root / ".skill-field-lab-install"
    receipt_path = package_root / "installation-receipt.json"
    receipt = read_json(receipt_path) if receipt_path.is_file() else None
    source_digest = python_source_digest(Path(__file__).resolve().parent)
    receipt_matches_source = bool(
        receipt
        and receipt.get("version") == __version__
        and receipt.get("source", {}).get("fieldlab_source_sha256") == source_digest
    )
    python_supported = sys.version_info >= (3, 10)
    host_supported = os.name == "posix"
    git_path = shutil.which("git")
    codex_path = shutil.which(codex_bin)
    report = {
        "schema_version": 2,
        "fieldlab_version": __version__,
        "fieldlab_source_sha256": source_digest,
        "package_root": str(package_root),
        "recognized_install": marker.is_file(),
        "installation_receipt": receipt,
        "installation_receipt_matches_source": receipt_matches_source,
        "python": {
            "version": platform.python_version(),
            "supported": python_supported,
        },
        "git": {"path": git_path, "available": git_path is not None},
        "codex": {"requested": codex_bin, "path": codex_path, "available": codex_path is not None},
        "host": {"platform": platform.platform(), "posix_live_supported": host_supported},
        "skill_discovery_path": str(selected_skills),
        "controllers": controllers,
        "claims": {"target_agent_invocations": 0},
    }
    report["ok"] = bool(
        marker.is_file()
        and receipt_matches_source
        and python_supported
        and host_supported
        and git_path
        and codex_path
        and all(item["matches_source"] for item in controllers.values())
    )
    return report

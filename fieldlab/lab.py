from __future__ import annotations

import os
import re
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .contracts import load_cases, load_lab, require_id, safe_mount, validate_assertion
from .errors import ConfigError
from .io import atomic_write_json, read_json, safe_relative, sha256_file, tree_digest, utc_now
from .records import validate_record_tree
from .trees import copy_tree_source, validate_tree_symlinks


LAB_DIRECTORIES = (
    "candidates",
    "claims",
    "cases",
    "plans",
    "runs",
    "receipts",
    "reviews",
    "decisions",
    "snapshots",
)
PROMOTABLE_DIRECTORIES = (
    "candidates",
    "claims",
    "cases",
    "receipts",
    "reviews",
    "decisions",
)


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return require_id(slug, "lab id")


def initialize_lab(
    directory: Path,
    *,
    lab_id: str | None = None,
    description: str | None = None,
) -> Path:
    directory = directory.expanduser().resolve()
    if directory.exists() and not directory.is_dir():
        raise ConfigError(f"lab path is not a directory: {directory}")
    if directory.exists() and any(directory.iterdir()):
        raise ConfigError(f"refusing to initialize a non-empty directory: {directory}")
    resolved_id = require_id(lab_id, "lab id") if lab_id else _slug(directory.name)
    directory.mkdir(parents=True, exist_ok=True)
    for name in LAB_DIRECTORIES:
        (directory / name).mkdir()
    template_path = Path(__file__).resolve().parents[1] / "templates" / "lab" / "fieldlab.json"
    manifest = read_json(template_path)
    manifest["lab_id"] = resolved_id
    manifest["description"] = description or manifest["description"]
    manifest_path = directory / "fieldlab.json"
    atomic_write_json(manifest_path, manifest)
    return manifest_path


def promote_lab(
    *,
    source_lab: Path,
    destination: Path,
    records: list[str] | None = None,
) -> dict[str, Any]:
    source_lab = source_lab.expanduser().resolve()
    manifest_path = source_lab / "fieldlab.json"
    if not manifest_path.is_file():
        raise ConfigError(f"source lab has no fieldlab.json: {source_lab}")
    lab, lab_root, cases_root = load_lab(manifest_path)
    validate_record_tree(lab_root)
    load_cases(cases_root, allow_empty=True)
    destination = destination.expanduser().resolve()
    if destination == source_lab or source_lab in destination.parents:
        raise ConfigError("promotion destination must be outside the source lab")

    selected: list[Path] = []
    if records:
        for raw in records:
            relative = Path(raw)
            if relative.is_absolute() or ".." in relative.parts or not relative.parts:
                raise ConfigError(f"unsafe promotion record: {raw}")
            if relative.parts[0] not in PROMOTABLE_DIRECTORIES:
                raise ConfigError(f"record is not promotable: {raw}")
            path = source_lab / relative
            if not path.exists():
                raise ConfigError(f"promotion record does not exist: {path}")
            if path.is_dir():
                selected.extend(item for item in sorted(path.rglob("*")) if item.is_file())
            elif path.is_file():
                selected.append(path)
    else:
        for name in PROMOTABLE_DIRECTORIES:
            directory = source_lab / name
            if directory.is_dir():
                validate_tree_symlinks(directory, f"promotion source {name}")
                selected.extend(item for item in sorted(directory.rglob("*")) if item.is_file())

    selected = sorted(set(selected))
    targets = [(source, destination / source.relative_to(source_lab)) for source in selected]
    collisions = [target for _, target in targets if target.exists()]
    if collisions:
        raise ConfigError(f"promotion refuses destination collisions: {collisions[:5]}")
    for source, target in targets:
        if source.is_symlink():
            raise ConfigError(f"promotion refuses symlink record: {source}")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)

    receipt = {
        "schema_version": 2,
        "receipt_type": "promotion",
        "created_at": utc_now(),
        "lab_id": lab["lab_id"],
        "source_lab": str(source_lab),
        "destination": str(destination),
        "files": [
            {
                "source": source.relative_to(source_lab).as_posix(),
                "destination": target.relative_to(destination).as_posix(),
                "sha256": sha256_file(target),
            }
            for source, target in targets
        ],
        "claims": {
            "fieldlab_runtime_promoted": False,
            "manifest_promoted": False,
            "plans_or_runs_promoted": False,
            "target_agent_invocations": 0,
        },
    }
    receipt_path = source_lab / "receipts" / f"promotion-{_stamp()}.json"
    atomic_write_json(receipt_path, receipt)
    return {"receipt_path": str(receipt_path), **receipt}


def _load_v1_pack_for_migration(pack_path: Path) -> tuple[dict[str, Any], Path, Path]:
    """Read the legacy format only for the explicit one-shot migration command."""

    pack_path = pack_path.expanduser().resolve()
    pack_root = pack_path.parent
    pack = read_json(pack_path)
    required = {"schema_version", "pack_id", "description", "cases_root", "subjects", "defaults"}
    allowed = required | {"metadata"}
    missing = required - set(pack)
    extra = set(pack) - allowed
    if missing or extra:
        raise ConfigError(
            f"{pack_path}: v1 fields mismatch; missing={sorted(missing)}, extra={sorted(extra)}"
        )
    if pack.get("schema_version") != 1:
        raise ConfigError(f"{pack_path}: migrate-v1 requires schema_version 1")
    require_id(pack.get("pack_id"), f"{pack_path}: pack_id")
    if not isinstance(pack.get("description"), str) or not pack["description"].strip():
        raise ConfigError(f"{pack_path}: description must be non-empty")
    if not isinstance(pack.get("cases_root"), str):
        raise ConfigError(f"{pack_path}: cases_root must be a string")
    cases_root = safe_relative(pack_root, pack["cases_root"])
    if not cases_root.is_dir():
        raise ConfigError(f"{pack_path}: cases_root does not exist: {cases_root}")

    defaults = pack.get("defaults")
    expected_defaults = {
        "adapter", "approval_policy", "network_access", "output_root", "keep_workspace"
    }
    if not isinstance(defaults, dict) or set(defaults) != expected_defaults:
        raise ConfigError(f"{pack_path}: v1 defaults require exactly {sorted(expected_defaults)}")
    if defaults.get("adapter") != "codex-exec":
        raise ConfigError(f"{pack_path}: unsupported v1 adapter")
    if defaults.get("approval_policy") not in {"untrusted", "on-request", "never"}:
        raise ConfigError(f"{pack_path}: invalid v1 approval_policy")
    if not isinstance(defaults.get("network_access"), bool):
        raise ConfigError(f"{pack_path}: v1 network_access must be boolean")
    if not isinstance(defaults.get("output_root"), str):
        raise ConfigError(f"{pack_path}: v1 output_root must be a string")
    if not isinstance(defaults.get("keep_workspace"), bool):
        raise ConfigError(f"{pack_path}: v1 keep_workspace must be boolean")

    subjects = pack.get("subjects")
    if not isinstance(subjects, dict) or not subjects:
        raise ConfigError(f"{pack_path}: subjects must be a non-empty object")
    for subject_id, subject in subjects.items():
        require_id(subject_id, "v1 subject id")
        if not isinstance(subject, dict):
            raise ConfigError(f"v1 subject {subject_id}: definition must be an object")
        allowed_subject = {"label", "attribution", "overlays", "notes"}
        if set(subject) - allowed_subject:
            raise ConfigError(f"v1 subject {subject_id}: unknown fields")
        if not isinstance(subject.get("label"), str) or not subject["label"].strip():
            raise ConfigError(f"v1 subject {subject_id}: label must be non-empty")
        if subject.get("attribution") not in {"ambient", "repo_scoped"}:
            raise ConfigError(f"v1 subject {subject_id}: unsupported attribution")
        overlays = subject.get("overlays", [])
        if not isinstance(overlays, list):
            raise ConfigError(f"v1 subject {subject_id}: overlays must be a list")
        if subject["attribution"] == "repo_scoped" and not overlays:
            raise ConfigError(f"v1 subject {subject_id}: repo_scoped requires overlays")
        for index, overlay in enumerate(overlays):
            if not isinstance(overlay, dict) or set(overlay) != {"source", "target"}:
                raise ConfigError(f"v1 subject {subject_id}: overlay {index} is invalid")
            if not all(isinstance(overlay.get(key), str) for key in ("source", "target")):
                raise ConfigError(f"v1 subject {subject_id}: overlay paths must be strings")
            source = safe_relative(pack_root, overlay["source"])
            if not source.exists():
                raise ConfigError(f"v1 subject {subject_id}: overlay source missing: {source}")
            safe_mount(Path("/workspace"), overlay["target"])
    return pack, pack_root, cases_root


def _migrate_v1_case(case_dir: Path) -> dict[str, Any]:
    case_path = case_dir / "case.json"
    case = read_json(case_path)
    required = {
        "schema_version", "case_id", "description", "prompt_file", "sandbox",
        "timeout_seconds", "assertions",
    }
    optional = {"trace_assertions", "tags", "claim_ids"}
    missing = required - set(case)
    extra = set(case) - required - optional
    if missing or extra:
        raise ConfigError(
            f"{case_path}: v1 case fields mismatch; missing={sorted(missing)}, extra={sorted(extra)}"
        )
    if case.get("schema_version") != 1:
        raise ConfigError(f"{case_path}: migrate-v1 expects schema_version 1 cases")
    case_id = require_id(case.get("case_id"), f"{case_path}: case_id")
    if case_id != case_dir.name:
        raise ConfigError(f"{case_path}: case_id must match directory name")
    prompt_file = case.get("prompt_file")
    if not isinstance(prompt_file, str) or Path(prompt_file).name != prompt_file:
        raise ConfigError(f"{case_path}: prompt_file must be one filename")
    if not (case_dir / prompt_file).is_file():
        raise ConfigError(f"{case_path}: prompt file missing")
    assertions = case.get("assertions")
    if not isinstance(assertions, list) or not assertions:
        raise ConfigError(f"{case_path}: assertions must be non-empty")
    for index, assertion in enumerate(assertions):
        validate_assertion(assertion, f"{case_path}: assertions[{index}]")
    migrated: dict[str, Any] = {
        "schema_version": 2,
        "case_id": case_id,
        "description": case["description"],
        "prompt_file": prompt_file,
        "activation": "implicit",
        "sandbox": case["sandbox"],
        "timeout_seconds": case["timeout_seconds"],
        "workspace_assertions": [
            item for item in assertions if item.get("type") != "command"
        ],
        "command_assertions": [
            {key: value for key, value in item.items() if key != "type"}
            for item in assertions
            if item.get("type") == "command"
        ],
    }
    for key in ("trace_assertions", "tags", "claim_ids"):
        if key in case:
            migrated[key] = case[key]
    return migrated


def migrate_v1(pack_path: Path, output_path: Path) -> dict[str, Any]:
    pack_path = pack_path.expanduser().resolve()
    output_path = output_path.expanduser().resolve()
    if output_path.name != "fieldlab.json":
        raise ConfigError("migrate-v1 output must be named fieldlab.json")
    pack, pack_root, cases_root = _load_v1_pack_for_migration(pack_path)
    destination_root = output_path.parent
    if destination_root == pack_root:
        raise ConfigError("migrate-v1 output must use a separate lab directory")
    if destination_root.exists():
        raise ConfigError(f"migrate-v1 destination already exists: {destination_root}")
    destination_root.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(
        prefix="fieldlab-migrate-v1-",
        dir=destination_root.parent,
    ) as raw:
        staging = Path(raw) / destination_root.name
        for name in LAB_DIRECTORIES:
            (staging / name).mkdir(parents=True, exist_ok=True)
        validate_tree_symlinks(cases_root, "v1 cases")
        shutil.copytree(cases_root, staging / "cases", dirs_exist_ok=True, symlinks=True)
        for case_dir in sorted((staging / "cases").iterdir()):
            if case_dir.is_dir() and not case_dir.name.startswith("."):
                atomic_write_json(case_dir / "case.json", _migrate_v1_case(case_dir))

        migrated_subjects: dict[str, Any] = {}
        mappings: list[dict[str, Any]] = []
        for subject_id, subject in pack["subjects"].items():
            if subject["attribution"] == "ambient":
                migrated_subjects[subject_id] = {
                    "kind": "control",
                    "label": subject["label"],
                    "notes": (
                        "Migrated from a v1 ambient subject as an isolated control. "
                        "This is an explicit semantic change recorded in the migration receipt."
                    ),
                }
                mappings.append(
                    {
                        "subject_id": subject_id,
                        "v1_attribution": "ambient",
                        "v2_subject_scope": "isolated-control",
                        "semantic_change": True,
                    }
                )
                continue
            snapshot_root = staging / "subjects" / subject_id
            snapshot_root.mkdir(parents=True)
            overlay_mappings: list[dict[str, str]] = []
            for overlay in subject.get("overlays", []):
                source = (pack_root / overlay["source"]).resolve()
                target = safe_mount(snapshot_root, overlay["target"])
                copy_tree_source(source, target, "v1 subject overlay")
                overlay_mappings.append(
                    {
                        "source": overlay["source"],
                        "target": overlay["target"],
                        "sha256": tree_digest(source) if source.is_dir() else sha256_file(source),
                    }
                )
            migrated_subjects[subject_id] = {
                "kind": "agent-skill",
                "label": subject["label"],
                "source": {"type": "snapshot", "path": f"subjects/{subject_id}"},
                "mount": ".",
            }
            if subject.get("notes"):
                migrated_subjects[subject_id]["notes"] = subject["notes"]
            mappings.append(
                {
                    "subject_id": subject_id,
                    "v1_attribution": subject["attribution"],
                    "v2_subject_scope": "workspace-scoped",
                    "semantic_change": False,
                    "overlays": overlay_mappings,
                }
            )

        manifest = {
            "schema_version": 2,
            "lab_id": pack["pack_id"],
            "description": pack["description"],
            "subjects": migrated_subjects,
            "cases_root": "cases",
            "defaults": {
                **pack["defaults"],
                "output_root": "runs",
            },
            "metadata": {
                "migrated_from": str(pack_path),
                "source_schema_version": 1,
            },
        }
        staged_manifest = staging / output_path.name
        atomic_write_json(staged_manifest, manifest)
        migrated_lab, _, migrated_cases_root = load_lab(staged_manifest)
        if migrated_lab["lab_id"] != pack["pack_id"]:
            raise ConfigError("migrated lab identity does not match source pack")
        load_cases(migrated_cases_root)
        receipt = {
            "schema_version": 2,
            "receipt_type": "migration-v1",
            "created_at": utc_now(),
            "source_manifest": {
                "path": str(pack_path),
                "sha256": sha256_file(pack_path),
            },
            "output_manifest": {
                "path": str(output_path),
                "sha256": sha256_file(staged_manifest),
            },
            "subjects": mappings,
            "cases_tree_sha256": tree_digest(staging / "cases"),
            "claims": {
                "source_manifest_modified": False,
                "target_agent_invocations": 0,
            },
        }
        receipt_name = f"migration-v1-{_stamp()}.json"
        atomic_write_json(staging / "receipts" / receipt_name, receipt)
        os.replace(staging, destination_root)

    return {
        **receipt,
        "output_path": str(output_path),
        "receipt_path": str(destination_root / "receipts" / receipt_name),
    }

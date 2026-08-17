from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .errors import ConfigError
from .io import canonical_json, read_json, safe_relative, sha256_file, sha256_text, tree_digest

SCHEMA_VERSION = 1
ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
ASSERTION_TYPES = {
    "file_equals",
    "file_contains",
    "file_not_contains",
    "file_exists",
    "changed_files_exact",
    "command",
}
TRACE_ASSERTION_KEYS = {
    "max_command_executions",
    "max_plan_updates",
    "max_subagent_events",
    "reference_reads_include",
}
ATTRIBUTIONS = {"ambient", "repo_scoped", "hermetic"}
MODES = {"canary", "matched", "environment-smoke"}
EFFORTS = {"minimal", "low", "medium", "high", "xhigh"}
SANDBOXES = {"read-only", "workspace-write"}
APPROVAL_POLICIES = {"untrusted", "on-request", "never"}


def require_id(value: object, label: str) -> str:
    if not isinstance(value, str) or not ID_RE.fullmatch(value):
        raise ConfigError(f"{label} must use lowercase letters, digits, and hyphens")
    return value


def validate_assertion(assertion: object, label: str) -> None:
    if not isinstance(assertion, dict):
        raise ConfigError(f"{label}: assertion must be an object")
    assertion_type = assertion.get("type")
    if assertion_type not in ASSERTION_TYPES:
        raise ConfigError(f"{label}: unsupported assertion type {assertion_type!r}")

    if assertion_type in {"file_equals", "file_contains", "file_not_contains"}:
        expected = {"type", "path", "value"}
        if set(assertion) != expected:
            raise ConfigError(f"{label}: {assertion_type} requires exactly {sorted(expected)}")
        if not isinstance(assertion["path"], str) or not isinstance(assertion["value"], str):
            raise ConfigError(f"{label}: path and value must be strings")
        safe_relative(Path("/case-root"), assertion["path"])
        return

    if assertion_type == "file_exists":
        if set(assertion) != {"type", "path"} or not isinstance(assertion.get("path"), str):
            raise ConfigError(f"{label}: file_exists requires a string path")
        safe_relative(Path("/case-root"), assertion["path"])
        return

    if assertion_type == "changed_files_exact":
        if set(assertion) != {"type", "paths"}:
            raise ConfigError(f"{label}: changed_files_exact requires paths")
        paths = assertion.get("paths")
        if not isinstance(paths, list) or not all(isinstance(item, str) for item in paths):
            raise ConfigError(f"{label}: changed paths must be strings")
        if len(paths) != len(set(paths)):
            raise ConfigError(f"{label}: changed paths must be unique")
        for path in paths:
            safe_relative(Path("/case-root"), path)
        return

    allowed = {"type", "argv", "exit_code", "timeout_seconds"}
    if set(assertion) - allowed:
        raise ConfigError(f"{label}: command has unknown fields")
    argv = assertion.get("argv")
    if not isinstance(argv, list) or not argv or not all(isinstance(item, str) for item in argv):
        raise ConfigError(f"{label}: command requires a non-empty string argv")
    if not isinstance(assertion.get("exit_code", 0), int):
        raise ConfigError(f"{label}: command exit_code must be an integer")
    timeout = assertion.get("timeout_seconds", 30)
    if not isinstance(timeout, int) or not 1 <= timeout <= 300:
        raise ConfigError(f"{label}: command timeout_seconds must be 1..300")


def load_case(case_dir: Path) -> dict[str, Any]:
    case_path = case_dir / "case.json"
    case = read_json(case_path)
    required = {
        "schema_version",
        "case_id",
        "description",
        "prompt_file",
        "sandbox",
        "timeout_seconds",
        "assertions",
    }
    allowed = required | {"trace_assertions", "tags", "claim_ids"}
    missing = required - set(case)
    extra = set(case) - allowed
    if missing or extra:
        raise ConfigError(
            f"{case_path}: fields mismatch; missing={sorted(missing)}, extra={sorted(extra)}"
        )
    if case["schema_version"] != SCHEMA_VERSION:
        raise ConfigError(f"{case_path}: unsupported schema_version")
    case_id = require_id(case.get("case_id"), f"{case_path}: case_id")
    if case_id != case_dir.name:
        raise ConfigError(f"{case_path}: case_id must match directory name")
    if not isinstance(case.get("description"), str) or not case["description"].strip():
        raise ConfigError(f"{case_path}: description must be non-empty")
    prompt_file = case.get("prompt_file")
    if not isinstance(prompt_file, str) or Path(prompt_file).name != prompt_file:
        raise ConfigError(f"{case_path}: prompt_file must be one filename")
    if not (case_dir / prompt_file).is_file():
        raise ConfigError(f"{case_path}: prompt file missing")
    if not (case_dir / "fixture").is_dir():
        raise ConfigError(f"{case_path}: fixture/ is required")
    if case.get("sandbox") not in SANDBOXES:
        raise ConfigError(f"{case_path}: unsupported sandbox")
    timeout = case.get("timeout_seconds")
    if not isinstance(timeout, int) or not 1 <= timeout <= 3600:
        raise ConfigError(f"{case_path}: timeout_seconds must be 1..3600")
    assertions = case.get("assertions")
    if not isinstance(assertions, list) or not assertions:
        raise ConfigError(f"{case_path}: assertions must be non-empty")
    for index, assertion in enumerate(assertions):
        validate_assertion(assertion, f"{case_path}: assertions[{index}]")

    trace = case.get("trace_assertions", {})
    if not isinstance(trace, dict) or set(trace) - TRACE_ASSERTION_KEYS:
        raise ConfigError(f"{case_path}: invalid trace_assertions")
    for key in ("max_command_executions", "max_plan_updates", "max_subagent_events"):
        value = trace.get(key)
        if value is not None and (not isinstance(value, int) or value < 0):
            raise ConfigError(f"{case_path}: {key} must be a non-negative integer")
    references = trace.get("reference_reads_include", [])
    if not isinstance(references, list) or not all(isinstance(item, str) and item for item in references):
        raise ConfigError(f"{case_path}: reference_reads_include must be strings")
    for key in ("tags", "claim_ids"):
        values = case.get(key, [])
        if not isinstance(values, list) or not all(isinstance(item, str) and item for item in values):
            raise ConfigError(f"{case_path}: {key} must be strings")
    return case


def validate_subject(subject_id: str, subject: object, pack_dir: Path) -> dict[str, Any]:
    require_id(subject_id, "subject id")
    if not isinstance(subject, dict):
        raise ConfigError(f"subject {subject_id}: definition must be an object")
    allowed = {"label", "attribution", "overlays", "notes"}
    if set(subject) - allowed:
        raise ConfigError(f"subject {subject_id}: unknown fields {sorted(set(subject) - allowed)}")
    label = subject.get("label")
    if not isinstance(label, str) or not label.strip():
        raise ConfigError(f"subject {subject_id}: label must be non-empty")
    attribution = subject.get("attribution")
    if attribution not in ATTRIBUTIONS:
        raise ConfigError(f"subject {subject_id}: invalid attribution")
    overlays = subject.get("overlays", [])
    if not isinstance(overlays, list):
        raise ConfigError(f"subject {subject_id}: overlays must be a list")
    for index, overlay in enumerate(overlays):
        if not isinstance(overlay, dict) or set(overlay) != {"source", "target"}:
            raise ConfigError(f"subject {subject_id}: overlays[{index}] requires source and target")
        source = overlay.get("source")
        target = overlay.get("target")
        if not isinstance(source, str) or not isinstance(target, str):
            raise ConfigError(f"subject {subject_id}: overlay source and target must be strings")
        safe_relative(pack_dir, source)
        safe_relative(Path("/workspace"), target)
    if attribution == "repo_scoped" and not overlays:
        raise ConfigError(f"subject {subject_id}: repo_scoped subjects require an overlay")
    if attribution == "hermetic":
        raise ConfigError(
            f"subject {subject_id}: hermetic attribution is reserved; the v0.1 Codex adapter "
            "can establish repo_scoped evidence only"
        )
    return subject


def load_pack(pack_path: Path, *, require_overlay_sources: bool = True) -> tuple[dict[str, Any], Path, Path]:
    pack_path = pack_path.expanduser().resolve()
    pack_dir = pack_path.parent
    pack = read_json(pack_path)
    required = {"schema_version", "pack_id", "description", "cases_root", "subjects", "defaults"}
    allowed = required | {"metadata"}
    missing = required - set(pack)
    extra = set(pack) - allowed
    if missing or extra:
        raise ConfigError(
            f"{pack_path}: fields mismatch; missing={sorted(missing)}, extra={sorted(extra)}"
        )
    if pack["schema_version"] != SCHEMA_VERSION:
        raise ConfigError(f"{pack_path}: unsupported schema_version")
    require_id(pack.get("pack_id"), f"{pack_path}: pack_id")
    if not isinstance(pack.get("description"), str) or not pack["description"].strip():
        raise ConfigError(f"{pack_path}: description must be non-empty")
    cases_root_text = pack.get("cases_root")
    if not isinstance(cases_root_text, str):
        raise ConfigError(f"{pack_path}: cases_root must be a string")
    cases_root = safe_relative(pack_dir, cases_root_text)
    if not cases_root.is_dir():
        raise ConfigError(f"{pack_path}: cases_root does not exist: {cases_root}")

    subjects = pack.get("subjects")
    if not isinstance(subjects, dict) or not subjects:
        raise ConfigError(f"{pack_path}: subjects must be a non-empty object")
    for subject_id, subject in subjects.items():
        validate_subject(subject_id, subject, pack_dir)
        if require_overlay_sources:
            for overlay in subject.get("overlays", []):
                source = safe_relative(pack_dir, overlay["source"])
                if not source.exists():
                    raise ConfigError(f"subject {subject_id}: overlay source does not exist: {source}")

    defaults = pack.get("defaults")
    if not isinstance(defaults, dict):
        raise ConfigError(f"{pack_path}: defaults must be an object")
    expected_defaults = {
        "adapter",
        "approval_policy",
        "network_access",
        "output_root",
        "keep_workspace",
    }
    if set(defaults) != expected_defaults:
        raise ConfigError(
            f"{pack_path}: defaults require exactly {sorted(expected_defaults)}"
        )
    if defaults.get("adapter") != "codex-exec":
        raise ConfigError(f"{pack_path}: v0.1 supports adapter codex-exec only")
    if defaults.get("approval_policy") not in APPROVAL_POLICIES:
        raise ConfigError(f"{pack_path}: invalid approval_policy")
    if not isinstance(defaults.get("network_access"), bool):
        raise ConfigError(f"{pack_path}: network_access must be boolean")
    if not isinstance(defaults.get("output_root"), str):
        raise ConfigError(f"{pack_path}: output_root must be a string")
    safe_relative(pack_dir, defaults["output_root"])
    if not isinstance(defaults.get("keep_workspace"), bool):
        raise ConfigError(f"{pack_path}: keep_workspace must be boolean")
    return pack, pack_dir, cases_root


def load_cases(cases_root: Path) -> dict[str, tuple[Path, dict[str, Any]]]:
    cases: dict[str, tuple[Path, dict[str, Any]]] = {}
    for case_dir in sorted(cases_root.iterdir()):
        if not case_dir.is_dir() or case_dir.name.startswith("."):
            continue
        case = load_case(case_dir)
        cases[case["case_id"]] = (case_dir, case)
    if not cases:
        raise ConfigError(f"no cases found in {cases_root}")
    return cases


def case_identity(case_dir: Path, case: dict[str, Any]) -> dict[str, str]:
    prompt = (case_dir / case["prompt_file"]).read_text(encoding="utf-8").strip()
    return {
        "case_sha256": sha256_text(canonical_json(case)),
        "fixture_tree_sha256": tree_digest(case_dir / "fixture"),
        "prompt_sha256": sha256_text(prompt),
    }


def subject_identity(subject: dict[str, Any], pack_dir: Path) -> dict[str, Any]:
    overlays: list[dict[str, str]] = []
    for overlay in subject.get("overlays", []):
        source = safe_relative(pack_dir, overlay["source"])
        digest = tree_digest(source) if source.is_dir() else sha256_file(source)
        overlays.append({"target": overlay["target"], "sha256": digest})
    return {
        "attribution": subject["attribution"],
        "overlays": overlays,
    }

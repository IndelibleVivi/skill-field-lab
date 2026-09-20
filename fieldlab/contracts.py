from __future__ import annotations

import copy
import re
from pathlib import Path, PurePosixPath
from typing import Any

from .errors import ConfigError
from .io import canonical_json, read_json, safe_relative, sha256_text, tree_digest
from .review_material import validate_declared_material


V2_SCHEMA_VERSION = 2
SCHEMA_VERSION = V2_SCHEMA_VERSION
ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
WORKSPACE_ASSERTION_TYPES = {
    "file_equals", "file_contains", "file_not_contains", "file_exists",
    "changed_files_exact",
}
ASSERTION_TYPES = WORKSPACE_ASSERTION_TYPES | {"command"}
TRACE_ASSERTION_KEYS = {
    "max_command_executions", "max_plan_updates", "max_subagent_events",
    "reference_reads_include", "command_reference_mentions_include",
}
RESULT_ASSERTION_KEYS = {
    "text_contains", "text_not_contains", "text_matches", "json_schema",
}
SOURCE_TYPES = {"local-path", "local-git-ref", "snapshot"}
ACTIVATIONS = {"implicit", "explicit", "direct"}
MODES = {"canary", "matched"}
EFFORTS = {"minimal", "low", "medium", "high", "xhigh"}
SANDBOXES = {"read-only", "workspace-write"}
APPROVAL_POLICIES = {"untrusted", "on-request", "never"}


def require_id(value: object, label: str) -> str:
    if not isinstance(value, str) or not ID_RE.fullmatch(value):
        raise ConfigError(f"{label} must use lowercase letters, digits, and hyphens")
    return value


def resolve_local_path(root: Path, raw_path: str) -> Path:
    path = Path(raw_path).expanduser()
    if not path.is_absolute():
        path = root / path
    return path.resolve()


def safe_mount(workspace: Path, raw_mount: str) -> Path:
    if raw_mount == ".":
        return workspace.resolve()
    return safe_relative(workspace, raw_mount)


def _require_nonempty_text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"{label} must be non-empty")
    return value


def _validate_string_list(value: object, label: str, *, allow_empty: bool = True) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        raise ConfigError(f"{label} must be strings")
    if not allow_empty and not value:
        raise ConfigError(f"{label} must not be empty")
    if len(value) != len(set(value)):
        raise ConfigError(f"{label} must be unique")
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


def _validate_trace_assertions(trace: object, label: str) -> dict[str, Any]:
    if not isinstance(trace, dict) or set(trace) - TRACE_ASSERTION_KEYS:
        raise ConfigError(f"{label}: invalid trace_assertions")
    for key in ("max_command_executions", "max_plan_updates", "max_subagent_events"):
        value = trace.get(key)
        if value is not None and (not isinstance(value, int) or value < 0):
            raise ConfigError(f"{label}: {key} must be a non-negative integer")
    _validate_string_list(trace.get("reference_reads_include", []), f"{label}: reference_reads_include")
    _validate_string_list(
        trace.get("command_reference_mentions_include", []),
        f"{label}: command_reference_mentions_include",
    )
    return trace


def _validate_result_assertions(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) - RESULT_ASSERTION_KEYS:
        raise ConfigError(f"{label}: invalid result_assertions")
    for key in ("text_contains", "text_not_contains", "text_matches"):
        values = _validate_string_list(value.get(key, []), f"{label}: {key}")
        if key == "text_matches":
            for pattern in values:
                try:
                    re.compile(pattern)
                except re.error as exc:
                    raise ConfigError(f"{label}: invalid regular expression {pattern!r}: {exc}") from exc
    schema = value.get("json_schema")
    if schema is not None and not isinstance(schema, dict):
        raise ConfigError(f"{label}: json_schema must be an object")
    return value


def _load_case_v2(case_dir: Path, case: dict[str, Any], case_path: Path) -> dict[str, Any]:
    required = {
        "schema_version", "case_id", "description", "prompt_file", "activation",
        "sandbox", "timeout_seconds",
    }
    optional = {
        "result_assertions", "workspace_assertions", "command_assertions",
        "trace_assertions", "human_review_requirements", "tags", "claim_ids",
        "human_review_material",
    }
    missing = required - set(case)
    extra = set(case) - required - optional
    if missing or extra:
        raise ConfigError(f"{case_path}: fields mismatch; missing={sorted(missing)}, extra={sorted(extra)}")
    case_id = require_id(case.get("case_id"), f"{case_path}: case_id")
    if case_id != case_dir.name:
        raise ConfigError(f"{case_path}: case_id must match directory name")
    _require_nonempty_text(case.get("description"), f"{case_path}: description")
    prompt_file = case.get("prompt_file")
    if not isinstance(prompt_file, str) or Path(prompt_file).name != prompt_file:
        raise ConfigError(f"{case_path}: prompt_file must be one filename")
    if not (case_dir / prompt_file).is_file():
        raise ConfigError(f"{case_path}: prompt file missing")
    if case.get("activation") not in ACTIVATIONS:
        raise ConfigError(f"{case_path}: unsupported activation")
    if case.get("sandbox") not in SANDBOXES:
        raise ConfigError(f"{case_path}: unsupported sandbox")
    timeout = case.get("timeout_seconds")
    if not isinstance(timeout, int) or not 1 <= timeout <= 3600:
        raise ConfigError(f"{case_path}: timeout_seconds must be 1..3600")

    result_assertions = _validate_result_assertions(case.get("result_assertions", {}), str(case_path))
    workspace_assertions = case.get("workspace_assertions", [])
    if not isinstance(workspace_assertions, list):
        raise ConfigError(f"{case_path}: workspace_assertions must be a list")
    for index, assertion in enumerate(workspace_assertions):
        validate_assertion(assertion, f"{case_path}: workspace_assertions[{index}]")
        if assertion.get("type") == "command":
            raise ConfigError(f"{case_path}: command belongs in command_assertions")
    command_assertions = case.get("command_assertions", [])
    if not isinstance(command_assertions, list):
        raise ConfigError(f"{case_path}: command_assertions must be a list")
    normalized_commands: list[dict[str, Any]] = []
    for index, assertion in enumerate(command_assertions):
        if not isinstance(assertion, dict):
            raise ConfigError(f"{case_path}: command_assertions[{index}] must be an object")
        normalized = {"type": "command", **assertion}
        validate_assertion(normalized, f"{case_path}: command_assertions[{index}]")
        normalized_commands.append(normalized)
    trace = _validate_trace_assertions(case.get("trace_assertions", {}), str(case_path))
    human = _validate_string_list(
        case.get("human_review_requirements", []),
        f"{case_path}: human_review_requirements",
    )
    review_material: list[str] | None = None
    if "human_review_material" in case:
        if not human:
            raise ConfigError(
                f"{case_path}: human_review_material requires human_review_requirements"
            )
        review_material = validate_declared_material(
            case["human_review_material"],
            f"{case_path}: human_review_material",
        )
    for key in ("tags", "claim_ids"):
        _validate_string_list(case.get(key, []), f"{case_path}: {key}")
    has_result = any(result_assertions.get(key) for key in RESULT_ASSERTION_KEYS)
    if not (has_result or workspace_assertions or normalized_commands or trace or human):
        raise ConfigError(f"{case_path}: case requires an assertion or human review requirement")

    normalized_case = copy.deepcopy(case)
    normalized_case.update({
        "source_schema_version": 2,
        "result_assertions": result_assertions,
        "workspace_assertions": workspace_assertions,
        "command_assertions": normalized_commands,
        "trace_assertions": trace,
        "human_review_requirements": human,
        "tags": list(case.get("tags", [])),
        "claim_ids": list(case.get("claim_ids", [])),
    })
    if review_material is not None:
        normalized_case["human_review_material"] = review_material
    return normalized_case


def load_case(case_dir: Path) -> dict[str, Any]:
    case_path = case_dir / "case.json"
    case = read_json(case_path)
    if case.get("schema_version") != 2:
        raise ConfigError(
            f"{case_path}: active labs require schema_version 2; "
            "migrate legacy packs with fieldlab migrate-v1"
        )
    return _load_case_v2(case_dir, case, case_path)


def _validate_v2_subject(
    subject_id: str,
    subject: object,
    lab_root: Path,
    *,
    require_source: bool,
) -> dict[str, Any]:
    require_id(subject_id, "subject id")
    if not isinstance(subject, dict):
        raise ConfigError(f"subject {subject_id}: definition must be an object")
    kind = subject.get("kind")
    scope = subject.get("subject_scope")
    if scope == "hermetic":
        raise ConfigError(f"subject {subject_id}: hermetic subject_scope remains reserved")
    if kind == "control":
        allowed = {"kind", "label", "notes", "subject_scope"}
        if set(subject) - allowed:
            raise ConfigError(f"subject {subject_id}: control has unknown fields")
        if scope is not None and scope != "isolated-control":
            raise ConfigError(f"subject {subject_id}: control scope must be isolated-control")
        return subject
    if kind != "agent-skill":
        raise ConfigError(f"subject {subject_id}: kind must be agent-skill or control")
    allowed = {"kind", "label", "notes", "source", "mount", "subject_scope"}
    if set(subject) - allowed:
        raise ConfigError(f"subject {subject_id}: unknown fields {sorted(set(subject) - allowed)}")
    if scope is not None and scope != "workspace-scoped":
        raise ConfigError(f"subject {subject_id}: agent-skill scope must be workspace-scoped")
    mount = subject.get("mount", f".agents/skills/{subject_id}")
    if not isinstance(mount, str):
        raise ConfigError(f"subject {subject_id}: mount must be a string")
    safe_mount(Path("/workspace"), mount)
    source = subject.get("source")
    if not isinstance(source, dict):
        raise ConfigError(f"subject {subject_id}: source must be an object")
    source_type = source.get("type")
    if source_type not in SOURCE_TYPES:
        raise ConfigError(f"subject {subject_id}: unsupported source type {source_type!r}")
    if source_type == "local-path":
        if set(source) != {"type", "path"} or not isinstance(source.get("path"), str):
            raise ConfigError(f"subject {subject_id}: local-path requires path")
        path = resolve_local_path(lab_root, source["path"])
        if require_source and not path.is_dir():
            raise ConfigError(f"subject {subject_id}: local-path source does not exist: {path}")
    elif source_type == "snapshot":
        if set(source) != {"type", "path"} or not isinstance(source.get("path"), str):
            raise ConfigError(f"subject {subject_id}: snapshot requires path")
        try:
            path = safe_relative(lab_root, source["path"])
        except ConfigError as exc:
            raise ConfigError(f"subject {subject_id}: snapshot must stay inside the lab") from exc
        if require_source and not path.is_dir():
            raise ConfigError(f"subject {subject_id}: snapshot source does not exist: {path}")
    else:
        expected = {"type", "repo", "ref", "subpath"}
        if set(source) != expected or not all(isinstance(source.get(key), str) for key in expected):
            raise ConfigError(f"subject {subject_id}: local-git-ref requires repo, ref, and subpath")
        repo = resolve_local_path(lab_root, source["repo"])
        if require_source and not ((repo / ".git").is_dir() or (repo / ".git").is_file()):
            raise ConfigError(f"subject {subject_id}: local-git-ref repo is not a Git worktree: {repo}")
        ref = source["ref"]
        if not ref or ref.startswith("-"):
            raise ConfigError(f"subject {subject_id}: ref must be a non-option Git revision")
        subpath = PurePosixPath(source["subpath"])
        if subpath.is_absolute() or not subpath.parts or ".." in subpath.parts:
            raise ConfigError(f"subject {subject_id}: subpath must be repository-relative")
    return subject


def _validate_defaults(defaults: object, manifest_path: Path) -> dict[str, Any]:
    if not isinstance(defaults, dict):
        raise ConfigError(f"{manifest_path}: defaults must be an object")
    expected = {"adapter", "approval_policy", "network_access", "output_root", "keep_workspace"}
    if set(defaults) != expected:
        raise ConfigError(f"{manifest_path}: defaults require exactly {sorted(expected)}")
    if defaults.get("adapter") != "codex-exec":
        raise ConfigError(f"{manifest_path}: v0.2 supports adapter codex-exec only")
    if defaults.get("approval_policy") not in APPROVAL_POLICIES:
        raise ConfigError(f"{manifest_path}: invalid approval_policy")
    if not isinstance(defaults.get("network_access"), bool):
        raise ConfigError(f"{manifest_path}: network_access must be boolean")
    if not isinstance(defaults.get("output_root"), str):
        raise ConfigError(f"{manifest_path}: output_root must be a string")
    safe_relative(manifest_path.parent, defaults["output_root"])
    if not isinstance(defaults.get("keep_workspace"), bool):
        raise ConfigError(f"{manifest_path}: keep_workspace must be boolean")
    return defaults


def load_lab(
    manifest_path: Path,
    *,
    require_subject_sources: bool = True,
) -> tuple[dict[str, Any], Path, Path]:
    manifest_path = manifest_path.expanduser().resolve()
    raw = read_json(manifest_path)
    if raw.get("schema_version") != 2:
        raise ConfigError(
            f"{manifest_path}: active labs require schema_version 2; "
            "migrate legacy packs with fieldlab migrate-v1"
        )
    required = {"schema_version", "lab_id", "description", "cases_root", "subjects", "defaults"}
    allowed = required | {"metadata"}
    missing = required - set(raw)
    extra = set(raw) - allowed
    if missing or extra:
        raise ConfigError(f"{manifest_path}: fields mismatch; missing={sorted(missing)}, extra={sorted(extra)}")
    require_id(raw.get("lab_id"), f"{manifest_path}: lab_id")
    _require_nonempty_text(raw.get("description"), f"{manifest_path}: description")
    cases_root_text = raw.get("cases_root")
    if not isinstance(cases_root_text, str):
        raise ConfigError(f"{manifest_path}: cases_root must be a string")
    cases_root = safe_relative(manifest_path.parent, cases_root_text)
    if not cases_root.is_dir():
        raise ConfigError(f"{manifest_path}: cases_root does not exist: {cases_root}")
    subjects = raw.get("subjects")
    if not isinstance(subjects, dict) or not subjects:
        raise ConfigError(f"{manifest_path}: subjects must be a non-empty object")
    for subject_id, subject in subjects.items():
        _validate_v2_subject(
            subject_id,
            subject,
            manifest_path.parent,
            require_source=require_subject_sources,
        )
    _validate_defaults(raw.get("defaults"), manifest_path)
    return copy.deepcopy(raw), manifest_path.parent, cases_root


def load_cases(
    cases_root: Path,
    *,
    allow_empty: bool = False,
) -> dict[str, tuple[Path, dict[str, Any]]]:
    cases: dict[str, tuple[Path, dict[str, Any]]] = {}
    for case_dir in sorted(cases_root.iterdir()):
        if not case_dir.is_dir() or case_dir.name.startswith("."):
            continue
        case = load_case(case_dir)
        cases[case["case_id"]] = (case_dir, case)
    if not cases and not allow_empty:
        raise ConfigError(f"no cases found in {cases_root}")
    return cases


def case_identity(case_dir: Path, case: dict[str, Any]) -> dict[str, Any]:
    prompt = (case_dir / case["prompt_file"]).read_text(encoding="utf-8").strip()
    fixture = case_dir / "fixture"
    return {
        "case_sha256": sha256_text(canonical_json(case)),
        "fixture_tree_sha256": tree_digest(fixture) if fixture.is_dir() else None,
        "prompt_sha256": sha256_text(prompt),
    }


def manifest_identity(manifest_path: Path) -> dict[str, Any]:
    manifest_path = manifest_path.expanduser().resolve()
    raw = read_json(manifest_path)
    return {
        "schema_version": raw.get("schema_version"),
        "sha256": sha256_text(canonical_json(raw)),
    }

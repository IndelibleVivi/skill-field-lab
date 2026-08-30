from __future__ import annotations

from pathlib import Path
from typing import Any

from .contracts import require_id
from .errors import ConfigError
from .io import read_json


DECISIONS = {"ADOPT", "ADAPT", "REJECT", "DEFER", "ALREADY COVERED"}
LANDING_PLANES = {"runtime", "eval-maintainer", "packaging", "docs-provenance"}
CLAIM_STATUSES = {"proposed", "planned", "observed", "verified", "rejected", "inconclusive"}


def _exact_fields(value: dict[str, Any], required: set[str], optional: set[str], label: str) -> None:
    missing = required - set(value)
    extra = set(value) - required - optional
    if missing or extra:
        raise ConfigError(f"{label}: fields mismatch; missing={sorted(missing)}, extra={sorted(extra)}")


def _text(value: object, label: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str) or (not allow_empty and not value.strip()):
        qualifier = "a string" if allow_empty else "a non-empty string"
        raise ConfigError(f"{label} must be {qualifier}")
    return value


def _text_list(value: object, label: str, *, allow_empty: bool = True) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
        raise ConfigError(f"{label} must be a list of non-empty strings")
    if not allow_empty and not value:
        raise ConfigError(f"{label} must not be empty")
    if len(value) != len(set(value)):
        raise ConfigError(f"{label} must contain unique values")
    return value


def _source(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ConfigError(f"{label} must be an object")
    source_type = value.get("type")
    if source_type not in {"local-path", "local-git-ref", "snapshot", "external-reference"}:
        raise ConfigError(f"{label}: unsupported source type {source_type!r}")
    for key, item in value.items():
        if not isinstance(key, str) or not isinstance(item, str) or not item.strip():
            raise ConfigError(f"{label}: source fields must be non-empty strings")
    return value


def validate_candidate(candidate: object, label: str = "candidate") -> dict[str, Any]:
    if not isinstance(candidate, dict):
        raise ConfigError(f"{label} must be an object")
    required = {
        "schema_version", "candidate_id", "source", "pin", "reviewed_files",
        "source_observations", "distilled_mechanism", "local_problem", "local_fit",
        "landing_plane", "open_questions",
    }
    _exact_fields(candidate, required, {"license_note", "review_date"}, label)
    if candidate.get("schema_version") != 2:
        raise ConfigError(f"{label}: schema_version must be 2")
    require_id(candidate.get("candidate_id"), f"{label}: candidate_id")
    _source(candidate.get("source"), f"{label}: source")
    _text(candidate.get("pin"), f"{label}: pin")
    _text_list(candidate.get("reviewed_files"), f"{label}: reviewed_files", allow_empty=False)
    _text_list(candidate.get("source_observations"), f"{label}: source_observations", allow_empty=False)
    _text(candidate.get("distilled_mechanism"), f"{label}: distilled_mechanism")
    if candidate.get("local_problem") is not None:
        _text(candidate.get("local_problem"), f"{label}: local_problem")
    _text(candidate.get("local_fit"), f"{label}: local_fit")
    if candidate.get("landing_plane") not in LANDING_PLANES:
        raise ConfigError(f"{label}: invalid landing_plane")
    _text_list(candidate.get("open_questions"), f"{label}: open_questions")
    for key in ("license_note", "review_date"):
        if key in candidate:
            _text(candidate[key], f"{label}: {key}", allow_empty=True)
    return candidate


def validate_claim(claim: object, label: str = "claim") -> dict[str, Any]:
    if not isinstance(claim, dict):
        raise ConfigError(f"{label} must be an object")
    required = {
        "schema_version", "claim_id", "subject_id", "statement", "observable_delta",
        "preserved_behaviors", "sufficient_evidence", "status",
    }
    _exact_fields(claim, required, {"candidate_id"}, label)
    if claim.get("schema_version") != 2:
        raise ConfigError(f"{label}: schema_version must be 2")
    require_id(claim.get("claim_id"), f"{label}: claim_id")
    require_id(claim.get("subject_id"), f"{label}: subject_id")
    if "candidate_id" in claim:
        require_id(claim.get("candidate_id"), f"{label}: candidate_id")
    _text(claim.get("statement"), f"{label}: statement")
    _text(claim.get("observable_delta"), f"{label}: observable_delta")
    _text_list(claim.get("preserved_behaviors"), f"{label}: preserved_behaviors")
    _text_list(claim.get("sufficient_evidence"), f"{label}: sufficient_evidence", allow_empty=False)
    if claim.get("status") not in CLAIM_STATUSES:
        raise ConfigError(f"{label}: invalid status")
    return claim


def validate_decision(decision: object, label: str = "decision") -> dict[str, Any]:
    if not isinstance(decision, dict):
        raise ConfigError(f"{label} must be an object")
    required = {
        "schema_version", "decision_id", "candidate_id", "decision", "rationale",
        "accepted_kernel", "excluded_machinery", "evidence_references", "landing_plane",
        "local_delta", "reopen_condition",
    }
    _exact_fields(decision, required, set(), label)
    if decision.get("schema_version") != 2:
        raise ConfigError(f"{label}: schema_version must be 2")
    require_id(decision.get("decision_id"), f"{label}: decision_id")
    require_id(decision.get("candidate_id"), f"{label}: candidate_id")
    if decision.get("decision") not in DECISIONS:
        raise ConfigError(f"{label}: invalid decision")
    _text(decision.get("rationale"), f"{label}: rationale")
    _text(decision.get("accepted_kernel"), f"{label}: accepted_kernel", allow_empty=True)
    _text(decision.get("excluded_machinery"), f"{label}: excluded_machinery", allow_empty=True)
    _text_list(decision.get("evidence_references"), f"{label}: evidence_references")
    if decision.get("landing_plane") not in LANDING_PLANES:
        raise ConfigError(f"{label}: invalid landing_plane")
    _text(decision.get("local_delta"), f"{label}: local_delta", allow_empty=True)
    _text(decision.get("reopen_condition"), f"{label}: reopen_condition")
    return decision


def validate_record_tree(lab_root: Path) -> dict[str, int]:
    validators = {
        "candidates": validate_candidate,
        "claims": validate_claim,
        "decisions": validate_decision,
    }
    counts: dict[str, int] = {}
    for directory_name, validator in validators.items():
        directory = lab_root / directory_name
        count = 0
        if directory.is_dir():
            for path in sorted(directory.glob("*.json")):
                validator(read_json(path), str(path))
                count += 1
        counts[directory_name] = count
    return counts

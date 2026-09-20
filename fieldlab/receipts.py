from __future__ import annotations

from pathlib import Path
from typing import Any

from .errors import ConfigError
from .io import (
    content_light_artifacts,
    read_json,
    read_json_with_digest,
    sha256_file,
    utc_now,
)
from .review_material import MATERIAL_DIR_NAME
from .subjects import declared_subject_scope


ATTEMPT_OUTCOMES = {
    "pass", "fail", "error", "timeout", "termination-failure", "inconclusive",
    "input-drift", "preflight-failed",
}
CLAIM_ASSESSMENTS = {"supported", "not-supported", "inconclusive"}
REVIEW_INDEPENDENCE = {"implementer-run", "separate-agent", "external-reviewer"}


def _attempt_artifact_names(attempt_dir: Path, verification: dict[str, Any]) -> list[str]:
    names = [
        "case.json", "prompt.md", "trace.jsonl", "stderr.log",
        "final-output.md", "diff.patch", "verification.json", "metadata.json",
    ]
    names.extend(sorted(path.name for path in attempt_dir.glob("verifier-diff-*.patch")))
    material = verification.get("review_material")
    if isinstance(material, dict) and material.get("status") == "sealed":
        manifest = material.get("manifest")
        if isinstance(manifest, str):
            names.append(manifest)
        for entry in material.get("files", []):
            relative = entry.get("path") if isinstance(entry, dict) else None
            if isinstance(relative, str):
                names.append(f"{MATERIAL_DIR_NAME}/{relative}")
    return names


def _declared_review_requirements(receipt: dict[str, Any]) -> list[str]:
    verification = receipt.get("verification_summary", {})
    if not isinstance(verification, dict):
        raise ConfigError("receipt verification_summary must be an object")
    human = verification.get("human_review", {})
    if not isinstance(human, dict):
        raise ConfigError("receipt human_review summary must be an object")
    requirements = human.get("requirements", [])
    if (not isinstance(requirements, list)
            or any(not isinstance(item, str) or not item for item in requirements)
            or len(set(requirements)) != len(requirements)):
        raise ConfigError("receipt review requirements must be unique non-empty strings")
    if human.get("required", bool(requirements)) is not bool(requirements):
        raise ConfigError("receipt human_review required flag disagrees with its requirements")
    return requirements


def synthetic_receipt(
    *,
    run_id: str,
    attempt_id: str,
    lab_id: str,
    case_id: str,
    claim_ids: list[str],
    subject_id: str,
    subject: dict[str, Any],
    mode: str,
    comparison_capable: bool,
    identity_sha256: str,
    input_identity: dict[str, Any],
    execution: dict[str, Any],
    process: dict[str, Any] | None,
    outcome: str,
    verification: dict[str, Any],
    attempt_dir: Path,
) -> dict[str, Any]:
    if outcome not in ATTEMPT_OUTCOMES:
        raise ConfigError(f"unsupported attempt outcome: {outcome}")
    subject_scope = declared_subject_scope(subject)
    human_requirements = list(verification.get("human_review_requirements", []))
    return {
        "schema_version": 2,
        "receipt_type": "attempt",
        "created_at": utc_now(),
        "run_id": run_id,
        "attempt_id": attempt_id,
        "lab_id": lab_id,
        "case_id": case_id,
        "claim_ids": claim_ids,
        "subject_id": subject_id,
        "subject_delivery": verification.get("subject_delivery", {"status": "unknown"}),
        "declared_activation": verification.get("declared_activation"),
        "host_selection": {"status": "unknown"},
        "content_application": {"status": "requires-semantic-review"},
        "target_agent_invocations": 0 if process is None else 1,
        "evidence": {
            "origin": "synthetic",
            "subject_scope": subject_scope,
            "comparison": "matched" if mode == "matched" else "single",
            "verification_methods": ["deterministic"],
            "independence": "implementer-run",
            "comparison_capable": comparison_capable,
            "exclusive_subject_claimed": False,
        },
        "identity_sha256": identity_sha256,
        "inputs": input_identity,
        "selection": {
            "mode": execution["selection_mode"],
            "requested_model": execution["requested_model"],
            "requested_reasoning_effort": execution["requested_reasoning_effort"],
            "actual_model_claimed": False,
        },
        "execution_boundary": {
            "sandbox": execution["sandbox"],
            "approval_policy": execution["approval_policy"],
            "network_access": execution["network_access"],
            "target_started": process is not None,
            "user_home_isolated": True if process is not None else None,
            "user_config_ignored": True if process is not None else None,
            "quiescent": process["quiescent"] if process is not None else None,
            "termination_reason": process["termination_reason"] if process is not None else None,
            "orphan_descendants": process["orphan_descendants"] if process is not None else None,
        },
        "outcome": outcome,
        "verification_summary": {
            "passed": verification.get("passed", False),
            "worker_completion_supported": verification.get(
                "worker_completion_supported", verification.get("passed", False)
            ),
            "changed_files": verification.get("changed_files", []),
            "worker_final": verification.get("worker_final"),
            "review_material": verification.get("review_material"),
            "verifier": verification.get("verifier"),
            "retention": verification.get("retention"),
            "usage": verification.get("trace_summary", {}).get("usage"),
            "human_review": {
                "required": bool(human_requirements),
                "requirements": human_requirements,
                "status": "pending" if human_requirements else "not-required",
            },
        },
        "artifacts": content_light_artifacts(
            attempt_dir,
            _attempt_artifact_names(attempt_dir, verification),
        ),
    }


def observed_receipt_v2(
    *,
    lab_id: str,
    claim_ids: list[str],
    case_id: str | None,
    subject_id: str,
    subject: dict[str, Any],
    assessment: str,
    artifacts: dict[str, Path],
    note: str,
) -> dict[str, Any]:
    if not claim_ids:
        raise ConfigError("observed evidence must bind at least one claim")
    if assessment not in CLAIM_ASSESSMENTS:
        raise ConfigError(f"unsupported claim assessment: {assessment}")
    outcome = {
        "supported": "pass",
        "not-supported": "fail",
        "inconclusive": "inconclusive",
    }[assessment]
    receipt: dict[str, Any] = {
        "schema_version": 2,
        "receipt_type": "observed",
        "created_at": utc_now(),
        "lab_id": lab_id,
        "claim_ids": claim_ids,
        "subject_id": subject_id,
        "evidence": {
            "origin": "observed",
            "subject_scope": declared_subject_scope(subject),
            "comparison": "unmatched",
            "verification_methods": ["human"],
            "independence": "implementer-run",
            "comparison_capable": False,
            "exclusive_subject_claimed": False,
        },
        "claim_assessment": assessment,
        "outcome": outcome,
        "review_note": note,
        "artifacts": {
            name: {"sha256": sha256_file(path), "bytes": path.stat().st_size}
            for name, path in sorted(artifacts.items())
        },
        "claims": {
            "target_agent_invoked_by_observe": False,
            "controlled_comparison": False,
        },
    }
    if case_id is not None:
        receipt["case_id"] = case_id
    return receipt


def human_review_record(
    *,
    review_id: str,
    receipt_path: Path,
    independence: str,
    judgment: str,
    rationale: str,
    requirement_outcomes: dict[str, str] | None = None,
) -> dict[str, Any]:
    if independence not in REVIEW_INDEPENDENCE:
        raise ConfigError(f"unsupported reviewer independence: {independence}")
    if judgment not in CLAIM_ASSESSMENTS:
        raise ConfigError(f"unsupported review judgment: {judgment}")
    receipt_path = receipt_path.expanduser().resolve()
    # Parse and hash the same bytes so the review always binds exactly the
    # receipt content that was validated.
    receipt, receipt_sha256 = read_json_with_digest(receipt_path)
    if receipt.get("schema_version") != 2:
        raise ConfigError("human review requires a schema-v2 receipt")
    requirements = _declared_review_requirements(receipt)
    outcomes = {} if requirement_outcomes is None else requirement_outcomes
    if not isinstance(outcomes, dict):
        raise ConfigError("requirement outcomes must be a JSON object")
    if any(not isinstance(key, str) for key in outcomes):
        raise ConfigError("requirement outcome keys must be strings")
    missing = sorted(set(requirements) - set(outcomes))
    unexpected = sorted(set(outcomes) - set(requirements))
    if missing or unexpected:
        raise ConfigError(
            "requirement outcome keys must exactly match the receipt requirements; "
            f"missing={missing!r}, unexpected={unexpected!r}"
        )
    if any(value not in CLAIM_ASSESSMENTS for value in outcomes.values()):
        raise ConfigError(
            "requirement outcomes must be supported, not-supported, or inconclusive"
        )
    return {
        "schema_version": 2,
        "review_id": review_id,
        "created_at": utc_now(),
        "receipt": {
            "path": str(receipt_path),
            "sha256": receipt_sha256,
        },
        "method": "human",
        "independence": independence,
        "judgment": judgment,
        "rationale": rationale,
        "requirement_outcomes": outcomes,
    }


def load_review_record(path: Path) -> dict[str, Any]:
    path = path.expanduser().resolve()
    record = read_json(path)
    if record.get("schema_version") != 2 or not isinstance(record.get("review_id"), str):
        raise ConfigError(f"not a schema-v2 review record: {path}")
    binding = record.get("receipt")
    if not isinstance(binding, dict) or not isinstance(binding.get("sha256"), str):
        raise ConfigError(f"review record is missing a receipt digest binding: {path}")
    return record


def load_review_records(
    lab_root: Path,
    extra_paths: list[Path] | None = None,
) -> list[tuple[Path, dict[str, Any]]]:
    """Read every lab-scoped review record plus any explicitly supplied review."""
    candidates: list[Path] = []
    reviews_dir = lab_root / "reviews"
    if reviews_dir.is_dir():
        candidates.extend(sorted(path for path in reviews_dir.rglob("*.json") if path.is_file()))
    candidates.extend(path.expanduser().resolve() for path in extra_paths or [])
    records: list[tuple[Path, dict[str, Any]]] = []
    seen: set[Path] = set()
    for path in candidates:
        if path in seen:
            continue
        seen.add(path)
        records.append((path, load_review_record(path)))
    return records

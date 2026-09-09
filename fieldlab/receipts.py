from __future__ import annotations

from pathlib import Path
from typing import Any

from .errors import ConfigError
from .io import content_light_artifacts, read_json, sha256_file, utc_now
from .subjects import declared_subject_scope


ATTEMPT_OUTCOMES = {
    "pass", "fail", "error", "timeout", "termination-failure", "inconclusive"
}
CLAIM_ASSESSMENTS = {"supported", "not-supported", "inconclusive"}
REVIEW_INDEPENDENCE = {"implementer-run", "separate-agent", "external-reviewer"}


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
    process: dict[str, Any],
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
            "user_home_isolated": True,
            "user_config_ignored": True,
            "quiescent": process["quiescent"],
            "termination_reason": process["termination_reason"],
            "orphan_descendants": process["orphan_descendants"],
        },
        "outcome": outcome,
        "verification_summary": {
            "passed": verification.get("passed", False),
            "changed_files": verification.get("changed_files", []),
            "usage": verification.get("trace_summary", {}).get("usage"),
            "human_review": {
                "required": bool(human_requirements),
                "requirements": human_requirements,
                "status": "pending" if human_requirements else "not-required",
            },
        },
        "artifacts": content_light_artifacts(
            attempt_dir,
            [
                "case.json", "prompt.md", "trace.jsonl", "stderr.log",
                "final-output.md", "diff.patch", "verification.json", "metadata.json",
            ],
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
    receipt = read_json(receipt_path)
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
            "sha256": sha256_file(receipt_path),
        },
        "method": "human",
        "independence": independence,
        "judgment": judgment,
        "rationale": rationale,
        "requirement_outcomes": outcomes,
    }

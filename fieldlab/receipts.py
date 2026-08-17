from __future__ import annotations

from pathlib import Path
from typing import Any

from .io import content_light_artifacts, sha256_file, utc_now


def synthetic_receipt(
    *,
    run_id: str,
    attempt_id: str,
    pack_id: str,
    case_id: str,
    subject_id: str,
    subject: dict[str, Any],
    mode: str,
    comparison_capable: bool,
    identity_sha256: str,
    input_identity: dict[str, str],
    execution: dict[str, Any],
    process: dict[str, Any],
    outcome: str,
    verification: dict[str, Any],
    attempt_dir: Path,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "receipt_type": "attempt",
        "created_at": utc_now(),
        "run_id": run_id,
        "attempt_id": attempt_id,
        "pack_id": pack_id,
        "case_id": case_id,
        "subject_id": subject_id,
        "evidence": {
            "origin": "synthetic",
            "attribution": subject["attribution"],
            "comparison": "matched" if mode == "matched" else "single",
            "verification": "deterministic",
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
            "user_home_isolated": subject["attribution"] == "repo_scoped",
            "user_config_ignored": subject["attribution"] == "repo_scoped",
            "quiescent": process["quiescent"],
            "termination_reason": process["termination_reason"],
            "orphan_descendants": process["orphan_descendants"],
        },
        "outcome": outcome,
        "verification_summary": {
            "passed": verification.get("passed", False),
            "changed_files": verification.get("changed_files", []),
            "usage": verification.get("trace_summary", {}).get("usage"),
        },
        "artifacts": content_light_artifacts(
            attempt_dir,
            [
                "case.json",
                "prompt.md",
                "trace.jsonl",
                "stderr.log",
                "final-output.md",
                "diff.patch",
                "verification.json",
                "metadata.json",
            ],
        ),
    }


def observed_receipt(
    *,
    pack_id: str,
    case_id: str,
    subject_id: str,
    subject: dict[str, Any],
    outcome: str,
    artifacts: dict[str, Path],
    note: str,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "receipt_type": "observed-import",
        "created_at": utc_now(),
        "pack_id": pack_id,
        "case_id": case_id,
        "subject_id": subject_id,
        "evidence": {
            "origin": "observed",
            "attribution": subject["attribution"],
            "comparison": "unmatched",
            "verification": "human",
            "independence": "implementer-run",
            "comparison_capable": False,
            "exclusive_subject_claimed": False,
        },
        "outcome": outcome,
        "review_note": note,
        "artifacts": {
            name: {"sha256": sha256_file(path), "bytes": path.stat().st_size}
            for name, path in sorted(artifacts.items())
        },
        "claims": {
            "target_agent_invoked_by_import": False,
            "controlled_comparison": False,
        },
    }

from __future__ import annotations

import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .contracts import (
    EFFORTS,
    MODES,
    RUN_ID_RE,
    case_identity,
    load_cases,
    load_lab,
    manifest_identity,
)
from .errors import ConfigError
from .io import canonical_json, python_source_digest, sha256_file, sha256_text, utc_now
from .subjects import subject_identity


def executable_request_identity(codex_bin: str) -> dict[str, str | None]:
    discovered = shutil.which(codex_bin)
    if not discovered:
        return {"requested": codex_bin, "resolved_path": None, "sha256": None}
    path = Path(discovered).expanduser().resolve()
    digest: str | None = None
    if path.is_file():
        try:
            digest = sha256_file(path)
        except OSError:
            digest = None
    return {"requested": codex_bin, "resolved_path": str(path), "sha256": digest}


def planned_inputs(
    *,
    manifest_path: Path,
    lab: dict[str, Any],
    lab_root: Path,
    cases: dict[str, tuple[Path, dict[str, Any]]],
    subject_ids: list[str],
    case_ids: list[str],
    codex_bin: str,
) -> dict[str, Any]:
    return {
        "manifest": manifest_identity(manifest_path),
        "fieldlab_source_sha256": python_source_digest(Path(__file__).resolve().parent),
        "adapter_executable": executable_request_identity(codex_bin),
        "subjects": {
            subject_id: subject_identity(
                subject_id,
                lab["subjects"][subject_id],
                lab_root,
            )
            for subject_id in subject_ids
        },
        "cases": {
            case_id: case_identity(cases[case_id][0], cases[case_id][1])
            for case_id in case_ids
        },
    }


def default_run_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    return f"{stamp}-{uuid.uuid4().hex[:8]}"


def _resolved_output_root(lab_root: Path, requested: str | None, default: str) -> Path:
    raw = Path(requested or default).expanduser()
    if not raw.is_absolute():
        raw = lab_root / raw
    return raw.resolve()


def build_plan(
    *,
    manifest_path: Path,
    subject_ids: list[str],
    case_ids: list[str],
    mode: str,
    repeat: int,
    model: str | None,
    reasoning_effort: str | None,
    codex_bin: str,
    run_id: str | None,
    output_root: str | None,
    timeout_override: int | None,
    keep_workspace: bool | None,
) -> dict[str, Any]:
    """Build an immutable no-spend plan for one schema-v2 lab."""

    manifest_path = manifest_path.expanduser().resolve()
    lab, lab_root, cases_root = load_lab(manifest_path)
    cases = load_cases(cases_root)
    if mode not in MODES:
        raise ConfigError(f"unsupported mode: {mode}")
    if not subject_ids or not case_ids:
        raise ConfigError("select at least one --subject and one --case; no live matrix is implicit")
    subject_ids = list(dict.fromkeys(subject_ids))
    case_ids = list(dict.fromkeys(case_ids))
    unknown_subjects = sorted(set(subject_ids) - set(lab["subjects"]))
    unknown_cases = sorted(set(case_ids) - set(cases))
    if unknown_subjects:
        raise ConfigError(f"unknown subjects: {', '.join(unknown_subjects)}")
    if unknown_cases:
        raise ConfigError(f"unknown cases: {', '.join(unknown_cases)}")
    if repeat < 1:
        raise ConfigError("repeat must be at least 1")
    if timeout_override is not None and not 1 <= timeout_override <= 3600:
        raise ConfigError("timeout override must be 1..3600")

    identities = {
        subject_id: subject_identity(
            subject_id,
            lab["subjects"][subject_id],
            lab_root,
        )
        for subject_id in subject_ids
    }
    if not model:
        raise ConfigError("live-capable plans require an explicit --model")
    if reasoning_effort not in EFFORTS:
        raise ConfigError(
            "live-capable plans require explicit --reasoning-effort: "
            + ", ".join(sorted(EFFORTS))
        )
    if mode == "matched" and len(subject_ids) < 2:
        raise ConfigError("matched mode requires at least two subjects")
    if mode == "canary" and len(subject_ids) != 1:
        raise ConfigError("canary mode requires exactly one subject")
    if mode == "matched":
        scopes = {identity["subject_scope"] for identity in identities.values()}
        if "isolated-control" not in scopes or "workspace-scoped" not in scopes:
            raise ConfigError(
                "matched mode requires at least one isolated-control and one workspace-scoped subject"
            )
    selection_mode = "explicit"
    comparison_capable = True

    resolved_run_id = run_id or default_run_id()
    if not RUN_ID_RE.fullmatch(resolved_run_id):
        raise ConfigError("run_id must use letters, digits, dot, underscore, or hyphen")
    output_root_path = _resolved_output_root(
        lab_root,
        output_root,
        lab["defaults"]["output_root"],
    )
    effective_keep_workspace = (
        lab["defaults"]["keep_workspace"] if keep_workspace is None else keep_workspace
    )
    matrix = [
        {"subject_id": subject_id, "case_id": case_id, "repeat": index}
        for subject_id in subject_ids
        for case_id in case_ids
        for index in range(1, repeat + 1)
    ]
    plan: dict[str, Any] = {
        "schema_version": 2,
        "run_id": resolved_run_id,
        "created_at": utc_now(),
        "manifest_path": str(manifest_path),
        "lab_id": lab["lab_id"],
        "mode": mode,
        "comparison_capable": comparison_capable,
        "subjects": subject_ids,
        "cases": case_ids,
        "repeat": repeat,
        "target_invocations": len(matrix),
        "llm_grader_invocations": 0,
        "matrix": matrix,
        "planned_inputs": planned_inputs(
            manifest_path=manifest_path,
            lab=lab,
            lab_root=lab_root,
            cases=cases,
            subject_ids=subject_ids,
            case_ids=case_ids,
            codex_bin=codex_bin,
        ),
        "execution": {
            "adapter": lab["defaults"]["adapter"],
            "codex_bin": codex_bin,
            "selection_mode": selection_mode,
            "requested_model": model,
            "requested_reasoning_effort": reasoning_effort,
            "approval_policy": lab["defaults"]["approval_policy"],
            "network_access": lab["defaults"]["network_access"],
            "timeout_override_seconds": timeout_override,
            "keep_workspace": effective_keep_workspace,
            "output_root": str(output_root_path),
        },
    }
    plan["plan_sha256"] = sha256_text(canonical_json(plan))
    return plan


def validate_plan(plan: dict[str, Any]) -> None:
    required = {
        "schema_version", "run_id", "created_at", "manifest_path",
        "lab_id", "mode", "comparison_capable",
        "subjects", "cases", "repeat", "target_invocations",
        "llm_grader_invocations", "matrix", "planned_inputs", "execution",
        "plan_sha256",
    }
    if set(plan) != required:
        raise ConfigError(
            f"plan fields mismatch; missing={sorted(required - set(plan))}, "
            f"extra={sorted(set(plan) - required)}"
        )
    if plan["schema_version"] != 2:
        raise ConfigError("plan has unsupported schema_version")
    if plan["mode"] not in MODES:
        raise ConfigError("plan has unsupported mode")
    stored = plan["plan_sha256"]
    body = dict(plan)
    del body["plan_sha256"]
    if stored != sha256_text(canonical_json(body)):
        raise ConfigError("plan_sha256 does not match plan content")
    if plan["target_invocations"] != len(plan["matrix"]):
        raise ConfigError("target_invocations does not match matrix")
    expected_matrix = [
        {"subject_id": subject_id, "case_id": case_id, "repeat": index}
        for subject_id in plan["subjects"]
        for case_id in plan["cases"]
        for index in range(1, plan["repeat"] + 1)
    ]
    if plan["matrix"] != expected_matrix:
        raise ConfigError("plan matrix is not the declared subject/case/repeat product")
    planned = plan.get("planned_inputs")
    expected_planned = {
        "manifest", "fieldlab_source_sha256", "adapter_executable", "subjects", "cases"
    }
    if not isinstance(planned, dict) or set(planned) != expected_planned:
        raise ConfigError("plan planned_inputs contract is invalid")
    manifest = planned["manifest"]
    if not isinstance(manifest, dict) or set(manifest) != {"schema_version", "sha256"}:
        raise ConfigError("plan manifest identity is invalid")
    if manifest["schema_version"] != 2:
        raise ConfigError("plan manifest identity must be schema version 2")
    if not isinstance(manifest["sha256"], str) or len(manifest["sha256"]) != 64:
        raise ConfigError("plan manifest digest is invalid")
    if not isinstance(planned["fieldlab_source_sha256"], str) or len(planned["fieldlab_source_sha256"]) != 64:
        raise ConfigError("plan Field Lab source digest is invalid")
    adapter_request = planned["adapter_executable"]
    if not isinstance(adapter_request, dict) or set(adapter_request) != {
        "requested", "resolved_path", "sha256"
    }:
        raise ConfigError("plan adapter executable identity is invalid")
    if adapter_request["requested"] != plan["execution"].get("codex_bin"):
        raise ConfigError("plan adapter request does not match execution.codex_bin")
    if set(planned["subjects"]) != set(plan["subjects"]):
        raise ConfigError("plan subject digests do not match selected subjects")
    if set(planned["cases"]) != set(plan["cases"]):
        raise ConfigError("plan case digests do not match selected cases")
    if plan["mode"] == "canary" and len(plan["subjects"]) != 1:
        raise ConfigError("canary plan requires exactly one subject")
    if plan["mode"] == "matched" and len(plan["subjects"]) < 2:
        raise ConfigError("matched plan requires at least two subjects")
    execution = plan["execution"]
    if execution.get("adapter") != "codex-exec":
        raise ConfigError("unsupported plan adapter")
    if execution.get("selection_mode") == "explicit":
        if not execution.get("requested_model") or execution.get("requested_reasoning_effort") not in EFFORTS:
            raise ConfigError("explicit plans require model and reasoning effort")

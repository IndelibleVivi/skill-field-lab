from __future__ import annotations

import json
import os
import platform
import shutil
from pathlib import Path
from typing import Any

from . import __version__
from .adapters.registry import create_adapter
from .contracts import case_identity, load_cases, load_lab
from .errors import ConfigError, EvidenceError, ExecutionError
from .io import (
    atomic_write_json,
    atomic_write_text,
    canonical_json,
    read_json,
    sha256_file,
    sha256_text,
    tree_digest,
    utc_now,
)
from .plan import planned_inputs, validate_plan
from .receipts import synthetic_receipt
from .review_material import LIMITS as REVIEW_MATERIAL_LIMITS, seal_review_material
from .subjects import subject_identity
from .trace import parse_trace
from .verify import (
    evaluate_command_assertion,
    evaluate_result_assertions,
    evaluate_trace_assertions,
    evaluate_workspace_assertions,
)
from .workspace import capture_diff, changed_files, copy_workspace, prepare_workspace


TERMINAL_STATES = {"completed", "termination-failed", "evidence-failed"}
EVIDENCE_ERROR_REASON_LIMIT = 500


def _next_attempt_dir(repeat_dir: Path) -> Path:
    indexes: list[int] = []
    for path in repeat_dir.glob("attempt-*"):
        try:
            indexes.append(int(path.name.removeprefix("attempt-")))
        except ValueError:
            continue
    return repeat_dir / f"attempt-{max(indexes, default=0) + 1:03d}"


def _completed_attempt(repeat_dir: Path) -> dict[str, Any] | None:
    for path in sorted(repeat_dir.glob("attempt-*/metadata.json"), reverse=True):
        try:
            metadata = read_json(path)
        except ConfigError:
            continue
        if metadata.get("state") == "completed":
            return metadata
    return None


def _effective_execution(plan: dict[str, Any], case: dict[str, Any]) -> dict[str, Any]:
    execution = plan["execution"]
    timeout = execution["timeout_override_seconds"] or case["timeout_seconds"]
    return {
        "selection_mode": execution["selection_mode"],
        "requested_model": execution["requested_model"],
        "requested_reasoning_effort": execution["requested_reasoning_effort"],
        "approval_policy": execution["approval_policy"],
        "network_access": execution["network_access"],
        "sandbox": case["sandbox"],
        "timeout_seconds": timeout,
    }


def _run_identity(
    *,
    plan: dict[str, Any],
    lab: dict[str, Any],
    lab_root: Path,
    cases: dict[str, tuple[Path, dict[str, Any]]],
    adapter_identity: dict[str, Any],
) -> dict[str, Any]:
    identity: dict[str, Any] = {
        "fieldlab_version": __version__,
        "fieldlab_source_sha256": plan["planned_inputs"]["fieldlab_source_sha256"],
        "runtime": {"python": platform.python_version(), "platform": platform.platform()},
        "plan_sha256": plan["plan_sha256"],
        "manifest": {
            "lab_id": lab["lab_id"],
            **plan["planned_inputs"]["manifest"],
        },
        "cases": {
            case_id: case_identity(cases[case_id][0], cases[case_id][1])
            for case_id in plan["cases"]
        },
        "subjects": {
            subject_id: subject_identity(
                subject_id,
                lab["subjects"][subject_id],
                lab_root,
            )
            for subject_id in plan["subjects"]
        },
        "adapter": adapter_identity,
        "execution": {
            key: plan["execution"][key]
            for key in (
                "selection_mode", "requested_model", "requested_reasoning_effort",
                "approval_policy", "network_access", "timeout_override_seconds",
                "keep_workspace",
            )
        },
        "mode": plan["mode"],
        "repeat": plan["repeat"],
    }
    identity["identity_sha256"] = sha256_text(canonical_json(identity))
    return identity


def _run_directory(plan: dict[str, Any]) -> Path:
    output_root = Path(plan["execution"]["output_root"])
    return output_root / plan["run_id"]


def run_plan(
    plan_path: Path,
    *,
    live: bool,
    max_invocations: int | None,
    resume: bool,
) -> int:
    if not live:
        raise ConfigError(
            "refusing to start target-agent invocations without --live; "
            "skill activation and planning do not grant spend"
        )
    plan = read_json(plan_path.expanduser().resolve())
    validate_plan(plan)
    if max_invocations is None:
        raise ConfigError("--max-invocations is required at the live boundary")
    if max_invocations < plan["target_invocations"]:
        raise ConfigError(
            f"plan requires {plan['target_invocations']} target invocations, "
            f"above --max-invocations {max_invocations}"
        )
    manifest_path = Path(plan["manifest_path"])
    lab, lab_root, cases_root = load_lab(manifest_path)
    cases = load_cases(cases_root)
    if lab["lab_id"] != plan["lab_id"]:
        raise ConfigError("plan lab identity no longer matches the loaded manifest")
    unknown_subjects = sorted(set(plan["subjects"]) - set(lab["subjects"]))
    unknown_cases = sorted(set(plan["cases"]) - set(cases))
    if unknown_subjects or unknown_cases:
        raise ConfigError(
            f"plan selections no longer exist; subjects={unknown_subjects}, cases={unknown_cases}"
        )
    current_planned_inputs = planned_inputs(
        manifest_path=manifest_path,
        lab=lab,
        lab_root=lab_root,
        cases=cases,
        subject_ids=plan["subjects"],
        case_ids=plan["cases"],
        codex_bin=plan["execution"]["codex_bin"],
    )
    if current_planned_inputs != plan["planned_inputs"]:
        raise ConfigError(
            "plan input drift: manifest, case, fixture, prompt, subject source, "
            "Field Lab source, or adapter executable changed; create and review a new "
            "no-spend plan before running live"
        )
    adapter = create_adapter(plan["execution"]["adapter"], plan["execution"]["codex_bin"])
    identity = _run_identity(
        plan=plan,
        lab=lab,
        lab_root=lab_root,
        cases=cases,
        adapter_identity=adapter.identity(),
    )

    run_dir = _run_directory(plan)
    summary_path = run_dir / "summary.json"
    if run_dir.exists() and not resume:
        raise ConfigError(f"run already exists; use --resume or a new run id: {run_dir}")
    if resume:
        if not summary_path.is_file():
            raise ConfigError(f"cannot resume without summary: {summary_path}")
        previous = read_json(summary_path)
        if previous.get("identity") != identity:
            raise ConfigError(
                "resume identity mismatch: "
                + json.dumps(
                    {
                        "existing": previous.get("identity", {}).get("identity_sha256"),
                        "requested": identity["identity_sha256"],
                    },
                    ensure_ascii=False,
                )
            )

    summary: dict[str, Any] = {
        "schema_version": 2,
        "state": "running",
        "run_id": plan["run_id"],
        "lab_id": lab["lab_id"],
        "mode": plan["mode"],
        "comparison_capable": plan["comparison_capable"],
        "started_at": utc_now(),
        "updated_at": utc_now(),
        "identity": identity,
        "attempts": [],
    }
    if resume:
        previous = read_json(summary_path)
        summary["started_at"] = previous.get("started_at", summary["started_at"])
    run_dir.mkdir(parents=True, exist_ok=True)
    atomic_write_json(summary_path, summary)

    try:
        for item in plan["matrix"]:
            subject_id = item["subject_id"]
            case_id = item["case_id"]
            repeat = item["repeat"]
            repeat_dir = run_dir / subject_id / case_id / f"repeat-{repeat:03d}"
            if resume:
                prior = _completed_attempt(repeat_dir)
                if prior is not None:
                    summary["attempts"].append(prior)
                    print(f"SKIP {subject_id}/{case_id} repeat={repeat} outcome={prior['outcome']}")
                    continue
            attempt_dir = _next_attempt_dir(repeat_dir)
            metadata = run_attempt(
                plan=plan,
                identity=identity,
                lab=lab,
                lab_root=lab_root,
                subject_id=subject_id,
                case_id=case_id,
                case_dir=cases[case_id][0],
                case=cases[case_id][1],
                repeat=repeat,
                attempt_dir=attempt_dir,
                adapter=adapter,
            )
            summary["attempts"].append(metadata)
            summary["updated_at"] = utc_now()
            atomic_write_json(summary_path, summary)
            print(
                f"{metadata['outcome'].upper()} {subject_id}/{case_id} repeat={repeat} "
                f"artifacts={attempt_dir}"
            )
    except KeyboardInterrupt:
        summary["state"] = "interrupted"
        summary["updated_at"] = utc_now()
        atomic_write_json(summary_path, summary)
        return 130
    except EvidenceError:
        summary["state"] = "evidence-failed"
        summary["updated_at"] = utc_now()
        atomic_write_json(summary_path, summary)
        raise
    except ExecutionError:
        summary["state"] = "termination-failed"
        summary["updated_at"] = utc_now()
        atomic_write_json(summary_path, summary)
        raise

    summary["state"] = "completed"
    summary["updated_at"] = utc_now()
    atomic_write_json(summary_path, summary)
    outcomes = [attempt["outcome"] for attempt in summary["attempts"]]
    passed = bool(outcomes) and all(outcome == "pass" for outcome in outcomes)
    print(f"Run {plan['run_id']} completed: {outcomes.count('pass')}/{len(outcomes)} attempts passed.")
    return 0 if passed else 1


def _has_declared_deterministic_assertion(case: dict[str, Any]) -> bool:
    result_assertions = case.get("result_assertions", {})
    return bool(
        any(result_assertions.get(key) for key in result_assertions)
        or case.get("workspace_assertions")
        or case.get("command_assertions")
        or case.get("trace_assertions")
    )


def _path_signature(root: Path, relative: str) -> str:
    """Describe one workspace path without following a symlink."""
    target = root / relative
    if target.is_symlink():
        return "symlink:" + os.readlink(target)
    if target.is_file():
        return "file:" + sha256_file(target)
    if target.exists():
        return "other"
    return "absent"


def _derived_changes(
    worker_workspace: Path,
    verifier_workspace: Path,
    worker_changed_files: list[str],
    verifier_changed_files: list[str],
) -> list[str]:
    """List paths whose bytes the verifier changed relative to worker output."""
    candidates = sorted(set(worker_changed_files) | set(verifier_changed_files))
    return [
        path
        for path in candidates
        if _path_signature(worker_workspace, path) != _path_signature(verifier_workspace, path)
    ]


def run_attempt(
    *,
    plan: dict[str, Any],
    identity: dict[str, Any],
    lab: dict[str, Any],
    lab_root: Path,
    subject_id: str,
    case_id: str,
    case_dir: Path,
    case: dict[str, Any],
    repeat: int,
    attempt_dir: Path,
    adapter: Any,
) -> dict[str, Any]:
    attempt_dir.mkdir(parents=True, exist_ok=False)
    workspace = attempt_dir / "workspace"
    subject = lab["subjects"][subject_id]
    prepare_workspace(
        case_dir=case_dir,
        subject=subject,
        lab_root=lab_root,
        subject_id=subject_id,
        workspace=workspace,
    )
    prompt = (case_dir / case["prompt_file"]).read_text(encoding="utf-8").strip()
    atomic_write_text(attempt_dir / "prompt.md", prompt + "\n")
    atomic_write_json(attempt_dir / "case.json", case)
    execution = _effective_execution(plan, case)
    attempt_id = attempt_dir.name
    input_identity = case_identity(case_dir, case)
    metadata: dict[str, Any] = {
        "schema_version": 2,
        "state": "running",
        "outcome": "pending",
        "run_id": plan["run_id"],
        "attempt_id": attempt_id,
        "lab_id": lab["lab_id"],
        "case_id": case_id,
        "subject_id": subject_id,
        "repeat": repeat,
        "started_at": utc_now(),
        "updated_at": utc_now(),
        "identity_sha256": identity["identity_sha256"],
        "inputs": input_identity,
        "execution": execution,
        "process": None,
        "artifacts": {
            "trace": "trace.jsonl",
            "stderr": "stderr.log",
            "final_response": "final-output.md",
            "verification": "verification.json",
            "diff": "diff.patch",
            "receipt": "receipt.json",
        },
    }
    atomic_write_json(attempt_dir / "metadata.json", metadata)

    process_result = adapter.execute(
        workspace=workspace,
        prompt=prompt,
        subject=subject,
        execution=execution,
        trace_path=attempt_dir / "trace.jsonl",
        stderr_path=attempt_dir / "stderr.log",
    )
    process = process_result.to_dict()
    metadata["process"] = process
    metadata["updated_at"] = utc_now()

    if not process_result.quiescent:
        metadata["state"] = "termination-failed"
        metadata["outcome"] = "termination-failure"
        atomic_write_json(attempt_dir / "metadata.json", metadata)
        raise ExecutionError(
            process_result.termination_error
            or "execution group could not be proven quiescent; evidence remains unsealed"
        )

    trace_summary = parse_trace(attempt_dir / "trace.jsonl")
    final_response = trace_summary["final_message"]
    atomic_write_text(attempt_dir / "final-output.md", final_response + "\n")

    # Seal worker-final bytes before any verifier process can observe or mutate
    # them. The sealed diff and changed-file set describe only the worker.
    worker_changed_files = changed_files(workspace)
    worker_diff = capture_diff(workspace)
    worker_tree_sha256 = tree_digest(workspace)
    atomic_write_text(attempt_dir / "diff.patch", worker_diff)

    review_requirements = list(case.get("human_review_requirements", []))
    command_assertions = list(case.get("command_assertions", []))
    keep_workspace = bool(plan["execution"]["keep_workspace"])
    declared_material = case.get("human_review_material")
    if declared_material is not None:
        try:
            review_material = seal_review_material(
                workspace=workspace,
                attempt_dir=attempt_dir,
                declared=declared_material,
            )
        except EvidenceError as exc:
            # The worker already reached a trustworthy terminal state; the
            # failure is evidence construction, not process termination.
            reason = str(exc)[:EVIDENCE_ERROR_REASON_LIMIT]
            metadata["state"] = "evidence-failed"
            metadata["outcome"] = "error"
            metadata["error"] = reason
            metadata["updated_at"] = utc_now()
            atomic_write_json(attempt_dir / "metadata.json", metadata)
            if not keep_workspace:
                shutil.rmtree(workspace, ignore_errors=True)
            raise
    else:
        review_material = {
            "status": "not-declared",
            "directory": None,
            "manifest": None,
            "manifest_sha256": None,
            "files": [],
            "total_bytes": 0,
            "limits": dict(REVIEW_MATERIAL_LIMITS),
        }

    result_results = evaluate_result_assertions(case, final_response)
    # Workspace assertions read the sealed worker-final tree, never a verifier
    # copy, so a verifier repair cannot satisfy them.
    workspace_results = evaluate_workspace_assertions(
        case,
        workspace,
        attempt_dir / "assertion-artifacts" / "workspace",
    )
    command_results: list[dict[str, Any]] = []
    command_attribution: list[dict[str, Any]] = []
    verifier_mutated = False
    for index, assertion in enumerate(command_assertions):
        copy = attempt_dir / "verifier-workspace" / f"command-{index:03d}"
        try:
            # Every command assertion starts from the same sealed worker-final
            # tree in its own byte copy, so no command inherits another's edit.
            copy_workspace(workspace, copy)
            command_results.append(
                evaluate_command_assertion(
                    assertion,
                    copy,
                    attempt_dir / "assertion-artifacts" / "commands",
                    index,
                )
            )
            copy_changed_files = changed_files(copy)
            mutated = tree_digest(copy) != worker_tree_sha256
            derived_changed_files = _derived_changes(
                workspace,
                copy,
                worker_changed_files,
                copy_changed_files,
            )
            attribution: dict[str, Any] = {
                "index": index,
                "mutated_worker_output": mutated,
                "derived_changed_files": derived_changed_files,
            }
            if mutated:
                patch_name = f"verifier-diff-{index:03d}.patch"
                diff = capture_diff(copy)
                atomic_write_text(attempt_dir / patch_name, diff)
                attribution["diff"] = patch_name
                attribution["diff_sha256"] = sha256_text(diff)
            command_attribution.append(attribution)
            verifier_mutated = verifier_mutated or mutated
        finally:
            shutil.rmtree(copy, ignore_errors=True)
    verifier_root = attempt_dir / "verifier-workspace"
    if verifier_root.exists():
        shutil.rmtree(verifier_root, ignore_errors=True)
    trace_results = evaluate_trace_assertions(case, trace_summary)

    verifier_summary = {
        "command_assertions": len(command_assertions),
        "isolated_copy": bool(command_assertions),
        "fresh_copy_per_command": True,
        "mutated_worker_output": verifier_mutated,
        "derived_changed_files": sorted(
            {
                path
                for attribution in command_attribution
                for path in attribution["derived_changed_files"]
            }
        ),
        "worker_final_tree_sha256": worker_tree_sha256,
        "commands": command_attribution,
    }
    retention = {
        "workspace_retained": keep_workspace,
        "reason": "keep-workspace" if keep_workspace else "not-retained",
    }
    all_results = result_results + workspace_results + command_results + trace_results
    verification = {
        "schema_version": 2,
        "passed": all(result["passed"] for result in all_results),
        "result_assertions": result_results,
        "workspace_assertions": workspace_results,
        "command_assertions": command_results,
        "trace_assertions": trace_results,
        "human_review_requirements": review_requirements,
        "changed_files": worker_changed_files,
        "worker_final": {
            "changed_files": worker_changed_files,
            "tree_sha256": worker_tree_sha256,
            "diff_sha256": sha256_text(worker_diff),
        },
        "review_material": review_material,
        "verifier": verifier_summary,
        "retention": retention,
        "trace_summary": trace_summary,
    }
    # A verifier that had to mutate its copy cannot turn a worker result into a
    # clean completion: the sealed worker bytes stay the only support surface.
    verification["worker_completion_supported"] = (
        verification["passed"] and not verifier_mutated
    )
    atomic_write_json(attempt_dir / "verification.json", verification)

    if process_result.timed_out:
        outcome = "timeout"
    elif process_result.orphan_descendants:
        outcome = "error"
    elif process_result.return_code != 0:
        outcome = "error"
    elif not _has_declared_deterministic_assertion(case) and review_requirements:
        outcome = "inconclusive"
    elif verification["worker_completion_supported"]:
        outcome = "pass"
    elif verification["passed"]:
        outcome = "inconclusive"
    else:
        outcome = "fail"

    metadata["state"] = "completed"
    metadata["outcome"] = outcome
    metadata["retention"] = retention
    metadata["updated_at"] = utc_now()
    atomic_write_json(attempt_dir / "metadata.json", metadata)
    receipt = synthetic_receipt(
        run_id=plan["run_id"],
        attempt_id=attempt_id,
        lab_id=lab["lab_id"],
        case_id=case_id,
        claim_ids=list(case.get("claim_ids", [])),
        subject_id=subject_id,
        subject=subject,
        mode=plan["mode"],
        comparison_capable=plan["comparison_capable"],
        identity_sha256=identity["identity_sha256"],
        input_identity=input_identity,
        execution=execution,
        process=process,
        outcome=outcome,
        verification=verification,
        attempt_dir=attempt_dir,
    )
    atomic_write_json(attempt_dir / "receipt.json", receipt)

    if not retention["workspace_retained"]:
        shutil.rmtree(workspace)
    return metadata

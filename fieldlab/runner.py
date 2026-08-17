from __future__ import annotations

import json
import platform
import shutil
from pathlib import Path
from typing import Any

from . import __version__
from .adapters.codex_exec import CodexExecAdapter
from .contracts import case_identity, load_cases, load_pack, subject_identity
from .errors import ConfigError, ExecutionError
from .io import (
    atomic_write_json,
    atomic_write_text,
    canonical_json,
    read_json,
    sha256_text,
    utc_now,
)
from .plan import planned_inputs, validate_plan
from .receipts import synthetic_receipt
from .trace import parse_trace
from .verify import evaluate_file_assertions, evaluate_trace_assertions
from .workspace import capture_diff, changed_files, prepare_workspace

TERMINAL_STATES = {"completed", "termination-failed"}


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
    pack: dict[str, Any],
    pack_dir: Path,
    cases: dict[str, tuple[Path, dict[str, Any]]],
    adapter_identity: dict[str, Any],
) -> dict[str, Any]:
    identity: dict[str, Any] = {
        "fieldlab_version": __version__,
        "fieldlab_source_sha256": plan["planned_inputs"]["fieldlab_source_sha256"],
        "runtime": {
            "python": platform.python_version(),
            "platform": platform.platform(),
        },
        "plan_sha256": plan["plan_sha256"],
        "pack": {
            "pack_id": pack["pack_id"],
            "sha256": sha256_text(canonical_json(pack)),
        },
        "cases": {
            case_id: case_identity(cases[case_id][0], cases[case_id][1])
            for case_id in plan["cases"]
        },
        "subjects": {
            subject_id: subject_identity(pack["subjects"][subject_id], pack_dir)
            for subject_id in plan["subjects"]
        },
        "adapter": adapter_identity,
        "execution": {
            key: plan["execution"][key]
            for key in (
                "selection_mode",
                "requested_model",
                "requested_reasoning_effort",
                "approval_policy",
                "network_access",
                "timeout_override_seconds",
                "keep_workspace",
            )
        },
        "mode": plan["mode"],
        "repeat": plan["repeat"],
    }
    identity["identity_sha256"] = sha256_text(canonical_json(identity))
    return identity


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
    if plan["mode"] == "environment-smoke" and resume:
        raise ConfigError("environment-smoke runs cannot resume across mutable ambient defaults")

    pack_path = Path(plan["pack_path"])
    pack, pack_dir, cases_root = load_pack(pack_path)
    cases = load_cases(cases_root)
    if pack["pack_id"] != plan["pack_id"]:
        raise ConfigError("plan pack_id no longer matches the loaded pack")
    unknown_subjects = sorted(set(plan["subjects"]) - set(pack["subjects"]))
    unknown_cases = sorted(set(plan["cases"]) - set(cases))
    if unknown_subjects or unknown_cases:
        raise ConfigError(
            f"plan selections no longer exist; subjects={unknown_subjects}, cases={unknown_cases}"
        )
    current_planned_inputs = planned_inputs(
        pack=pack,
        pack_dir=pack_dir,
        cases=cases,
        subject_ids=plan["subjects"],
        case_ids=plan["cases"],
        codex_bin=plan["execution"]["codex_bin"],
    )
    if current_planned_inputs != plan["planned_inputs"]:
        raise ConfigError(
            "plan input drift: pack, case, fixture, prompt, subject overlay, or Codex executable changed; "
            "create and review a new no-spend plan before running live"
        )
    adapter = CodexExecAdapter(plan["execution"]["codex_bin"])
    adapter_identity = adapter.identity()
    identity = _run_identity(
        plan=plan,
        pack=pack,
        pack_dir=pack_dir,
        cases=cases,
        adapter_identity=adapter_identity,
    )

    output_root = Path(plan["execution"]["output_root"])
    run_dir = output_root / "runs" / plan["run_id"]
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
        "schema_version": 1,
        "state": "running",
        "run_id": plan["run_id"],
        "pack_id": pack["pack_id"],
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
                pack=pack,
                pack_dir=pack_dir,
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


def run_attempt(
    *,
    plan: dict[str, Any],
    identity: dict[str, Any],
    pack: dict[str, Any],
    pack_dir: Path,
    subject_id: str,
    case_id: str,
    case_dir: Path,
    case: dict[str, Any],
    repeat: int,
    attempt_dir: Path,
    adapter: CodexExecAdapter,
) -> dict[str, Any]:
    attempt_dir.mkdir(parents=True, exist_ok=False)
    workspace = attempt_dir / "workspace"
    subject = pack["subjects"][subject_id]
    prepare_workspace(
        case_dir=case_dir,
        subject=subject,
        pack_dir=pack_dir,
        workspace=workspace,
    )
    prompt = (case_dir / case["prompt_file"]).read_text(encoding="utf-8").strip()
    atomic_write_text(attempt_dir / "prompt.md", prompt + "\n")
    atomic_write_json(attempt_dir / "case.json", case)
    execution = _effective_execution(plan, case)
    attempt_id = attempt_dir.name
    input_identity = case_identity(case_dir, case)
    metadata: dict[str, Any] = {
        "schema_version": 1,
        "state": "running",
        "outcome": "pending",
        "run_id": plan["run_id"],
        "attempt_id": attempt_id,
        "pack_id": pack["pack_id"],
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
    atomic_write_text(attempt_dir / "final-output.md", trace_summary["final_message"] + "\n")
    file_results = evaluate_file_assertions(
        case,
        workspace,
        attempt_dir / "assertion-artifacts",
    )
    trace_results = evaluate_trace_assertions(case, trace_summary)
    final_changed_files = changed_files(workspace)
    atomic_write_text(attempt_dir / "diff.patch", capture_diff(workspace))
    verification = {
        "schema_version": 1,
        "passed": all(result["passed"] for result in file_results + trace_results),
        "file_assertions": file_results,
        "trace_assertions": trace_results,
        "changed_files": final_changed_files,
        "trace_summary": trace_summary,
    }
    atomic_write_json(attempt_dir / "verification.json", verification)

    if process_result.timed_out:
        outcome = "timeout"
    elif process_result.orphan_descendants:
        outcome = "error"
    elif process_result.return_code != 0:
        outcome = "error"
    elif verification["passed"]:
        outcome = "pass"
    else:
        outcome = "fail"

    metadata["state"] = "completed"
    metadata["outcome"] = outcome
    metadata["updated_at"] = utc_now()
    atomic_write_json(attempt_dir / "metadata.json", metadata)
    receipt = synthetic_receipt(
        run_id=plan["run_id"],
        attempt_id=attempt_id,
        pack_id=pack["pack_id"],
        case_id=case_id,
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

    if outcome == "pass" and not plan["execution"]["keep_workspace"]:
        shutil.rmtree(workspace)
    return metadata

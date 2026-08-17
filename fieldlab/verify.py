from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .io import safe_relative
from .process import run_bounded_process
from .workspace import changed_files


def assertion_result(assertion_type: str, passed: bool, message: str, **details: object) -> dict[str, Any]:
    result: dict[str, Any] = {
        "type": assertion_type,
        "passed": passed,
        "message": message,
    }
    if details:
        result["details"] = details
    return result


def evaluate_file_assertions(
    case: dict[str, Any],
    workspace: Path,
    assertion_artifacts: Path,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for index, assertion in enumerate(case["assertions"]):
        assertion_type = assertion["type"]
        if assertion_type == "changed_files_exact":
            actual = changed_files(workspace)
            expected = sorted(assertion["paths"])
            results.append(
                assertion_result(
                    assertion_type,
                    actual == expected,
                    "changed file set matches" if actual == expected else "changed file set differs",
                    expected=expected,
                    actual=actual,
                )
            )
            continue

        if assertion_type == "command":
            command_dir = assertion_artifacts / f"command-{index:03d}"
            env = os.environ.copy()
            env["PYTHONDONTWRITEBYTECODE"] = "1"
            execution = run_bounded_process(
                list(assertion["argv"]),
                cwd=workspace,
                stdout_path=command_dir / "stdout.log",
                stderr_path=command_dir / "stderr.log",
                timeout_seconds=float(assertion.get("timeout_seconds", 30)),
                env=env,
            )
            expected_code = int(assertion.get("exit_code", 0))
            stdout = (command_dir / "stdout.log").read_text(encoding="utf-8", errors="replace")[-20000:]
            stderr = (command_dir / "stderr.log").read_text(encoding="utf-8", errors="replace")[-20000:]
            passed = (
                execution.quiescent
                and not execution.timed_out
                and not execution.orphan_descendants
                and execution.return_code == expected_code
            )
            message = "command exit matched" if passed else "command assertion failed"
            results.append(
                assertion_result(
                    assertion_type,
                    passed,
                    message,
                    argv=assertion["argv"],
                    expected_exit_code=expected_code,
                    actual_exit_code=execution.return_code,
                    stdout=stdout,
                    stderr=stderr,
                    execution=execution.to_dict(),
                )
            )
            continue

        path = safe_relative(workspace, assertion["path"])
        if assertion_type == "file_exists":
            passed = path.is_file()
            results.append(
                assertion_result(
                    assertion_type,
                    passed,
                    "file exists" if passed else "file is missing",
                    path=assertion["path"],
                )
            )
            continue

        actual = path.read_text(encoding="utf-8") if path.is_file() else None
        value = assertion["value"]
        if assertion_type == "file_equals":
            passed = actual == value
            message = "file content matches" if passed else "file content differs"
        elif assertion_type == "file_contains":
            passed = actual is not None and value in actual
            message = "file contains value" if passed else "file does not contain value"
        else:
            passed = actual is not None and value not in actual
            message = "file omits forbidden value" if passed else "file contains forbidden value"
        results.append(
            assertion_result(
                assertion_type,
                passed,
                message,
                path=assertion["path"],
                expected=value,
                actual=actual,
            )
        )
    return results


def evaluate_trace_assertions(case: dict[str, Any], summary: dict[str, Any]) -> list[dict[str, Any]]:
    results = [
        assertion_result(
            "trace_jsonl_valid",
            summary["malformed_lines"] == 0,
            "trace JSONL is valid" if summary["malformed_lines"] == 0 else "trace has malformed lines",
            malformed_lines=summary["malformed_lines"],
        ),
        assertion_result(
            "trace_completed",
            bool(summary["thread_started"] and summary["turn_completed"] and not summary["errors"]),
            "thread completed without trace errors"
            if summary["thread_started"] and summary["turn_completed"] and not summary["errors"]
            else "thread completion evidence is incomplete",
            thread_started=summary["thread_started"],
            turn_completed=summary["turn_completed"],
            errors=summary["errors"],
        ),
    ]
    expectations = case.get("trace_assertions", {})
    metrics = {
        "max_command_executions": "command_executions",
        "max_plan_updates": "plan_updates",
        "max_subagent_events": "subagent_events",
    }
    for expectation, metric in metrics.items():
        if expectation not in expectations:
            continue
        maximum = int(expectations[expectation])
        actual = int(summary[metric])
        results.append(
            assertion_result(
                expectation,
                actual <= maximum,
                f"{metric} within limit" if actual <= maximum else f"{metric} exceeded limit",
                maximum=maximum,
                actual=actual,
            )
        )
    actual_references = set(summary["reference_reads"])
    for expected in expectations.get("reference_reads_include", []):
        passed = expected in actual_references
        results.append(
            assertion_result(
                "reference_reads_include",
                passed,
                "required reference observed" if passed else "required reference not observed",
                expected=expected,
                actual=sorted(actual_references),
            )
        )
    return results

from __future__ import annotations

import json
import os
import re
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


def _json_type_matches(value: object, expected: str) -> bool:
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "null":
        return value is None
    return False


def _json_schema_errors(value: object, schema: dict[str, Any], path: str = "$") -> list[str]:
    errors: list[str] = []
    expected_type = schema.get("type")
    if isinstance(expected_type, str) and not _json_type_matches(value, expected_type):
        return [f"{path}: expected {expected_type}"]
    if "const" in schema and value != schema["const"]:
        errors.append(f"{path}: value does not match const")
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: value is not in enum")
    if isinstance(value, str):
        minimum = schema.get("minLength")
        if isinstance(minimum, int) and len(value) < minimum:
            errors.append(f"{path}: string is shorter than minLength")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if isinstance(schema.get("minimum"), (int, float)) and value < schema["minimum"]:
            errors.append(f"{path}: number is below minimum")
        if isinstance(schema.get("maximum"), (int, float)) and value > schema["maximum"]:
            errors.append(f"{path}: number is above maximum")
    if isinstance(value, list):
        if isinstance(schema.get("minItems"), int) and len(value) < schema["minItems"]:
            errors.append(f"{path}: array is shorter than minItems")
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, item in enumerate(value):
                errors.extend(_json_schema_errors(item, item_schema, f"{path}[{index}]"))
    if isinstance(value, dict):
        required = schema.get("required", [])
        if isinstance(required, list):
            for key in required:
                if key not in value:
                    errors.append(f"{path}: missing required property {key}")
        properties = schema.get("properties", {})
        if isinstance(properties, dict):
            for key, property_schema in properties.items():
                if key in value and isinstance(property_schema, dict):
                    errors.extend(_json_schema_errors(value[key], property_schema, f"{path}.{key}"))
            if schema.get("additionalProperties") is False:
                for key in value:
                    if key not in properties:
                        errors.append(f"{path}: unexpected property {key}")
    return errors


def evaluate_result_assertions(case: dict[str, Any], final_response: str) -> list[dict[str, Any]]:
    assertions = case.get("result_assertions", {})
    results: list[dict[str, Any]] = []
    for expected in assertions.get("text_contains", []):
        passed = expected in final_response
        results.append(
            assertion_result(
                "text_contains",
                passed,
                "final response contains value" if passed else "final response omits value",
                expected=expected,
            )
        )
    for forbidden in assertions.get("text_not_contains", []):
        passed = forbidden not in final_response
        results.append(
            assertion_result(
                "text_not_contains",
                passed,
                "final response omits forbidden value" if passed else "final response contains forbidden value",
                forbidden=forbidden,
            )
        )
    for pattern in assertions.get("text_matches", []):
        passed = re.search(pattern, final_response) is not None
        results.append(
            assertion_result(
                "text_matches",
                passed,
                "final response matches pattern" if passed else "final response does not match pattern",
                pattern=pattern,
            )
        )
    schema = assertions.get("json_schema")
    if isinstance(schema, dict):
        try:
            value = json.loads(final_response)
        except json.JSONDecodeError as exc:
            results.append(
                assertion_result(
                    "json_schema",
                    False,
                    "final response is not valid JSON",
                    error=str(exc),
                )
            )
        else:
            errors = _json_schema_errors(value, schema)
            results.append(
                assertion_result(
                    "json_schema",
                    not errors,
                    "final response matches JSON schema" if not errors else "final response violates JSON schema",
                    errors=errors,
                )
            )
    return results


def _evaluate_assertion_list(
    assertions: list[dict[str, Any]],
    workspace: Path,
    assertion_artifacts: Path,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for index, assertion in enumerate(assertions):
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


def evaluate_workspace_assertions(
    case: dict[str, Any],
    workspace: Path,
    assertion_artifacts: Path,
) -> list[dict[str, Any]]:
    return _evaluate_assertion_list(
        list(case.get("workspace_assertions", [])),
        workspace,
        assertion_artifacts,
    )


def evaluate_command_assertions(
    case: dict[str, Any],
    workspace: Path,
    assertion_artifacts: Path,
) -> list[dict[str, Any]]:
    assertions = [
        assertion if assertion.get("type") == "command" else {"type": "command", **assertion}
        for assertion in case.get("command_assertions", [])
    ]
    return _evaluate_assertion_list(
        assertions,
        workspace,
        assertion_artifacts,
    )


def evaluate_file_assertions(
    case: dict[str, Any],
    workspace: Path,
    assertion_artifacts: Path,
) -> list[dict[str, Any]]:
    """Evaluate the deterministic workspace oracle used by lab self-test."""
    commands = [
        assertion if assertion.get("type") == "command" else {"type": "command", **assertion}
        for assertion in case.get("command_assertions", [])
    ]
    assertions = list(case.get("workspace_assertions", [])) + commands
    return _evaluate_assertion_list(assertions, workspace, assertion_artifacts)


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

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from .contracts import load_cases, load_lab
from .errors import ConfigError
from .verify import evaluate_file_assertions
from .workspace import apply_expected, prepare_workspace


def _failed(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [result for result in results if not result["passed"]]


def _coverage(case: dict[str, Any], *, applicable: bool) -> dict[str, Any]:
    surfaces = [
        "workspace_assertions", "command_assertions", "result_assertions",
        "trace_assertions", "human_review_requirements",
    ]
    exercised = [
        name for name in surfaces[:2] if applicable and case.get(name)
    ]
    return {
        "deterministic_oracle_status": "credible" if applicable else "not-applicable",
        "exercised_surfaces": exercised,
        "unexercised_surfaces": [name for name in surfaces if name not in exercised],
        "target_agent_invocations": 0,
    }


def selftest_lab(manifest_path: Path, case_ids: list[str] | None = None) -> dict[str, Any]:
    lab, lab_root, cases_root = load_lab(manifest_path)
    cases = load_cases(cases_root)
    selected = list(dict.fromkeys(case_ids or list(cases)))
    unknown = sorted(set(selected) - set(cases))
    if unknown:
        raise ConfigError(f"unknown cases: {', '.join(unknown)}")
    results: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="fieldlab-selftest-") as raw:
        root = Path(raw)
        for case_id in selected:
            case_dir, case = cases[case_id]
            expected = case_dir / "expected"
            if not expected.is_dir() or not any(path.is_file() for path in expected.rglob("*")):
                results.append(
                    {
                        "case_id": case_id,
                        **_coverage(case, applicable=False),
                        "oracle_status": "not-applicable",
                        "fixture_failed_assertions": 0,
                        "expected_assertions_passed": 0,
                    }
                )
                continue
            before_workspace = root / case_id / "before"
            prepare_workspace(
                case_dir=case_dir,
                subject={"kind": "control"},
                lab_root=lab_root,
                workspace=before_workspace,
            )
            before = evaluate_file_assertions(
                case,
                before_workspace,
                root / "assertions-before" / case_id,
            )
            if not _failed(before):
                raise ConfigError(
                    f"{case_id}: unresolved fixture unexpectedly satisfies every deterministic assertion"
                )

            expected_workspace = root / case_id / "expected"
            prepare_workspace(
                case_dir=case_dir,
                subject={"kind": "control"},
                lab_root=lab_root,
                workspace=expected_workspace,
            )
            apply_expected(expected, expected_workspace)
            after = evaluate_file_assertions(
                case,
                expected_workspace,
                root / "assertions-after" / case_id,
            )
            failures = _failed(after)
            if failures:
                raise ConfigError(f"{case_id}: expected overlay failed assertions: {failures}")
            results.append(
                {
                    "case_id": case_id,
                    **_coverage(case, applicable=True),
                    "oracle_status": "credible",
                    "fixture_failed_assertions": len(_failed(before)),
                    "expected_assertions_passed": len(after),
                }
            )
    return {
        "lab_id": lab["lab_id"],
        "cases": results,
        "target_agent_invocations": 0,
    }

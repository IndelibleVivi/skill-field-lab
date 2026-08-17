from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from .contracts import load_cases, load_pack
from .errors import ConfigError
from .verify import evaluate_file_assertions
from .workspace import apply_expected, prepare_workspace


def _failed(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [result for result in results if not result["passed"]]


def selftest_pack(pack_path: Path) -> dict[str, Any]:
    pack, _, cases_root = load_pack(pack_path)
    cases = load_cases(cases_root)
    results: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="fieldlab-pack-selftest-") as raw:
        root = Path(raw)
        for case_id, (case_dir, case) in cases.items():
            before_workspace = root / case_id / "before"
            prepare_workspace(
                case_dir=case_dir,
                subject={"overlays": []},
                pack_dir=case_dir,
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
                subject={"overlays": []},
                pack_dir=case_dir,
                workspace=expected_workspace,
            )
            apply_expected(case_dir / "expected", expected_workspace)
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
                    "fixture_failed_assertions": len(_failed(before)),
                    "expected_assertions_passed": len(after),
                }
            )
    return {
        "pack_id": pack["pack_id"],
        "cases": results,
        "target_agent_invocations": 0,
    }

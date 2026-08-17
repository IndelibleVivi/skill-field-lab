from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .contracts import load_cases, load_pack
from .errors import FieldLabError
from .io import atomic_write_json, read_json
from .plan import build_plan
from .receipts import observed_receipt
from .runner import run_plan
from .selftest import selftest_pack
from .snapshot import snapshot_git_tree


def _artifact(value: str) -> tuple[str, Path]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("artifact must use name=/path/to/file")
    name, raw_path = value.split("=", 1)
    if not name or "/" in name or "\\" in name:
        raise argparse.ArgumentTypeError("artifact name must be one simple label")
    path = Path(raw_path).expanduser().resolve()
    if not path.is_file():
        raise argparse.ArgumentTypeError(f"artifact file not found: {path}")
    return name, path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fieldlab",
        description="Evolve and evaluate reusable agent skills without hiding quota spend.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate", help="Validate a pack and all deterministic case contracts")
    validate.add_argument("pack", type=Path)

    list_command = subparsers.add_parser("list", help="List subjects and cases without invoking a target agent")
    list_command.add_argument("pack", type=Path)

    pack_selftest = subparsers.add_parser(
        "selftest-pack",
        help="Prove fixture-known-fail and expected-known-pass assertions without a target agent",
    )
    pack_selftest.add_argument("pack", type=Path)

    plan = subparsers.add_parser("plan", help="Build an immutable, no-spend execution plan")
    plan.add_argument("pack", type=Path)
    plan.add_argument("--subject", action="append", required=True)
    plan.add_argument("--case", action="append", required=True)
    plan.add_argument("--mode", choices=["canary", "matched", "environment-smoke"], default="canary")
    plan.add_argument("--repeat", type=int, default=1)
    plan.add_argument("--model")
    plan.add_argument("--reasoning-effort", choices=["minimal", "low", "medium", "high", "xhigh"])
    plan.add_argument("--codex-bin", default="codex")
    plan.add_argument("--run-id")
    plan.add_argument("--output-root")
    plan.add_argument("--timeout-seconds", type=int)
    plan.add_argument("--keep-workspace", action=argparse.BooleanOptionalAction, default=None)
    plan.add_argument("--output", type=Path, required=True)

    run = subparsers.add_parser("run", help="Execute a saved plan; requires an explicit live spend boundary")
    run.add_argument("plan", type=Path)
    run.add_argument("--live", action="store_true")
    run.add_argument("--max-invocations", type=int)
    run.add_argument("--resume", action="store_true")

    snapshot = subparsers.add_parser(
        "snapshot-git",
        help="Materialize one Git ref/path as a local subject overlay without invoking a target agent",
    )
    snapshot.add_argument("--repo", type=Path, required=True)
    snapshot.add_argument("--ref", required=True)
    snapshot.add_argument("--source", required=True)
    snapshot.add_argument("--output", type=Path, required=True)
    snapshot.add_argument("--replace", action="store_true")

    imported = subparsers.add_parser(
        "import-observed",
        help="Create a content-light receipt from existing dogfood without starting a target agent",
    )
    imported.add_argument("pack", type=Path)
    imported.add_argument("--case", required=True)
    imported.add_argument("--subject", required=True)
    imported.add_argument("--outcome", choices=["pass", "fail", "error", "inconclusive"], required=True)
    imported.add_argument("--artifact", action="append", type=_artifact, default=[])
    imported.add_argument("--note", required=True)
    imported.add_argument("--output", type=Path, required=True)
    return parser


def command_validate(pack_path: Path) -> int:
    pack, _, cases_root = load_pack(pack_path)
    cases = load_cases(cases_root)
    print(f"VALID {pack['pack_id']}: {len(pack['subjects'])} subjects, {len(cases)} cases")
    return 0


def command_selftest_pack(pack_path: Path) -> int:
    result = selftest_pack(pack_path)
    print(f"SELFTEST {result['pack_id']}: {len(result['cases'])} cases credible")
    for case in result["cases"]:
        print(
            f"  {case['case_id']}: fixture failed "
            f"{case['fixture_failed_assertions']} assertion(s); expected passed "
            f"{case['expected_assertions_passed']} assertion(s)"
        )
    print("Target-agent invocations: 0")
    return 0


def command_list(pack_path: Path) -> int:
    pack, _, cases_root = load_pack(pack_path)
    cases = load_cases(cases_root)
    print("Subjects:")
    for subject_id, subject in pack["subjects"].items():
        print(f"  {subject_id}\t{subject['attribution']}\t{subject['label']}")
    print("Cases:")
    for case_id, (_, case) in cases.items():
        print(f"  {case_id}\t{case['description']}")
    return 0


def command_plan(args: argparse.Namespace) -> int:
    plan = build_plan(
        pack_path=args.pack,
        subject_ids=args.subject,
        case_ids=args.case,
        mode=args.mode,
        repeat=args.repeat,
        model=args.model,
        reasoning_effort=args.reasoning_effort,
        codex_bin=args.codex_bin,
        run_id=args.run_id,
        output_root=args.output_root,
        timeout_override=args.timeout_seconds,
        keep_workspace=args.keep_workspace,
    )
    output = args.output.expanduser().resolve()
    atomic_write_json(output, plan)
    print(f"Plan: {output}")
    print(f"Mode: {plan['mode']}")
    print(f"Subjects: {len(plan['subjects'])}")
    print(f"Cases: {len(plan['cases'])}")
    print(f"Repeats: {plan['repeat']}")
    print(f"Target-agent invocations: {plan['target_invocations']}")
    print(f"LLM-grader invocations: {plan['llm_grader_invocations']}")
    selection = plan["execution"]
    print(f"Model selection: {selection['requested_model'] or 'ambient default (smoke only)'}")
    print(
        "Reasoning effort: "
        + (selection["requested_reasoning_effort"] or "ambient default (smoke only)")
    )
    print(f"Approval policy: {selection['approval_policy']}")
    print(f"Network access: {str(selection['network_access']).lower()}")
    pack, _, cases_root = load_pack(args.pack)
    cases = load_cases(cases_root)
    print("Subject attribution:")
    for subject_id in plan["subjects"]:
        print(f"  {subject_id}: {pack['subjects'][subject_id]['attribution']}")
    print("Case boundaries:")
    for case_id in plan["cases"]:
        case = cases[case_id][1]
        timeout = selection["timeout_override_seconds"] or case["timeout_seconds"]
        print(f"  {case_id}: sandbox={case['sandbox']}, timeout={timeout}s")
    adapter_request = plan["planned_inputs"]["adapter_executable"]
    if adapter_request["resolved_path"]:
        print(
            "Codex executable: "
            f"{adapter_request['resolved_path']} (sha256={adapter_request['sha256']})"
        )
    else:
        print(
            f"Codex executable: unresolved request {adapter_request['requested']!r}; "
            "install or select it, then create a new plan before live execution"
        )
    print("Pack/case/subject, Field Lab source, and available executable digests are pinned in planned_inputs.")
    print("No target agent was invoked.")
    return 0


def command_import(args: argparse.Namespace) -> int:
    pack, _, cases_root = load_pack(args.pack)
    cases = load_cases(cases_root)
    if args.case not in cases:
        raise FieldLabError(f"unknown case: {args.case}")
    if args.subject not in pack["subjects"]:
        raise FieldLabError(f"unknown subject: {args.subject}")
    artifacts = dict(args.artifact)
    if not artifacts:
        raise FieldLabError("import-observed requires at least one --artifact")
    if len(artifacts) != len(args.artifact):
        raise FieldLabError("artifact names must be unique")
    receipt = observed_receipt(
        pack_id=pack["pack_id"],
        case_id=args.case,
        subject_id=args.subject,
        subject=pack["subjects"][args.subject],
        outcome=args.outcome,
        artifacts=artifacts,
        note=args.note,
    )
    atomic_write_json(args.output.expanduser().resolve(), receipt)
    print(f"Observed receipt written: {args.output.expanduser().resolve()}")
    print("Target-agent invocations: 0")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "validate":
            return command_validate(args.pack)
        if args.command == "list":
            return command_list(args.pack)
        if args.command == "selftest-pack":
            return command_selftest_pack(args.pack)
        if args.command == "plan":
            return command_plan(args)
        if args.command == "run":
            return run_plan(
                args.plan,
                live=args.live,
                max_invocations=args.max_invocations,
                resume=args.resume,
            )
        if args.command == "snapshot-git":
            metadata = snapshot_git_tree(
                repo=args.repo,
                ref=args.ref,
                source_path=args.source,
                output=args.output,
                replace=args.replace,
            )
            print(f"Snapshot: {args.output.expanduser().resolve()}")
            print(f"Resolved commit: {metadata['resolved_commit']}")
            print("Target-agent invocations: 0")
            return 0
        return command_import(args)
    except (FieldLabError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

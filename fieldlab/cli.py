from __future__ import annotations

import argparse
import json
import os
import stat
import sys
from datetime import datetime, timezone
from pathlib import Path

from .contracts import load_cases, load_lab
from .doctor import doctor_report
from .explain import explain_claim, render_explanation
from .errors import ConfigError, FieldLabError
from .io import atomic_write_json, read_json
from .lab import initialize_lab, migrate_v1, promote_lab
from .plan import build_plan
from .receipts import CLAIM_ASSESSMENTS, human_review_record, observed_receipt_v2
from .records import validate_claim, validate_record_tree
from .runner import run_plan
from .selftest import selftest_lab
from .snapshot import snapshot_git_tree
from .subjects import declared_subject_scope

MAX_REQUIREMENT_OUTCOMES_BYTES = 1_000_000


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


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


def _require_unique_artifacts(values: list[tuple[str, Path]]) -> dict[str, Path]:
    artifacts = dict(values)
    if not artifacts:
        raise FieldLabError("observed evidence requires at least one --artifact")
    if len(artifacts) != len(values):
        raise FieldLabError("artifact names must be unique")
    return artifacts


def _absolute_user_path(path: Path) -> Path:
    expanded = path.expanduser()
    if not expanded.is_absolute():
        expanded = Path.cwd() / expanded
    return Path(os.path.normpath(str(expanded)))


def _reject_symlinked_user_ancestor(path: Path) -> None:
    """Refuse a user-controlled symlinked ancestor without rejecting `/var` style layout.

    A symlink that is a direct child of the filesystem root expresses the host's
    own layout (for example macOS `/var` -> `private/var`, or `/tmp`). Any deeper
    symlinked directory is user-controlled content and must not redirect the file
    Field Lab reads.
    """
    for parent in path.parents:
        if parent.parent == parent or parent.parent == Path(parent.anchor):
            continue
        if parent.is_symlink():
            raise ConfigError(
                "requirement outcomes must not sit below a user-controlled "
                f"symlinked directory: {parent}"
            )


def _read_requirement_outcomes(path: Path) -> dict[str, str]:
    target = _absolute_user_path(path)
    _reject_symlinked_user_ancestor(target)
    if target.is_symlink():
        raise ConfigError(
            "requirement outcomes must be a bounded regular JSON file"
        )
    # Open non-blocking so a FIFO or other non-regular file cannot stall the
    # command before the regular-file check below rejects it.
    open_flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    try:
        handle = os.open(target, open_flags)
    except OSError as exc:
        raise ConfigError(
            "requirement outcomes must be a bounded regular JSON file"
        ) from exc
    try:
        with os.fdopen(handle, "rb") as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                raise ConfigError(
                    "requirement outcomes must be a bounded regular JSON file"
                )
            raw = stream.read(MAX_REQUIREMENT_OUTCOMES_BYTES + 1)
    except OSError as exc:
        raise ConfigError(f"requirement outcomes could not be read: {exc}") from exc
    if len(raw) > MAX_REQUIREMENT_OUTCOMES_BYTES:
        raise ConfigError(
            "requirement outcomes must be a bounded regular JSON file"
        )
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ConfigError(
            f"requirement outcomes must be valid UTF-8: {exc}"
        ) from exc

    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ConfigError(f"duplicate requirement outcome key: {key}")
            result[key] = value
        return result

    try:
        value = json.loads(text, object_pairs_hook=unique_object)
    except json.JSONDecodeError as exc:
        raise ConfigError(f"invalid requirement outcomes JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise ConfigError("requirement outcomes JSON root must be an object")
    for key, outcome in value.items():
        if not isinstance(outcome, str) or outcome not in CLAIM_ASSESSMENTS:
            raise ConfigError(
                f"requirement outcome for {key!r} must be supported, "
                "not-supported, or inconclusive"
            )
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fieldlab",
        description=(
            "Study before you install. Test only what matters. "
            "A local workbench for claim-bounded reusable-agent evidence."
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    doctor = subparsers.add_parser("doctor", help="Check the installed app and controller Skills without invoking a target agent")
    doctor.add_argument("--skills-dir", type=Path)
    doctor.add_argument("--codex-bin", default="codex")
    doctor.add_argument("--json", action="store_true")

    init = subparsers.add_parser("init", help="Create an external local lab without modifying any subject")
    init.add_argument("directory", type=Path)
    init.add_argument("--lab-id")
    init.add_argument("--description")

    validate = subparsers.add_parser("validate", help="Validate a schema-v2 lab")
    validate.add_argument("manifest", type=Path)

    list_command = subparsers.add_parser("list", help="List subjects, cases, and record counts without invoking a target agent")
    list_command.add_argument("manifest", type=Path)

    selftest = subparsers.add_parser("selftest", help="Check deterministic expected overlays when present")
    selftest.add_argument("manifest", type=Path)
    selftest.add_argument("--case", action="append")

    snapshot = subparsers.add_parser("snapshot-git", help="Materialize one local Git ref/path without invoking a target agent")
    snapshot.add_argument("--repo", type=Path, required=True)
    snapshot.add_argument("--ref", required=True)
    snapshot.add_argument("--source", required=True)
    snapshot.add_argument("--output", type=Path, required=True)
    snapshot.add_argument("--replace", action="store_true")

    observe = subparsers.add_parser("observe", help="Bind existing ordinary-work evidence directly to a claim")
    observe.add_argument("manifest", type=Path)
    observe.add_argument("--subject", required=True)
    observe.add_argument("--claim", action="append", required=True)
    observe.add_argument("--case")
    observe.add_argument("--outcome", choices=["supported", "not-supported", "inconclusive"], required=True)
    observe.add_argument("--artifact", action="append", type=_artifact, default=[])
    observe.add_argument("--note", required=True)
    observe.add_argument("--output", type=Path)

    review = subparsers.add_parser("review", help="Create a separate human-review record for an immutable receipt")
    review.add_argument("manifest", type=Path)
    review.add_argument("--review-id", required=True)
    review.add_argument("--receipt", type=Path, required=True)
    review.add_argument(
        "--independence",
        choices=["implementer-run", "separate-agent", "external-reviewer"],
        required=True,
    )
    review.add_argument("--judgment", choices=["supported", "not-supported", "inconclusive"], required=True)
    review.add_argument("--rationale", required=True)
    review.add_argument(
        "--requirement-outcomes",
        type=Path,
        help=(
            "JSON object mapping every exact receipt review requirement to "
            "supported, not-supported, or inconclusive"
        ),
    )
    review.add_argument("--output", type=Path)

    explain = subparsers.add_parser(
        "explain",
        help="Read-only per-claim evidence explanation from receipts and reviews",
    )
    explain.add_argument("manifest", type=Path)
    explain.add_argument("--claim", required=True)
    explain.add_argument("--json", action="store_true")

    plan = subparsers.add_parser("plan", help="Build an immutable, no-spend execution plan")
    plan.add_argument("manifest", type=Path)
    plan.add_argument("--subject", action="append", required=True)
    plan.add_argument("--case", action="append", required=True)
    plan.add_argument("--mode", choices=["canary", "matched"], default="canary")
    plan.add_argument("--repeat", type=int, default=1)
    plan.add_argument("--model")
    plan.add_argument("--reasoning-effort", choices=["minimal", "low", "medium", "high", "xhigh"])
    plan.add_argument("--codex-bin", default="codex")
    plan.add_argument("--run-id")
    plan.add_argument("--output-root")
    plan.add_argument("--timeout-seconds", type=int)
    plan.add_argument("--keep-workspace", action=argparse.BooleanOptionalAction, default=None)
    plan.add_argument("--output", type=Path, required=True)

    run = subparsers.add_parser("run", help="Execute a saved plan across the explicit live spend boundary")
    run.add_argument("plan", type=Path)
    run.add_argument("--live", action="store_true")
    run.add_argument("--max-invocations", type=int)
    run.add_argument("--resume", action="store_true")

    promote = subparsers.add_parser("promote", help="Copy selected lab records into subject-owned evidence")
    promote.add_argument("--from", dest="source_lab", type=Path, required=True)
    promote.add_argument("--to", dest="destination", type=Path, required=True)
    promote.add_argument("--record", action="append")

    migrate = subparsers.add_parser("migrate-v1", help="Create a v2 lab and migration receipt without changing the v1 pack")
    migrate.add_argument("pack", type=Path)
    migrate.add_argument("--output", type=Path, required=True)

    return parser


def command_doctor(args: argparse.Namespace) -> int:
    report = doctor_report(skills_dir=args.skills_dir, codex_bin=args.codex_bin)
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True))
    else:
        print(f"Field Lab: {report['fieldlab_version']} ({report['fieldlab_source_sha256']})")
        print(f"Recognized install: {str(report['recognized_install']).lower()}")
        print(f"Python: {report['python']['version']} supported={str(report['python']['supported']).lower()}")
        print(f"Git: {report['git']['path'] or 'missing'}")
        print(f"Codex: {report['codex']['path'] or 'missing'}")
        print(f"POSIX live host: {str(report['host']['posix_live_supported']).lower()}")
        print(f"Skill discovery path: {report['skill_discovery_path']}")
        for name, status in report["controllers"].items():
            print(f"  {name}: installed={str(status['installed']).lower()} matches={str(status['matches_source']).lower()}")
        print("Target-agent invocations: 0")
    return 0 if report["ok"] else 1


def command_init(args: argparse.Namespace) -> int:
    manifest = initialize_lab(args.directory, lab_id=args.lab_id, description=args.description)
    print(f"Lab initialized: {manifest.parent}")
    print(f"Manifest: {manifest}")
    print("Subject repositories modified: 0")
    print("Target-agent invocations: 0")
    return 0


def command_validate(manifest_path: Path) -> int:
    lab, lab_root, cases_root = load_lab(manifest_path)
    cases = load_cases(cases_root, allow_empty=True)
    records = validate_record_tree(lab_root)
    print(
        f"VALID {lab['lab_id']}: schema=v2, "
        f"{len(lab['subjects'])} subjects, {len(cases)} cases"
    )
    if records:
        print("Records: " + ", ".join(f"{name}={count}" for name, count in records.items()))
    print("Target-agent invocations: 0")
    return 0


def command_list(manifest_path: Path) -> int:
    lab, _, cases_root = load_lab(manifest_path)
    cases = load_cases(cases_root, allow_empty=True)
    print("Subjects:")
    for subject_id in lab["subjects"]:
        scope = declared_subject_scope(lab["subjects"][subject_id])
        label = lab["subjects"][subject_id].get("label", subject_id)
        print(f"  {subject_id}\t{scope}\t{label}")
    print("Cases:")
    for case_id, (_, case) in cases.items():
        print(f"  {case_id}\tactivation={case['activation']}\t{case['description']}")
    print("Target-agent invocations: 0")
    return 0


def command_selftest(manifest_path: Path, case_ids: list[str] | None) -> int:
    result = selftest_lab(manifest_path, case_ids)
    print(f"SELFTEST {result['lab_id']}: {len(result['cases'])} cases checked")
    for case in result["cases"]:
        if case["oracle_status"] == "not-applicable":
            print(f"  {case['case_id']}: no deterministic expected overlay; contract valid")
        else:
            print(
                f"  {case['case_id']}: fixture failed {case['fixture_failed_assertions']} "
                f"assertion(s); expected passed {case['expected_assertions_passed']} assertion(s)"
            )
    print("Target-agent invocations: 0")
    return 0


def command_plan(args: argparse.Namespace) -> int:
    plan = build_plan(
        manifest_path=args.manifest,
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
    print(f"Lab: {plan['lab_id']} (manifest schema v2)")
    print(f"Mode: {plan['mode']}")
    print(f"Subjects: {len(plan['subjects'])}")
    print(f"Cases: {len(plan['cases'])}")
    print(f"Repeats: {plan['repeat']}")
    print(f"Target-agent invocations: {plan['target_invocations']}")
    print(f"LLM-grader invocations: {plan['llm_grader_invocations']}")
    selection = plan["execution"]
    print(f"Model selection: {selection['requested_model']}")
    print(f"Reasoning effort: {selection['requested_reasoning_effort']}")
    print(f"Approval policy: {selection['approval_policy']}")
    print(f"Network access: {str(selection['network_access']).lower()}")
    print("Invocations:")
    for index, item in enumerate(plan["matrix"], 1):
        scope = plan["planned_inputs"]["subjects"][item["subject_id"]]["subject_scope"]
        print(
            f"  {index}: subject={item['subject_id']} scope={scope} "
            f"case={item['case_id']} repeat={item['repeat']}"
        )
    adapter_request = plan["planned_inputs"]["adapter_executable"]
    if adapter_request["resolved_path"]:
        print(f"Codex executable: {adapter_request['resolved_path']} (sha256={adapter_request['sha256']})")
    else:
        print(
            f"Codex executable: unresolved request {adapter_request['requested']!r}; "
            "install or select it, then create a new plan before live execution"
        )
    print("Manifest/case/subject, Field Lab source, and available executable identities are pinned.")
    print("No target agent was invoked.")
    return 0


def command_observe(args: argparse.Namespace) -> int:
    lab, lab_root, cases_root = load_lab(args.manifest)
    if args.subject not in lab["subjects"]:
        raise FieldLabError(f"unknown subject: {args.subject}")
    claims: list[str] = []
    for claim_id in list(dict.fromkeys(args.claim)):
        path = lab_root / "claims" / f"{claim_id}.json"
        claim = validate_claim(read_json(path), str(path))
        if claim["subject_id"] != args.subject:
            raise FieldLabError(
                f"claim {claim_id} belongs to subject {claim['subject_id']}, not {args.subject}"
            )
        claims.append(claim_id)
    if args.case is not None:
        cases = load_cases(cases_root, allow_empty=True)
        if args.case not in cases:
            raise FieldLabError(f"unknown case: {args.case}")
    artifacts = _require_unique_artifacts(args.artifact)
    receipt = observed_receipt_v2(
        lab_id=lab["lab_id"],
        claim_ids=claims,
        case_id=args.case,
        subject_id=args.subject,
        subject=lab["subjects"][args.subject],
        assessment=args.outcome,
        artifacts=artifacts,
        note=args.note,
    )
    output = (
        args.output.expanduser().resolve()
        if args.output
        else lab_root / "receipts" / f"observed-{_stamp()}.json"
    )
    atomic_write_json(output, receipt)
    print(f"Observed receipt written: {output}")
    print("Target-agent invocations: 0")
    return 0


def command_review(args: argparse.Namespace) -> int:
    lab, lab_root, _ = load_lab(args.manifest)
    requirement_outcomes = (
        None
        if args.requirement_outcomes is None
        else _read_requirement_outcomes(args.requirement_outcomes)
    )
    record = human_review_record(
        review_id=args.review_id,
        receipt_path=args.receipt,
        independence=args.independence,
        judgment=args.judgment,
        rationale=args.rationale,
        requirement_outcomes=requirement_outcomes,
    )
    output = (
        args.output.expanduser().resolve()
        if args.output
        else lab_root / "reviews" / f"{args.review_id}.json"
    )
    if output == args.receipt.expanduser().resolve():
        raise ConfigError("review output must not overwrite its immutable receipt")
    atomic_write_json(output, record)
    print(f"Human review written: {output}")
    print(f"Receipt remained immutable: {record['receipt']['sha256']}")
    print("Target-agent invocations: 0")
    return 0


def command_explain(args: argparse.Namespace) -> int:
    explanation = explain_claim(args.manifest, args.claim)
    if args.json:
        print(json.dumps(explanation, indent=2, ensure_ascii=False, sort_keys=True))
        return 0
    print(render_explanation(explanation))
    print("Target-agent invocations: 0")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "doctor":
            return command_doctor(args)
        if args.command == "init":
            return command_init(args)
        if args.command == "validate":
            return command_validate(args.manifest)
        if args.command == "list":
            return command_list(args.manifest)
        if args.command == "selftest":
            return command_selftest(args.manifest, args.case)
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
        if args.command == "observe":
            return command_observe(args)
        if args.command == "review":
            return command_review(args)
        if args.command == "explain":
            return command_explain(args)
        if args.command == "promote":
            result = promote_lab(
                source_lab=args.source_lab,
                destination=args.destination,
                records=args.record,
            )
            print(f"Promoted {len(result['files'])} record files -> {result['destination']}")
            print(f"Promotion receipt: {result['receipt_path']}")
            print("Field Lab runtime promoted: false")
            print("Target-agent invocations: 0")
            return 0
        if args.command == "migrate-v1":
            result = migrate_v1(args.pack, args.output)
            print(f"Migrated manifest: {result['output_path']}")
            print(f"Migration receipt: {result['receipt_path']}")
            print("Source manifest modified: false")
            print("Target-agent invocations: 0")
            return 0
        parser.error(f"unsupported command: {args.command}")
    except (FieldLabError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

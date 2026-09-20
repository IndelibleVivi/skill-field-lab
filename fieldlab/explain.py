from __future__ import annotations

from pathlib import Path, PurePosixPath
from typing import Any

from .contracts import load_lab, resolve_local_path
from .errors import ConfigError
from .io import read_json_with_digest, sha256_file
from .receipts import load_review_records
from .records import validate_claim


ASSESSMENTS = ("supported", "not-supported", "inconclusive")
AGGREGATE_ASSESSMENTS = ASSESSMENTS + ("mixed",)
OUTCOME_ASSESSMENT = {
    "pass": "supported",
    "fail": "not-supported",
    "error": "inconclusive",
    "timeout": "inconclusive",
    "termination-failure": "inconclusive",
    "inconclusive": "inconclusive",
}
RECEIPT_TYPES = ("attempt", "observed")


def _relative_label(path: Path, lab_root: Path) -> str:
    try:
        return path.resolve().relative_to(lab_root.resolve()).as_posix()
    except ValueError:
        return str(path)


def _receipt_assessment(receipt: dict[str, Any]) -> str:
    if receipt.get("receipt_type") == "observed":
        assessment = receipt.get("claim_assessment")
        return assessment if assessment in ASSESSMENTS else "inconclusive"
    return OUTCOME_ASSESSMENT.get(str(receipt.get("outcome")), "inconclusive")


def _dimensions(receipt: dict[str, Any]) -> dict[str, Any]:
    evidence = receipt.get("evidence")
    if not isinstance(evidence, dict):
        return {}
    return {
        key: evidence.get(key)
        for key in (
            "origin",
            "subject_scope",
            "comparison",
            "verification_methods",
            "independence",
            "comparison_capable",
        )
    }


def _run_identity(receipt_path: Path, lab_root: Path) -> dict[str, Any] | None:
    for parent in receipt_path.parents:
        candidate = parent / "summary.json"
        if candidate.is_file():
            summary, _ = read_json_with_digest(candidate)
            identity = summary.get("identity")
            return identity if isinstance(identity, dict) else None
        if parent == lab_root:
            break
    return None


def _subject_identity(
    receipt: dict[str, Any],
    receipt_path: Path,
    lab_root: Path,
) -> dict[str, Any] | None:
    identity = _run_identity(receipt_path, lab_root)
    if identity is None:
        return None
    entries = identity.get("subjects")
    if not isinstance(entries, dict):
        return None
    subject = entries.get(receipt.get("subject_id"))
    return subject if isinstance(subject, dict) else None


def _artifact_name_error(name: object) -> bool:
    if not isinstance(name, str) or not name:
        return True
    path = PurePosixPath(name)
    return path.is_absolute() or ".." in path.parts or "." in path.parts


def _artifact_report(receipt_path: Path, receipt: dict[str, Any]) -> dict[str, Any]:
    artifacts = receipt.get("artifacts")
    if not isinstance(artifacts, dict):
        return {
            "recorded": 0,
            "intact": [],
            "missing": [],
            "drifted": [],
            "unverifiable": [],
        }
    if receipt.get("receipt_type") == "observed":
        # Observed receipts record a digest at observe time but never a path, so
        # the artifact bytes cannot be re-checked from the receipt alone.
        return {
            "recorded": len(artifacts),
            "intact": [],
            "missing": [],
            "drifted": [],
            "unverifiable": sorted(str(name) for name in artifacts),
        }
    intact: list[str] = []
    missing: list[str] = []
    drifted: list[str] = []
    unverifiable: list[str] = []
    for name, entry in sorted(artifacts.items()):
        if _artifact_name_error(name):
            unverifiable.append(str(name))
            continue
        target = receipt_path.parent / name
        if target.is_symlink() or not target.is_file():
            missing.append(name)
            continue
        expected = entry.get("sha256") if isinstance(entry, dict) else None
        if not isinstance(expected, str):
            unverifiable.append(name)
        elif sha256_file(target) != expected:
            drifted.append(name)
        else:
            intact.append(name)
    return {
        "recorded": len(artifacts),
        "intact": intact,
        "missing": missing,
        "drifted": drifted,
        "unverifiable": unverifiable,
    }


def _boundary(receipt: dict[str, Any]) -> str | None:
    if receipt.get("outcome") in {"input-drift", "preflight-failed"}:
        return "pre-invocation"
    if receipt.get("receipt_type") != "attempt":
        return None
    summary = receipt.get("verification_summary")
    summary = summary if isinstance(summary, dict) else {}
    worker_final = summary.get("worker_final")
    return "sealed-before-verifier" if isinstance(worker_final, dict) else "legacy-ambiguous"


def _review_view(path: Path, record: dict[str, Any], lab_root: Path) -> dict[str, Any]:
    return {
        "review_id": record.get("review_id"),
        "path": _relative_label(path, lab_root),
        "independence": record.get("independence"),
        "judgment": record.get("judgment"),
        "requirement_outcomes": record.get("requirement_outcomes", {}),
        "created_at": record.get("created_at"),
    }


def _split_reviews(
    receipt_digest: str,
    receipt_path: Path,
    reviews: list[tuple[Path, dict[str, Any]]],
    lab_root: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    bound: list[dict[str, Any]] = []
    stale: list[dict[str, Any]] = []
    for path, record in reviews:
        binding = record.get("receipt", {})
        if binding.get("sha256") == receipt_digest:
            bound.append(_review_view(path, record, lab_root))
            continue
        try:
            same_path = Path(str(binding.get("path"))).expanduser().resolve() == receipt_path
        except (TypeError, ValueError):
            same_path = False
        if same_path:
            stale.append(
                {
                    "review_id": record.get("review_id"),
                    "path": _relative_label(path, lab_root),
                    "declared_receipt_sha256": binding.get("sha256"),
                    "current_receipt_sha256": receipt_digest,
                }
            )
    bound.sort(key=lambda item: (str(item.get("created_at", "")), str(item.get("path", ""))))
    stale.sort(key=lambda item: str(item.get("path", "")))
    return bound, stale


def _requirements(
    receipt: dict[str, Any],
    bound_reviews: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    summary = receipt.get("verification_summary")
    human = summary.get("human_review") if isinstance(summary, dict) else None
    declared = human.get("requirements") if isinstance(human, dict) else []
    if not isinstance(declared, list):
        declared = []
    report: list[dict[str, Any]] = []
    for requirement in declared:
        outcomes: list[str] = []
        missing_reviews: list[str] = []
        for review in bound_reviews:
            review_outcomes = review.get("requirement_outcomes")
            if isinstance(review_outcomes, dict) and requirement in review_outcomes:
                outcomes.append(str(review_outcomes[requirement]))
            else:
                missing_reviews.append(str(review.get("review_id")))
        distinct = set(outcomes)
        if not outcomes:
            status = "pending"
        elif len(distinct) == 1 and not missing_reviews:
            status = next(iter(distinct))
        elif len(distinct) == 1:
            # Some bound reviews disagree about whether the requirement applies.
            status = "mixed"
        else:
            status = "mixed"
        if status != "pending" and status not in AGGREGATE_ASSESSMENTS:
            status = "inconclusive"
        report.append(
            {
                "requirement": requirement,
                "status": status,
                "outcomes": sorted(distinct),
                "reviews": [str(review.get("review_id")) for review in bound_reviews],
            }
        )
    return report


def _receipt_view(
    receipt_path: Path,
    locations: list[Path],
    receipt: dict[str, Any],
    receipt_digest: str,
    reviews: list[tuple[Path, dict[str, Any]]],
    lab_root: Path,
) -> dict[str, Any]:
    bound, stale = _split_reviews(receipt_digest, receipt_path, reviews, lab_root)
    if bound:
        fingerprints = {
            (
                str(review.get("judgment")),
                tuple(sorted(dict(review.get("requirement_outcomes") or {}).items())),
            )
            for review in bound
        }
        if len(fingerprints) > 1:
            assessment = "mixed"
        else:
            assessment = str(bound[0].get("judgment"))
            if assessment not in ASSESSMENTS:
                assessment = "inconclusive"
    else:
        assessment = _receipt_assessment(receipt)
    summary = receipt.get("verification_summary")
    summary = summary if isinstance(summary, dict) else {}
    subject = _subject_identity(receipt, receipt_path, lab_root)
    payload_identity = None
    if isinstance(subject, dict):
        payload_identity = subject.get("payload_sha256") or subject.get("payload")
    return {
        "path": _relative_label(receipt_path, lab_root),
        "locations": [_relative_label(path, lab_root) for path in locations],
        "receipt_sha256": receipt_digest,
        "receipt_type": receipt.get("receipt_type"),
        "subject_id": receipt.get("subject_id"),
        "case_id": receipt.get("case_id"),
        "outcome": receipt.get("outcome"),
        "claim_assessment": receipt.get("claim_assessment"),
        "boundary": _boundary(receipt),
        "assessment": assessment,
        "conflicting": assessment == "mixed",
        "dimensions": _dimensions(receipt),
        "identity_sha256": receipt.get("identity_sha256"),
        "inputs": receipt.get("inputs"),
        "subject_identity": subject,
        "subject_delivery": receipt.get("subject_delivery", {"status": "unknown"}),
        "trace_evidence_semantics": "command-path mentions only; reference_reads_include is a deprecated alias",
        "host_selection": receipt.get("host_selection", {"status": "unknown"}),
        "content_application": receipt.get(
            "content_application", {"status": "requires-semantic-review"}
        ),
        "payload_identity": payload_identity,
        "worker_final": summary.get("worker_final"),
        "review_material": summary.get("review_material"),
        "verifier": summary.get("verifier"),
        "retention": summary.get("retention"),
        "artifacts": _artifact_report(receipt_path, receipt),
        "requirements": _requirements(receipt, bound),
        "reviews": bound,
        "stale_reviews": stale,
    }


def _claim_receipts(
    lab_root: Path,
    output_root: Path,
    claim_id: str,
) -> list[dict[str, Any]]:
    candidates: list[Path] = []
    receipts_dir = lab_root / "receipts"
    if receipts_dir.is_dir():
        candidates.extend(sorted(path for path in receipts_dir.rglob("*.json") if path.is_file()))
    if output_root.is_dir():
        candidates.extend(sorted(output_root.rglob("receipt.json")))
    by_digest: dict[str, dict[str, Any]] = {}
    seen_paths: set[Path] = set()
    for path in candidates:
        if path in seen_paths:
            continue
        seen_paths.add(path)
        receipt, digest = read_json_with_digest(path)
        if receipt.get("receipt_type") not in RECEIPT_TYPES:
            continue
        claim_ids = receipt.get("claim_ids")
        if not isinstance(claim_ids, list) or claim_id not in claim_ids:
            continue
        if digest in by_digest:
            # The same receipt copied or promoted to another canonical location
            # is one piece of evidence with several readable locations.
            by_digest[digest]["locations"].append(path)
            continue
        by_digest[digest] = {
            "digest": digest,
            "receipt": receipt,
            "locations": [path],
        }
    groups = list(by_digest.values())
    for group in groups:
        group["locations"].sort(
            key=lambda path: (_relative_label(path, lab_root), str(path))
        )
        group["primary"] = group["locations"][0]
        created = group["receipt"].get("created_at")
        group["created_at"] = str(created) if isinstance(created, str) else ""
    return sorted(groups, key=lambda group: (group["created_at"], group["digest"]))


def _collect(entries: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    collected: list[dict[str, Any]] = []
    for entry in entries:
        for item in entry[key]:
            collected.append({**item, "receipt": entry["path"]})
    return collected


def _next_gap(
    claim_id: str,
    entries: list[dict[str, Any]],
    verdict: str,
    mixed: list[dict[str, Any]],
    unsupported: list[dict[str, Any]],
    pending: list[dict[str, Any]],
    failed: list[dict[str, Any]],
    drifted: list[dict[str, Any]],
    legacy_only: list[dict[str, Any]],
) -> str:
    if not entries:
        return (
            f"No receipt binds to {claim_id}: record ordinary-work evidence with "
            "`fieldlab observe`, or build a no-spend plan for one canary case."
        )
    if mixed:
        return (
            "Conflicting bound reviews exist for "
            + ", ".join(entry["path"] for entry in mixed)
            + "; record one superseding review or a new receipt instead of choosing "
            "a side."
        )
    if unsupported:
        return (
            "Contradicting evidence exists in "
            + ", ".join(entry["path"] for entry in unsupported)
            + "; supersede it with a new run or address it in a separate review."
        )
    if pending:
        return f"Pending human-review requirement: {pending[0]['requirement']}"
    if failed:
        return (
            f"Review requirement not supported: {failed[0]['requirement']}; "
            "add a separate reviewer or new evidence."
        )
    if drifted:
        entry = drifted[0]
        names = entry["artifacts"]["missing"] + entry["artifacts"]["drifted"]
        return (
            f"Missing or digest-drifted artifact {names} in {entry['path']}; "
            "restore it or re-run the pinned case."
        )
    if legacy_only:
        return (
            "Only legacy receipts without the worker-final boundary marker support "
            "this claim; re-run under the sealed-before-verifier boundary, or bind "
            "a review that names that ambiguity."
        )
    supported = [entry for entry in entries if entry["assessment"] == "supported"]
    reviewed = [
        review
        for entry in entries
        for review in entry["reviews"]
        if review.get("independence") in {"separate-agent", "external-reviewer"}
    ]
    if supported and not reviewed:
        return (
            "No separate review is bound; a separate-agent review of the sealed "
            "receipt is the smallest remaining independence gap."
        )
    if supported and all(
        entry["dimensions"].get("comparison") != "matched" for entry in supported
    ):
        return (
            "Evidence is single/unmatched; a matched isolated-control comparison is "
            "the smallest remaining comparison gap."
        )
    if verdict == "supported":
        return (
            "No evidence gap identified for this claim; installed bytes, discovery, "
            "live behavior, and owner acceptance remain separate gates."
        )
    return "Add or bind comparable evidence, then re-run `fieldlab explain`."


def explain_claim(manifest_path: Path, claim_id: str) -> dict[str, Any]:
    """Compute one claim's evidence view from receipts and reviews, read-only."""

    lab, lab_root, _ = load_lab(manifest_path, require_subject_sources=False)
    claim_path = lab_root / "claims" / f"{claim_id}.json"
    if not claim_path.is_file():
        raise ConfigError(f"unknown claim: {claim_id}")
    claim, _ = read_json_with_digest(claim_path)
    claim = validate_claim(claim, str(claim_path))
    output_root = resolve_local_path(lab_root, lab["defaults"]["output_root"])
    reviews = load_review_records(lab_root)
    entries = [
        _receipt_view(
            group["primary"],
            group["locations"],
            group["receipt"],
            group["digest"],
            reviews,
            lab_root,
        )
        for group in _claim_receipts(lab_root, output_root, claim_id)
    ]
    requirements = _collect(entries, "requirements")
    mixed_entries = [entry for entry in entries if entry["assessment"] == "mixed"]
    unsupported_entries = [
        entry for entry in entries if entry["assessment"] == "not-supported"
    ]
    inconclusive_entries = [
        entry for entry in entries if entry["assessment"] == "inconclusive"
    ]
    supported_entries = [entry for entry in entries if entry["assessment"] == "supported"]
    pending = [item for item in requirements if item["status"] == "pending"]
    failed = [item for item in requirements if item["status"] in {"not-supported", "inconclusive"}]
    mixed_requirements = [item for item in requirements if item["status"] == "mixed"]
    drifted = [
        entry
        for entry in entries
        if entry["artifacts"]["missing"] or entry["artifacts"]["drifted"]
    ]
    # A legacy receipt stays readable, but it is never presented as proof that
    # worker bytes were sealed before a verifier ran.
    legacy_supported = [
        entry
        for entry in supported_entries
        if entry["boundary"] == "legacy-ambiguous"
    ]
    sealed_supported = [
        entry
        for entry in supported_entries
        if entry["boundary"] != "legacy-ambiguous"
    ]
    legacy_only = legacy_supported if supported_entries and not sealed_supported else []
    if mixed_entries or mixed_requirements:
        verdict = "mixed"
    elif unsupported_entries or any(item["status"] == "not-supported" for item in failed):
        verdict = "unsupported"
    elif pending or failed or drifted or inconclusive_entries or legacy_only:
        verdict = "inconclusive"
    elif sealed_supported:
        verdict = "supported"
    else:
        verdict = "inconclusive"
    return {
        "schema_version": 2,
        "lab_id": lab["lab_id"],
        "claim_id": claim_id,
        "subject_id": claim["subject_id"],
        "statement": claim["statement"],
        "declared_status": claim["status"],
        "declared_status_is_not_evidence": True,
        "derived_verdict": verdict,
        "counts": {
            "receipts": len(entries),
            "supported": len(supported_entries),
            "unsupported": len(unsupported_entries),
            "inconclusive": len(inconclusive_entries),
            "mixed": len(mixed_entries),
            "legacy_ambiguous_receipts": len(legacy_supported),
            "pending_requirements": len(pending),
            "failed_requirements": len(failed),
            "mixed_requirements": len(mixed_requirements),
            "missing_or_drifted_receipts": len(drifted),
        },
        "supported_receipts": [entry["path"] for entry in supported_entries],
        "unsupported_receipts": [entry["path"] for entry in unsupported_entries],
        "inconclusive_receipts": [entry["path"] for entry in inconclusive_entries],
        "mixed_receipts": [entry["path"] for entry in mixed_entries],
        "legacy_ambiguous_receipts": [entry["path"] for entry in legacy_supported],
        "pending_requirements": pending,
        "failed_requirements": failed,
        "mixed_requirements": mixed_requirements,
        "missing_or_drifted": [
            {
                "receipt": entry["path"],
                "missing": entry["artifacts"]["missing"],
                "drifted": entry["artifacts"]["drifted"],
            }
            for entry in drifted
        ],
        "stale_reviews": _collect(entries, "stale_reviews"),
        "next_gap": _next_gap(
            claim_id,
            entries,
            verdict,
            mixed_entries,
            unsupported_entries,
            pending,
            failed,
            drifted,
            legacy_only,
        ),
        "target_agent_invocations": 0,
        "receipts": entries,
    }


def render_explanation(view: dict[str, Any]) -> str:
    lines = [
        f"Claim: {view['claim_id']} (declared status: {view['declared_status']})",
        f"Subject: {view['subject_id']}",
        f"Statement: {view['statement']}",
        "Trace references are command-path mentions, not proof of content reads. "
        "reference_reads_include is a deprecated alias for command_reference_mentions_include.",
        "",
        "Derived evidence view (from receipts and reviews, not claim.status):",
        f"  verdict: {view['derived_verdict']}",
        f"  supported receipts: {view['counts']['supported']}",
        f"  unsupported receipts: {view['counts']['unsupported']}",
        f"  inconclusive receipts: {view['counts']['inconclusive']}",
        f"  mixed receipts: {view['counts']['mixed']}",
        f"  legacy-ambiguous receipts: {view['counts']['legacy_ambiguous_receipts']}",
        f"  pending review requirements: {view['counts']['pending_requirements']}",
        f"  failed review requirements: {view['counts']['failed_requirements']}",
        f"  mixed review requirements: {view['counts']['mixed_requirements']}",
        f"  missing or digest-drifted receipts: {view['counts']['missing_or_drifted_receipts']}",
    ]
    if view["receipts"]:
        lines.append("")
        lines.append("Bound receipts:")
    for index, entry in enumerate(view["receipts"], 1):
        dimensions = entry["dimensions"]
        provenance = ", ".join(f"{key}={dimensions.get(key)}" for key in dimensions)
        lines.append(f"  {index}. {entry['path']}")
        lines.append(
            f"     type={entry['receipt_type']} outcome={entry['outcome']} "
            f"assessment={entry['assessment']}"
        )
        lines.append(f"     dimensions: {provenance}")
        if entry["boundary"] == "legacy-ambiguous":
            lines.append(
                "     boundary: legacy-ambiguous (no worker-final boundary marker; "
                "not proven sealed before verifier)"
            )
        elif entry["boundary"] == "pre-invocation":
            lines.append("     boundary: pre-invocation (target was not started)")
        elif entry["boundary"]:
            lines.append("     boundary: sealed-before-verifier")
        lines.append(f"     subject delivery: {entry['subject_delivery']}")
        lines.append(f"     host selection: {entry['host_selection']}")
        lines.append(f"     content application: {entry['content_application']}")
        if len(entry["locations"]) > 1:
            lines.append(f"     locations: {entry['locations']}")
        if entry["subject_identity"]:
            subject = entry["subject_identity"]
            source = subject.get("source", {}) if isinstance(subject, dict) else {}
            lines.append(
                "     subject identity: "
                + ", ".join(f"{key}={value}" for key, value in source.items())
            )
        if entry["payload_identity"]:
            lines.append(f"     payload identity: {entry['payload_identity']}")
        if entry["worker_final"]:
            worker = entry["worker_final"]
            lines.append(
                "     worker-final: "
                f"changed_files={worker.get('changed_files')} "
                f"tree_sha256={worker.get('tree_sha256')}"
            )
        if entry["review_material"]:
            material = entry["review_material"]
            lines.append(
                "     review material: "
                f"status={material.get('status')} "
                f"manifest={material.get('manifest')} "
                f"files={[item.get('path') for item in material.get('files', [])]}"
            )
        if entry["verifier"]:
            verifier = entry["verifier"]
            lines.append(
                "     verifier: "
                f"copies={verifier.get('command_assertions')} "
                f"fresh_copy_per_command={str(verifier.get('fresh_copy_per_command')).lower()} "
                f"mutated_worker_output={str(verifier.get('mutated_worker_output')).lower()} "
                f"derived_changed_files={verifier.get('derived_changed_files')}"
            )
        if entry["retention"]:
            retention = entry["retention"]
            lines.append(
                "     retention: "
                f"workspace_retained={str(retention.get('workspace_retained')).lower()} "
                f"reason={retention.get('reason')}"
            )
        artifacts = entry["artifacts"]
        lines.append(
            "     artifacts: "
            f"intact={len(artifacts['intact'])} "
            f"missing={artifacts['missing']} "
            f"drifted={artifacts['drifted']}"
        )
        for review in entry["reviews"]:
            lines.append(
                "     review: "
                f"{review['review_id']} independence={review['independence']} "
                f"judgment={review['judgment']}"
            )
        for stale in entry["stale_reviews"]:
            lines.append(f"     stale review (digest drift): {stale['review_id']}")
    if view["pending_requirements"]:
        lines.append("")
        lines.append("Pending review requirements:")
        for item in view["pending_requirements"]:
            lines.append(f"  - {item['requirement']} (receipt {item['receipt']})")
    if view["failed_requirements"]:
        lines.append("")
        lines.append("Failed review requirements:")
        for item in view["failed_requirements"]:
            lines.append(
                f"  - {item['requirement']}: {item['status']} "
                f"(receipt {item['receipt']})"
            )
    if view["mixed_requirements"]:
        lines.append("")
        lines.append("Conflicting review requirements:")
        for item in view["mixed_requirements"]:
            lines.append(
                f"  - {item['requirement']}: outcomes={item['outcomes']} "
                f"(receipt {item['receipt']})"
            )
    if view["missing_or_drifted"]:
        lines.append("")
        lines.append("Missing or digest-drifted artifacts:")
        for item in view["missing_or_drifted"]:
            lines.append(
                f"  - {item['receipt']}: missing={item['missing']} drifted={item['drifted']}"
            )
    lines.append("")
    lines.append(f"Smallest next evidence gap: {view['next_gap']}")
    return "\n".join(lines)

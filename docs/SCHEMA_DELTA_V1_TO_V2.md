# Schema delta: v1 pack to v2 lab

Status: normative companion to
[PRODUCT_SPEC_V0.2.md](PRODUCT_SPEC_V0.2.md).

## Authority change

```text
v1: pack -> candidate/provisional decision -> claim -> case -> ... -> decision
v2: source -> candidate -> claim -> [case -> plan -> attempt -> receipt] -> decision
```

The v2 execution chain is optional. Decision is the only record that owns the
final `ADOPT | ADAPT | REJECT | DEFER | ALREADY COVERED` disposition.

## Manifest

| V1 | V2 |
| --- | --- |
| `schema_version: 1` | `schema_version: 2` |
| `pack_id` | `lab_id` |
| subject `attribution` + in-pack `overlays` | subject `kind` + structured local `source` + optional `mount` |
| overlay source constrained to pack directory | `local-path` may resolve outside the lab; all sources are pinned |
| `fieldlab-pack.json` primary entry | `fieldlab.json` only active entry; v1 is migration input only |

Defaults keep the same safety meaning. V0.2 still supports only
`adapter: codex-exec`, `read-only`/`workspace-write`, explicit approvals, and a
boolean network boundary.

## Candidate v2

Required meaning:

- structured `source` and exact `pin`;
- `reviewed_files[]` and `source_observations[]`;
- one `distilled_mechanism`;
- nullable `local_problem`;
- `local_fit`, `landing_plane`, and `open_questions[]`.

Removed authority:

- no `decision`;
- no final `accepted_kernel` or `excluded_machinery`;
- no candidate-owned final reopen condition.

## Claim v2

```text
statement
observable_delta
preserved_behaviors[]
sufficient_evidence[]
status
```

The v1 `observable`, `adjacent_control`, and scalar `sufficient_evidence` map
forward without changing the source record.

## Case v2

A case keeps one prompt and bounded execution settings, and adds:

- `activation: implicit | explicit | direct`;
- `result_assertions` for final-response text, regex, or structured JSON;
- `workspace_assertions` for file and changed-file behavior;
- `command_assertions` for bounded repository-owned commands;
- `trace_assertions` for raw execution telemetry; and
- `human_review_requirements[]` for declared non-deterministic judgment.

`fixture/` and `expected/` are optional. A deterministic expected overlay is a
self-test oracle when present; it is not required merely to make a case valid.
The legacy v1 `assertions[]` list is translated into v2 workspace/command
assertions by the one-shot migrator.

## Receipt v2

- `lab_id` replaces `pack_id`.
- `subject_scope` replaces evidence-dimension `attribution`.
- `verification_methods[]` replaces scalar `verification`.
- `claim_ids[]` is explicit; observed receipts require at least one claim.
- `case_id` is optional for observed evidence and required for attempts.
- outcome is one of `pass`, `fail`, `error`, `timeout`,
  `termination-failure`, or `inconclusive`.
- human-review requirements and pending status may be recorded without claiming
  that human verification already occurred.

## Review v2

A review is a separate immutable record containing:

- `review_id`, timestamp, reviewer independence, and method;
- the target receipt path and SHA-256 digest;
- `supported | not-supported | inconclusive` judgment;
- rationale and an exact outcome for each declared human-review requirement.

The outcome mapping is empty only when the receipt declares no requirements.
Each value is `supported`, `not-supported`, or `inconclusive`; missing, extra,
duplicate, or unsupported entries fail closed.

The receipt is never reopened or edited to add the review.

## Decision v2

Decision owns:

- final disposition and rationale;
- accepted kernel and excluded machinery;
- evidence references;
- landing plane and local delta; and
- reopen condition.

Evidence references may point to source-inspection records, observed receipts,
synthetic receipts, or separate human reviews.

## Migration-only boundary

- V0.2 normal commands reject schema-v1 packs. There is no dual runtime,
  environment-smoke path, or alias layer.
- `fieldlab migrate-v1 <fieldlab-pack.json> --output <fieldlab.json>` writes a
  new v2 manifest and migration receipt; it never changes or deletes the v1
  source.
- V1 overlay subjects become v2 `snapshot` sources copied into a migration-owned
  `subjects/` directory beside the new manifest. This preserves out-of-pack
  safety while avoiding a false external-source claim.
- V1 cases are rewritten to schema v2 during migration. The output can then use
  the same canonical `validate`, `selftest`, `plan`, and `run` paths as every
  other lab.

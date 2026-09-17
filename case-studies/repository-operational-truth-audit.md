# Repository Operational Truth Audit case study

Observed source identity: `a51f665d888f068cb6b42bf9572146be18540318`
on 2026-08-30. This is dated evidence, not an undated current-state claim.

## Orthogonal subject boundary

Repository Operational Truth Audit, displayed as **Repo Truth Audit**, is a
standalone read-only Skill for one concrete repository-state decision. Its own
repository owns `skills/repository-operational-truth-audit/`, product/evidence
contracts, six controlled case directories at the observed identity,
installation, validation, and release cadence.

Its repository explicitly describes Skill Field Lab as optional evaluation
infrastructure—not a runtime dependency and not an owner of the Skill. Field
Lab therefore stores no copy of its Skill or case fixtures.

## V0.2 integration

The dated source identity still carries a schema-v1 `fieldlab-pack.json`. A
disposable external migration is the current no-write route:

```bash
fieldlab migrate-v1 /path/to/repo-truth-audit/fieldlab-pack.json \
  --output /path/to/external-rot-lab/fieldlab.json

fieldlab validate /path/to/external-rot-lab/fieldlab.json
fieldlab selftest /path/to/external-rot-lab/fieldlab.json
```

The external lab can then build a no-spend canary or matched plan. Any live
attempt still needs its own selected case, requested model/effort, saved plan,
`--live`, and exact invocation cap.

## Existing real evidence

The subject repository publishes `docs/forward-behavior-receipt.md`, observed
2026-08-30. It reports two independent read-only forward runs:

- `source-artifact-split` found that a selected distribution artifact remained
  stale while a source-only test stayed green; and
- `intentional-multiplicity` correctly preserved explicitly selected stable and
  development routes as a clean result.

The public receipt is useful observed evidence. Its boundary is also explicit:
target-subject Git ref, model, effort, command counts, and plan counts were not
retained; there is no standalone raw event trace; installed runtime and owner
acceptance were not observed.

It has not been relabelled as a Field Lab v2 synthetic receipt, deterministic
trace verification, matched comparison, or provider-proven model identity. It
remains a separate observed-evidence surface with the unknowns above.

## Controlled v0.2 release receipt

On 2026-08-30, a fresh private external v2 lab migrated the dated source pack,
validated it, and self-tested all six cases before any target invocation. It
then saved and inspected run `rot-ac10-v020` with exactly this matrix:

- case `source-artifact-split`, current-Skill snapshot, canary, repeat one;
- one target invocation, zero LLM graders, no retry or resume;
- requested `gpt-5.6-sol` / `high` as caller-selection evidence only;
- approval `never`, workspace-write sandbox, and network disabled.

Exactly one target invocation ran and passed. The target received the ordinary
case prompt, not expected artifacts or evaluator assertions. After worker exit,
deterministic verification confirmed that the source-only test stayed green,
the manifest-selected `dist/cli.py` printed `artifact-v1`, and `AUDIT.md` named
the `artifact-v1` / `artifact-v2` identity split plus a not-ready operator
handoff decision. Only `AUDIT.md` changed. The retained trace was valid and
complete with five command executions, zero plan updates, and zero subagent
events. The process exited zero, became quiescent without orphan descendants,
and its disposable workspace was removed.

The immutable attempt receipt SHA-256 is
`28be5f49de1bcf9de8c49be1fbf9027787c145ed6babf9b28cd2c6cc2a17563e`.
A separate `implementer-run` human review, SHA-256
`8837beaf0a928aa534d259af30ed49536fe6a1f92decc1d2b3f6d11d03301b87`,
judged only the pinned synthetic false-green claim supported. The receipt does
not claim provider-resolved model identity or exclusive subject causality.

Raw stderr retained host-startup warnings about shortened skills descriptions
and unavailable MCP OAuth. The selected ROT Skill itself was read in full, the
target used neither MCP nor network, deterministic verification passed, and
the warnings are not promoted into evidence claims.

Before and after the run, the canonical subject remained at the source identity
above with a clean worktree. Raw trace, stderr, absolute local paths, and local
whole-checkout digests remain outside Git.

## Evidence ceiling

The controlled receipt supports one synthetic public repository shape under
the pinned prompt, case, subject snapshot, executable, permissions, and
assertions. The separate review adds a human claim ceiling, not independence.
It does not prove installed discovery, activated runtime, arbitrary-repository
behavior, owner acceptance, matched superiority, or longitudinal reliability.
The older public forward receipt continues to support only the two public
synthetic shapes and boundaries it names.

## V0.2.0 publication and forward evidence (2026-09-17/18)

Observed 2026-09-18 from the subject's public repository and release record.
This section is imported public evidence. It was not produced by a Field Lab
attempt, and it does not rewrite the 2026-08-30 history above.

## Immutable source identity

| Field | Recorded value |
| --- | --- |
| Public release | Repo Truth Audit `v0.2.0`, published 2026-09-17 |
| Forward-receipt source candidate | `0.2.0`, copied from the unreleased worktree based on Git HEAD `d2aebdfd82200d48dff7df4c1a8a0a9e72e1b85b` |
| Payload-reconciliation base | public `main` at `f84b22c97e49ff5eb0e777f28fb3c7cb11f0ce4b` |
| Subject-declared clean payload | eight declared files, `80863c9796a2364d99f43cd81d6f53c8d6059f0c303061d18362ba683411a29f` |
| Subject-declared runtime `SKILL.md` | `810b8756aa53174a3c11420f50871017aac0884b5eba9884b7d66f35448b5916` |
| Historical copied-tree digest | `8dc185ad608e1a94af3c37206f92c540b8be519cbd88c7238b9622dabc8b210b` (accurate for the evaluated directory, not a clean distributable payload) |

## Imported v0.2.0 forward evidence

The subject's public `docs/forward-0.2.0-receipt.md` records, dated 2026-09-17:

- a focused read-only routing regression across four independent requests;
- a fresh read-only `source-artifact-split` Audit regression in which only
  `AUDIT.md` changed;
- a same-session two-increment Operate run on a synthetic refactor, checked
  through behavior, structure, delivery, and usefulness;
- a payload-identity reconciliation that retained the historical directory
  digest while defining one clean eight-file payload; and
- a clean-payload follow-up with one actual Plan turn and one single-request
  whole-goal Operate turn.

The subject's v0.2.0 release notes additionally record a maintainer-side
source-owner gate: a transactional daily-copy upgrade with backup, then fresh
Audit, Plan, and Operate tasks in which a single complete Operate request
carried its finite goal through retirement and an externally checked
acceptance without a second prompt.

## Field Lab-side interpretation

The subject's declared payload is a subject-owned declaration about its own
distributable files. Field Lab subject identity in v0.2 remains the exact raw
tree digest of the mounted `local-path`, `local-git-ref`, or `snapshot` source.
Field Lab does not narrow that tree to a declared payload list, hard-code this
subject's files, silently ignore undeclared entries, or expose a Field Lab
payload-identity field. Any future payload identity would need one declaration
governing validation, digest, materialization, and receipt provenance; none
exists in v0.2.

### Ceilings

This section is imported, observed public evidence. It is not a Field Lab
rerun, not a Field Lab synthetic receipt, not a raw event trace, and not proof
of installed bytes, next-turn controller discovery, fresh-host behavior, or
owner acceptance. The v0.2.0 publication itself is asserted by the subject's
own release record; Field Lab did not independently verify the published
assets. No Field Lab target model was invoked for this update, and no subject
repository was written.

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

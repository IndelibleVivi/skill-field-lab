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

It must therefore not be relabelled as a Field Lab v2 synthetic receipt,
deterministic trace verification, matched comparison, or provider-proven model
identity. A screened v2 observed receipt may bind its digest to a narrow claim,
while preserving those fields as unknown. Until that screened record is
created and validated, the v0.2 real-receipt release gate remains open.

## Evidence ceiling

A fresh disposable integration on 2026-08-30 migrated and validated the dated
source pack, self-tested all six discovered cases, and generated one explicit
`source-artifact-split` canary plan with one target invocation and zero LLM
graders. The plan was not run. Before/after whole-checkout digests were equal;
HEAD stayed at the identity above and Git stayed clean. The local digest value
is not published because it also covered ignored machine-local state.

Disposable migration plus plan validation proves cross-subject operation and
zero subject writes. The published forward receipt supports only the two
public synthetic repository shapes and the boundaries it names. Neither fact
alone proves live Field Lab execution or general Repo Truth Audit behavior.

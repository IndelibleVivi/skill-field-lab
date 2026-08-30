# Softpowers case study

Observed source identity: `73ada46eb9ab03d87c0c196361e028551b377470`
on 2026-08-30. This is dated evidence, not an undated current-state claim.

## Why it matters

Softpowers was the first production dogfood subject for the execution and
evidence kernel. That history justified preserving no-spend planning, exact
input identity, controller/worker separation, explicit model/effort selection,
process-group quiescence, and content-light receipts.

Softpowers does not depend on Field Lab at runtime. It owns its generated Skill
tree, methods, cases, activation seeds, candidate/decision history, build,
installer, and releases. Field Lab owns only generic lab, plan, execution, and
receipt machinery.

## V0.2 integration

At the dated source identity, Softpowers still carries a schema-v1
`fieldlab-pack.json`. Normal v0.2 commands deliberately reject it. Faye can
create a separate v2 lab without touching Softpowers:

```bash
fieldlab migrate-v1 /path/to/softpowers/fieldlab-pack.json \
  --output /path/to/external-softpowers-lab/fieldlab.json

fieldlab validate /path/to/external-softpowers-lab/fieldlab.json
fieldlab selftest /path/to/external-softpowers-lab/fieldlab.json
fieldlab list /path/to/external-softpowers-lab/fieldlab.json
```

Migration snapshots the selected `skills/` overlay and copies/re-writes the
case tree into the external lab. The source pack, Skill source, cases, Git
state, and ignored local run state remain unchanged.

For later source-following work, create a fresh external lab whose subject uses
`local-path`, or pin one historical Skill tree through `local-git-ref`. Do not
copy the Field Lab runtime or a second Softpowers Skill tree into this repo.

## Retired projection

V0.1 carried a top-level `softpowers-companion/` functional copy. V0.2 removes
that visual and ownership ambiguity. Tag `v0.1.0` preserves its exact bytes;
current source keeps only this case study, migration provenance, and any
future screened receipts that have an explicit claim ceiling.

## Evidence ceiling

A fresh disposable integration on 2026-08-30 migrated and validated the dated
source pack, self-tested all nine discovered cases, and generated one explicit
`tiny-copy` canary plan with one target invocation and zero LLM graders. The
plan was not run. Before/after whole-checkout digests were equal; HEAD stayed at
the identity above and Git stayed clean. The local digest value is not
published because it also covered ignored machine-local state.

A successful migration and no-spend plan prove that Field Lab can read,
materialize, self-test, and pin Softpowers-owned evidence without subject
writes. They do not prove current Softpowers behavior, installed discovery,
live model performance, release readiness, or owner acceptance.

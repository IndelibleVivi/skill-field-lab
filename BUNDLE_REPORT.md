# Skill Field Lab 0.2.1 candidate bundle report

Date: 2026-09-20. Source version: 0.2.1; schema v2 remains active.
Status: unreleased source candidate. No candidate installation, tag, Release,
controller activation, or live target-model acceptance is claimed.

## Candidate changes and evidence ceiling

Every attempt checks the exact materialized subject mount against its plan and
records `subject_delivery` in metadata, verification, and receipt. Git subjects
use the planned commit. Drift/materialization failures stop before invocation
and stop the remaining matrix, with no process/worker-final claim. Trace
references mean command-path mentions only, and selftest discloses its limited
deterministic surfaces. Current adapter host selection remains unknown; semantic
application requires review. Historical receipt bytes are unchanged.

Validation: `scripts/check_bundle.py` passed on Python 3.12.13: 83 tests,
package compilation, and validation/selftest of both bundled examples. Both
controller Skills passed `skill-validate`; Git whitespace checks passed. The
bundle manifest now covers all 121 public files, including four source/test
files omitted by the previous manifest and the new delivery regression file.
See [TEST_REPORT.txt](TEST_REPORT.txt) for local Python 3.13 startup anomalies
and unchanged isolated reruns. Target-model invocations for this candidate: 0. LLM-grader invocations: 0. Fake executable runs are deterministic
regressions, not live target acceptance. Existing Unreleased sealing, bounded
review material, explain, and requirement-outcome improvements are included.

## Historical v0.2.0 bundle and acceptance (2026-08-30)

The preserved report below describes v0.2.0 only. Its installed/live evidence
must not be attributed to the 0.2.1 candidate. For current semantics use the
product, workspace, evidence, and adapter documents.

# Historical Skill Field Lab v0.2 bundle report

Date: 2026-08-30

Source version: 0.2.0

Status: v0.2.0 implementation and release acceptance complete; installed for
the owner. Git tag, GitHub Release, later-task controller discovery, and owner
acceptance remain separate read-backs.

## Product decision

Skill Field Lab is one local field-lab installation for studying any number of
local reusable-agent subjects without taking ownership of their source. V0.2
has one active runtime and one active workspace contract: schema-v2
`fieldlab.json`.

Schema v1 is not a compatibility runtime. `migrate-v1` is an explicit,
one-shot, offline conversion route for Faye's existing v0.1 material. Tag
`v0.1.0` remains the historical recovery point.

The governing execution rule remains:

> Activation grants analysis, not spend. Live execution requires an explicit
> saved plan, `--live`, and an exact invocation cap.

## Included surfaces

- one dependency-free `fieldlab` CLI with `init`, `validate`, `list`,
  `selftest`, `observe`, `review`, `plan`, `run`, `promote`, `snapshot-git`,
  `migrate-v1`, and `doctor`;
- a standalone v2 lab workspace supporting `local-path`, `local-git-ref`,
  lab-owned `snapshot`, and `control` subjects;
- candidate, claim, optional case/plan/attempt/receipt, separate review, and
  decision records with one final-disposition owner;
- final-response, workspace, command, and trace assertions;
- canary and matched plans with explicit target invocations;
- the protected POSIX execution/evidence kernel and one `codex-exec` adapter;
- the implicit `pattern-intake` controller and explicit `skill-eval` controller
  displayed as **Field Trial**;
- one transactional installer for the app, launcher, controllers, and install
  receipt, with recognized replacement, recoverable backup, `--replace`, and
  `--cli-only`;
- schema-v1 historical contracts under `schemas/v1/`, active contracts under
  `schemas/v2/`, bilingual README files, operating documentation, and two
  reference-only case studies.

The former top-level `softpowers-companion/` functional copy and all normal v1
runtime aliases are retired. Field Lab stores no functional copy of either
real subject.

## Deterministic verification

`python3 scripts/check_bundle.py` passed after the final implementation changes.
It compiled the package, validated and self-tested both bundled examples, and
ran **46 tests**. Coverage includes:

- active-v2 validation and explicit rejection of v1 manifests;
- nullable local problem, claim arrays, decision authority, and bundled record
  templates;
- claim-only observed evidence and immutable receipt-bound human review;
- output-only legal research with a deterministic final-response result and no
  workspace change;
- local-path, local Git ref, snapshot, and isolated-control materialization;
- matched control/Skill plans, explicit model and effort, immutable plan
  identity, and post-plan source/case/executable drift rejection;
- no-spend plan and mandatory live/cap boundaries;
- clean exit, timeout, interrupt, orphan descendant, and verifier-child
  process-group cleanup;
- transactional first install, recognized replacement with backup,
  unrecognized collision refusal, CLI-only install, and mid-transaction
  rollback;
- safe v1 migration, promotion boundaries, schema syntax, adapter registry,
  symlink confinement, and raw trace preservation.

All repository test-suite runner exercises used fake adapters.
**Target-agent invocations during deterministic bundle checks: 0.
LLM-grader invocations: 0.** The separately authorized live release acceptance
is reported below and is not hidden inside the test count.

The same 46-test suite also passed under isolated Python 3.10 and 3.12
interpreters. An independent Draft 2020-12 metaschema check validated all nine
active schemas plus the bundled labs/cases/templates, both real migration
receipts and plans, and representative observed, attempt, and review records.

## Installed and cross-subject evidence

The unified installer replaced the recognized owner-only v0.1 installation and
created a recoverable backup. The installed `fieldlab doctor --json` reported
version 0.2.0, a recognized install, matching app and controller source
digests, supported Python/POSIX host, available Git/Codex executables, and zero
target-agent invocations.

One disposable external integration migrated the dated real v1 manifests from
Softpowers and Repository Operational Truth Audit without writing either
subject checkout. The installed launcher then performed:

- Softpowers: v2 validation plus selftest of 9 discovered cases;
- Repository Operational Truth Audit: v2 validation plus selftest of 6
  discovered cases; and
- one explicit, unexecuted canary plan per subject, each declaring one target
  invocation and zero graders.

Before/after checkout digests matched, both subject HEAD identities remained
fixed, and both Git worktrees remained clean. The digests covered ignored local
state and are intentionally not published. See `case-studies/` for the dated
source identities and claim ceilings.

Both installed controller directories passed the Skill Creator validator.
Installed bytes and validation prove installation integrity; automatic
discovery in a later fresh Codex task remains a separate owner-observation
boundary.

## Controlled live release acceptance

On 2026-08-30, the installed launcher migrated a dated Repository Operational
Truth Audit v1 pack into a private external v2 lab, validated it, and self-tested
all six cases without invoking a target. It then saved and fully inspected one
immutable `source-artifact-split` canary plan:

- run ID `rot-ac10-v020`, one workspace-scoped Skill subject, repeat one;
- one target invocation and zero LLM graders;
- requested `gpt-5.6-sol` with `high` reasoning effort, recorded as explicit
  caller selection rather than provider-proven actual identity;
- approval `never`, workspace-write sandbox, network disabled, disposable
  workspace, and no retry or resume authority.

Exactly one target invocation ran. The attempt exited zero in 85.041 seconds,
the process group became quiescent with no orphan descendants, and the
disposable workspace was removed. Deterministic verification passed all
workspace, command, and trace assertions: the source check remained green,
the manifest-selected `dist/cli.py` printed `artifact-v1`, the report named
the `artifact-v1` / `artifact-v2` split and a not-ready handoff decision, only
`AUDIT.md` changed, and the trace contained five command executions, zero plan
updates, and zero subagent events.

The immutable attempt receipt SHA-256 is
`28be5f49de1bcf9de8c49be1fbf9027787c145ed6babf9b28cd2c6cc2a17563e`.
A separate `implementer-run` human review, SHA-256
`8837beaf0a928aa534d259af30ed49536fe6a1f92decc1d2b3f6d11d03301b87`,
judged the narrow pinned synthetic claim supported. Raw trace, stderr,
workspace details, and private paths remain outside Git.

## Acceptance state

- AC-01 through AC-09: verified by the installed cross-subject exercise,
  controller inspection/validation, v2 unit and integration tests, process
  regressions, and the real one-shot Softpowers migration.
- AC-10: **verified** by the one-invocation controlled ROT canary and its
  digest-bound human ceiling review. The older public ROT forward receipt
  remains separate observed evidence and has not been relabelled.

All v0.2 product acceptance rows are closed. Remote tag/release presence is a
publication read-back from the exact release commit, not something inferred
from this source report.

## Deliberate limits

- Codex CLI is the only implemented live adapter.
- POSIX process-group quiescence is not hostile-daemon or cgroup isolation.
- `hermetic` subject scope remains reserved and cannot be claimed.
- There is no remote clone, marketplace resolver, global registry, daemon,
  SQLite database, LLM grader, leaderboard, scheduled run, or automatic
  publication.
- Installation, Git publication, live execution, subject promotion, and owner
  acceptance remain separate gates.
- Functional material is governed by SUL-1.0; documentation and independent
  documentation-like assets are governed by CC BY-NC-SA 4.0. See
  `LICENSING.md` for the path map.

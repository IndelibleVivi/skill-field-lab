# Skill Field Lab v0.2 product specification

Status: accepted implementation authority, 2026-08-30

Amended 2026-09-10: PS-19 now requires exact per-requirement outcomes from
the public review command when a receipt declares human-review requirements.

Amended 2026-09-18: worker-final output is sealed before any verifier command
runs, each command assertion gets a fresh copy of that sealed tree, and
verifier-derived changes are attributed separately (PS-35); a live workspace is
not retained and a case declares bounded `human_review_material` instead
(PS-36); a read-only per-claim explanation command is part of the CLI (PS-37,
PS-34); and requirement-outcome file reading is bounded and fail-closed
(PS-19).

Repository baseline: `23ef2a5` (`v0.1.0`)

Product name: **Skill Field Lab**

Repository and CLI names: `skill-field-lab`, `fieldlab`

Owner calibration, 2026-08-30: Skill Field Lab v0.1 had no external users.
V0.2 therefore keeps no dual runtime or command-alias compatibility surface.
The sole legacy boundary is an explicit, offline, one-shot migration command
for Faye's own v1 packs and safe recognition of her existing local install.

## Thesis

> **Study before you install. Test only what matters.**
>
> A local maintainer workbench for learning from external agent skills,
> evolving your own reusable behavior, and producing bounded evidence without
> turning every useful idea into a dependency.

在安装之前研究，在接入之前判断；只为真正悬而未决的本地行为主张付出验证成本。

Skill Field Lab is one user-level installation that can study or exercise any
explicitly selected local subject. A subject remains independently usable and
never acquires Field Lab as a runtime dependency.

## Governing rules

- **PS-01 — External work is evidence and contrast, not authority over the
  local system.** Source inspection can inform a decision but cannot silently
  install, activate, or rewrite anything.
- **PS-02 — Activation grants analysis, not spend.** A target-agent invocation
  still requires a saved immutable plan, `fieldlab run --live`, and an explicit
  invocation cap.
- **PS-03 — A study may succeed with no installation, no live run, and no local
  change.** `REJECT`, `DEFER`, and `ALREADY COVERED` are valid completed study
  outcomes.
- **PS-04 — Evidence is claim-scoped.** Field Lab does not produce global Skill
  scores, rankings, or automatic winners.

## Users and jobs

The primary user maintains reusable agent behavior and needs to decide:

- whether one external mechanism solves a demonstrated local problem;
- what the smallest suitable landing plane is;
- whether ordinary work already supplies sufficient evidence;
- whether a bounded synthetic trial is worth target-agent invocations; and
- what a receipt can and cannot support.

## Three intervention levels

### PS-05 — Level 0: intake only

`$pattern-intake` pins and inspects a source, distils one portable mechanism,
identifies local fit, chooses the lowest landing plane, and closes with one of:

```text
ADOPT | ADAPT | REJECT | DEFER | ALREADY COVERED
```

Level 0 requires no lab manifest, case, fixture, subject write, installation,
or target-agent invocation.

### PS-06 — Level 1: external local lab

`fieldlab init <directory>` creates an explicit local lab workspace. The lab
may live anywhere the maintainer chooses and may read or materialize independent
subjects by pinned local source. The default Level 1 posture leaves every
subject repository byte-for-byte unchanged.

### PS-07 — Level 2: subject-owned evidence

`fieldlab promote --from <lab> --to <subject-evidence-directory>` is the only
Field Lab operation that intentionally writes selected lab-owned records into
a subject repository. Promotion copies selected candidates, claims, cases,
receipts, reviews, and decisions; it never copies the Field Lab runtime.

## Workspace and manifest model

- **PS-08 — `fieldlab.json` is the v2 lab manifest.** It describes a lab
  workspace, not an installed subject pack.
- **PS-09 — `fieldlab-pack.json` is migration input only.** Normal `validate`,
  `list`, `selftest`, `plan`, `run`, and `observe` paths accept schema v2 only.
  `migrate-v1` may read a legacy pack once, writes a separate v2 lab and
  receipt, and never modifies the source pack.
- **PS-10 — Subjects are explicit local sources.** V0.2 supports
  `local-path`, `local-git-ref`, `snapshot`, and `control`. It does not
  auto-clone remote URLs, resolve marketplaces, or guess installed Skills.
- **PS-11 — No hidden registry.** Lab state is inspectable files. V0.2 adds no
  SQLite registry, daemon, background monitor, or implicit global project list.

The normative source and drift rules are in
[WORKSPACE_MODEL_V0.2.md](WORKSPACE_MODEL_V0.2.md).

## Record authority

- **PS-12 — The authority chain is**
  `source -> candidate -> claim -> [case -> plan -> attempt -> receipt] -> decision`.
  The bracketed execution chain is optional.
- **PS-13 — Candidate records describe the mechanism, not the final
  disposition.** `local_problem` may be `null`; candidates do not own a final
  decision.
- **PS-14 — Decision is the sole final disposition owner.** It records the
  rationale, accepted kernel, excluded machinery, evidence references, landing
  plane, local delta, and reopen condition.
- **PS-15 — Observed evidence may bind directly to a claim.** A case is
  optional for evidence arising from ordinary work.

The normative record delta is in
[SCHEMA_DELTA_V1_TO_V2.md](SCHEMA_DELTA_V1_TO_V2.md).

## Case and evidence model

- **PS-16 — A case is an optional synthetic probe.** It records activation as
  `implicit`, `explicit`, or `direct` and may verify the final agent response,
  workspace, bounded commands, raw trace, and declared human-review needs.
- **PS-17 — Final agent response is a first-class artifact.** Deterministic
  checks support text inclusion, exclusion, regular expressions, and a bounded
  JSON Schema subset.
- **PS-18 — `fixture/` and `expected/` are optional.** Self-test runs the
  known-fail/known-pass oracle only when a deterministic expected overlay is
  present; output-only or human-review cases are valid without one.
- **PS-19 — Execution receipts are immutable.** Later human review is a
  separate record bound to the receipt digest. A review can add a verification
  method without rewriting the sealed execution receipt. When a receipt declares
  human-review requirements, the public review command records exactly one
  `supported`, `not-supported`, or `inconclusive` outcome for each requirement;
  missing or extra outcomes fail closed.
- **PS-20 — Evidence dimensions remain orthogonal.** V0.2 uses `subject_scope`
  (`isolated-control`, `workspace-scoped`, `hermetic`) and
  `verification_methods[]`. `hermetic` remains reserved.
- **PS-21 — Attempt outcomes are bounded.** Sealed attempts use `pass`, `fail`,
  `error`, `timeout`, `termination-failure`, or `inconclusive`. Claim-facing
  observed assessments such as `supported` are recorded separately and map to
  an execution-neutral receipt outcome.

## Protected execution kernel

The following v0.1 behavior is protected and must remain regression-covered:

- **PS-22** — Controller instructions, hidden assertions, expected outputs,
  candidate rationale, and evaluator advice never enter target-worker context.
- **PS-23** — Planning starts no target model and pins manifest, prompt, case,
  fixture, subject source, Field Lab source, and available adapter executable
  identity. Drift before live execution fails closed.
- **PS-24** — Live execution requires a saved plan, `--live`, and
  `--max-invocations N`; no retry, baseline, repeat, case, or full suite is
  implicit.
- **PS-25** — Target and verifier commands use dedicated POSIX process groups.
  Evidence is sealed only after group quiescence; surviving descendants are
  terminated and cannot produce a normal success receipt.
- **PS-26** — Absolute or tree-escaping fixture/source symlinks are rejected.
- **PS-27** — Requested model and effort remain caller-selection evidence, not
  provider-proven actual identity.
- **PS-28** — Windows live execution and `danger-full-access` continue to fail
  closed until an equivalent containment contract exists.

## Controller and adapter boundary

- **PS-29** — `pattern-intake` keeps its name, slug, display identity, and
  implicit invocation.
- **PS-30** — `skill-eval` keeps its slug and explicit-only policy; its display
  name becomes **Field Trial** and it designs the weakest sufficient evidence
  path for one unresolved claim.
- **PS-31** — The adapter surface has a registry seam. V0.2 implements only
  `codex-exec`; data may be host-aware without pretending the runtime is
  provider-agnostic.

## Installation and operations

- **PS-32** — `python scripts/install.py` transactionally installs the app,
  launcher, both controller Skills, and a provenance receipt. It recognises its
  own installs, supports `--replace` and `--cli-only`, preserves a recoverable
  backup until success, and documents clean uninstall.
- **PS-33** — `fieldlab doctor` performs read-only checks of Field Lab source
  identity/version, controller digests, Python, Git, Codex, supported host, and
  Skill discovery path. It starts no target agent.
- **PS-34** — V0.2 CLI includes `doctor`, `init`, `validate`, `list`, `selftest`,
  `snapshot-git`, `observe`, `review`, `explain`, `plan`, `run`, `promote`, and
  `migrate-v1`. Superseded v1 command aliases are removed.
- **PS-35** — The worker-final changed-file set, diff, and tree digest are sealed
  before any verifier command runs. Workspace assertions read the sealed worker
  tree. Each command assertion runs against its own disposable byte copy of that
  same sealed tree; changes made there are attributed as verifier-derived and
  cannot by themselves produce a `pass`. Sealing a diff uses a disposable Git
  index and never mutates the workspace index or cached diff. This is a
  worker-source/derived-output contract, not OS-level containment.
- **PS-36** — A live worker workspace is not retained; `keep_workspace` remains
  the only whole-workspace switch. A case that declares human-review
  requirements may declare bounded `human_review_material` exact
  workspace-relative files; they are copied atomically into attempt-owned
  `review-material/` with a manifest whose path, digest, and status are bound
  into `verification.json` and the immutable receipt. Missing, non-regular,
  symlinked, escaping, unreadable, or over-limit material is an evidence-sealing
  error that leaves no partial set and cannot yield `pass`. Cases without
  declared material rely on the standard attempt artifacts. Since the worker
  process is already quiescent, that failure is recorded as a distinct
  `evidence-failed` attempt/run state, not `termination-failed`; process
  termination and cleanup failures keep the `termination-failed` path.
- **PS-37** — `fieldlab explain` is read-only. It recomputes one claim's
  `supported`, `not-supported`, `inconclusive`, and `mixed` evidence from claims,
  immutable receipts, and separate reviews; it does not read `claim.status` as
  evidence or count a `PASS` as a conclusion, deduplicates the same receipt
  across canonical locations by raw digest, treats disagreeing bound reviews as
  conflicting rather than latest-wins, labels receipts without the worker-final
  boundary marker `legacy-ambiguous`, and starts no target model.

## Non-goals

- remote auto-clone, marketplace resolution, or guessed installed subjects;
- cloud dashboard, daemon, background or scheduled runs;
- global Skill scoring, leaderboard, or automatic winner selection;
- automatic LLM judging or broad provider support;
- automatic commit, push, publication, installation into subjects, or release;
- a dual v1/v2 runtime, ambient environment-smoke mode, or legacy command aliases;
- a licensing change inside the v0.2 schema/runtime tranche.

## Acceptance contract

- **AC-01** — One installed Field Lab can validate/plan against Softpowers and
  Repository Operational Truth Audit manifests without installing either
  subject into Field Lab.
- **AC-02** — A Level 1 plan/materialization leaves both subject repositories
  byte-for-byte unchanged.
- **AC-03** — Pattern Intake can close a source study without a manifest, case,
  or live run.
- **AC-04** — `observe` creates claim-bound evidence with no case.
- **AC-05** — A legal-research case that changes no workspace file can pass by
  deterministic final-response assertions.
- **AC-06** — `isolated-control` and one Skill subject produce a genuinely
  matched plan with identical non-subject execution inputs.
- **AC-07** — The plan enumerates every invocation and live execution rejects
  any pinned input drift.
- **AC-08** — Timeout, interrupt, orphan-descendant, verifier-child, and
  termination-failure regressions remain green.
- **AC-09** — The migration-only parser can convert a v1 Softpowers pack without
  overwriting the source manifest; cases become schema v2 and migration writes
  a receipt. The original pack is not accepted by normal runtime commands.
- **AC-10** — Repository Operational Truth Audit has at least one real
  controlled receipt whose claim ceiling is explicit before a v0.2 release.
  Creating a new live receipt still requires its own saved plan and invocation
  cap; source completion alone does not satisfy this gate.
- **AC-11** — A regression in which a verifier repairs a protected file in its
  own copy and exits zero stays non-passing: the sealed worker-final diff and
  changed-file set still describe the worker bytes, the verifier change is
  attributed, and a workspace assertion reads the sealed tree. A second
  command assertion receives a fresh copy and still observes the worker bytes.
- **AC-12** — A case with declared `human_review_material` seals exactly those
  files into attempt-owned `review-material/` before verification, binds the
  manifest digest into the receipt, and does not retain the whole workspace;
  invalid declared material fails closed with no partial set. A case with review
  requirements but no declared material keeps only the standard attempt
  artifacts.
- **AC-13** — `fieldlab explain` reports a claim's derivable evidence,
  dimensions, subject identity, pending, failed, or conflicting review
  requirements, duplicate receipt locations, legacy-ambiguous boundaries,
  missing or digest-drifted artifacts, and next evidence gap without modifying
  the lab.

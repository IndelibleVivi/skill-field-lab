# Skill Field Lab bundle report

Date: 2026-08-17
Working version: 0.1.0
Status: runnable standalone draft; not yet published or integrated into the live Softpowers repository.

## Product decision

The generic executable evaluator has been removed from Softpowers' conceptual runtime boundary. This bundle treats Softpowers as the first subject pack and keeps reusable evaluation machinery in a standalone maintainer companion.

The governing rule is:

> Activation grants analysis, not spend. Live execution requires an explicit run boundary.

## Included surfaces

- `pattern-intake` controller skill for pinned external-repository learning and `ADOPT / ADAPT / REJECT / DEFER / ALREADY COVERED` decisions.
- `skill-eval` controller skill for one falsifiable behavior claim and the weakest sufficient evidence lane.
- Dependency-free `fieldlab` CLI and runner.
- `codex-exec` adapter with explicit model/effort selection for comparison-capable runs.
- Pack, case, plan, receipt, candidate, claim, and decision schemas.
- No-spend observed-dogfood import.
- No-spend Git-ref subject snapshots for baseline/candidate comparison.
- Exact Softpowers companion copies of `tiny-copy`, `stale-cursor`, and `spec-chain`.
- A legal-research example to prove the core is not DevOps-only.

## Spend boundary

`validate`, `selftest-pack`, `list`, `plan`, `snapshot-git`, installation, and `import-observed` never start a target model. A target run requires all of:

1. a saved plan;
2. `fieldlab run`;
3. `--live`;
4. `--max-invocations N` at or above the saved matrix count.

The plan records zero LLM-grader invocations in v0.1. No retry, expanded case matrix, baseline, or full suite is implicit.

## Evidence correctness implemented

- Saved plans pin pack, case contract, prompt, fixture, subject-overlay, Field Lab Python source, and available Codex executable digests.
- Live execution fails closed when any pinned input drifts after planning.
- Canary and matched modes require explicit requested model and reasoning effort.
- Ambient defaults are restricted to one-shot, non-comparison `environment-smoke` runs and cannot resume.
- Receipts distinguish requested model/effort from provider-proven actual identity.
- Resume identity includes plan, inputs, adapter executable/version, Python/platform, permissions, timeout, and workspace-retention settings.
- Repo-scoped workers use an isolated `HOME`, preserve `CODEX_HOME` for authentication, and pass `--ignore-user-config`.
- Repo-scoped evidence never claims hermetic or exclusive subject attribution.
- Target workers and command assertions run in dedicated POSIX process groups.
- Timeout, KeyboardInterrupt, clean-parent-with-live-descendant, and assertion-timeout paths must reach group quiescence before evidence is sealed.
- Windows live execution fails closed until a Job Object adapter exists.
- Fixture and subject-overlay trees reject absolute or escaping symlinks.

## Deterministic verification

`python scripts/check_bundle.py` passed with no real target-model invocation.

Coverage includes:

- controller/adapter flags and worker-home isolation;
- model/effort and environment-smoke contracts;
- immutable plan hash and post-plan input/executable drift;
- local dependency-free CLI installation;
- known-fail fixture / known-pass expected-overlay credibility;
- clean exit, timeout, orphan descendant, and KeyboardInterrupt process cleanup;
- fake-Codex pass, live cap, resume, model drift, and effort drift;
- Git baseline snapshot materialization;
- Softpowers copy-into-root single and matched manifests;
- malformed/unknown trace preservation;
- command-assertion descendant cleanup;
- fixture symlink escape rejection.

Final deterministic suite at handoff: **25 tests passed**.

## Softpowers migration boundary

The bundle does not modify the connected Softpowers repository. `softpowers-companion/` contains the files and instructions for a later forward-only migration:

1. copy the manifest to the Softpowers root;
2. validate and selftest without quota;
3. run the fake-adapter suite;
4. optionally run one explicitly approved real canary;
5. retire the embedded `soft-eval` runner and projection only after migration evidence passes.

Historical Softpowers revisions remain untouched.

## Deliberate limits

- Working name remains `skill-field-lab`; it is rename-ready.
- Local Codex CLI is the only live adapter.
- Live process containment is POSIX process-group containment, not hostile daemon/cgroup containment.
- V0.1 supports `read-only` and `workspace-write`; `danger-full-access` is rejected.
- No LLM grader, cloud dashboard, monitoring, leaderboard, scheduled runs, or automatic publishing.
- A public license boundary has not been selected. Do not publish the bundle as a licensed release until `LICENSE-TODO.md` is resolved.

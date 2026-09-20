# Skill Field Lab repository contract

## Product and ownership

This repository owns the standalone Skill Field Lab app, CLI, controller
Skills, active schemas/templates, execution/evidence kernel, generic examples,
installation, and project documentation.

Subject repositories remain authoritative for their own Skills, cases,
decisions, installation, and release state. Softpowers and Repository
Operational Truth Audit are independent subjects. Do not copy, generate,
install, replace, or version their canonical source here. Case studies and
screened receipts are evidence, not subject source.

`fieldlab/` is the only runtime source. Installed app/controller directories
are derived deployment state and must never be hot-edited as source.

## Runtime contract

- Version 0.2 requires Python 3.10+ and uses only the standard library.
- Normal commands accept schema-v2 `fieldlab.json` and schema-v2 cases only.
- V1 is read only inside the explicit offline `migrate-v1` command. Do not add
  a compatibility loader, alternate runner, ambient smoke mode, or old command
  alias.
- Active schemas live in `schemas/v2/`; `schemas/v1/` is historical migration
  documentation.
- Supported subject sources are `local-path`, `local-git-ref`, lab-owned
  `snapshot`, and `control`. Remote auto-clone and marketplace resolution are
  out of scope.
- `codex-exec` is the only implemented adapter. The registry seam does not
  authorize weaker provider-specific boundaries.
- Live execution is POSIX-only until an equivalent Windows Job Object adapter
  exists. Cases may request only `read-only` or `workspace-write`; reject
  `danger-full-access`.

## Protected execution kernel

Do not weaken these contracts:

- controller/evaluator instructions, hidden assertions, expected artifacts,
  candidate rationale, and review rubrics never enter target-worker context;
- `plan` starts no target model, enumerates every invocation, and pins manifest,
  case, prompt, fixture, subject, Field Lab source, and available executable;
- live execution requires a saved plan, `--live`, and
  `--max-invocations N`; no retry, control, repeat, grader, or suite is implicit;
- post-plan drift fails closed; each attempt independently compares the actual
  subject mount with the plan digest, and Git materialization uses the planned
  resolved commit. Delivery mismatch/materialization failure stops the matrix
  before invocation as `input-drift`/`preflight-failed`, never termination failure;
- requested model and effort remain caller-selection evidence;
- target and verifier commands reuse the dedicated POSIX process-group helper;
- a parent exit is insufficient: seal only after group quiescence; and
- timeout, interrupt, surviving descendants, or cleanup failure cannot produce
  a normal success receipt.

Any change to identity, spend, adapter command construction, process cleanup,
receipt sealing, resume, or verification requires a focused deterministic
regression. CI and ordinary tests must use fake executables and zero real target
invocations.

## Workspace and write boundaries

- Level 0 Pattern Intake may finish with no lab or change.
- Level 1 labs read external subjects and write only lab-owned or disposable
  state. Reject absolute or tree-escaping source/fixture symlinks.
- `promote` is the only Field Lab operation that intentionally copies records
  to a chosen subject evidence directory. It never copies runtime, manifest,
  plans, or runs and must refuse collisions.
- Do not modify an independent subject repository during Field Lab integration
  work unless Faye explicitly authorizes that repository write.

## Record and evidence authority

The chain is:

```text
source -> candidate -> claim -> [case -> plan -> attempt -> receipt] -> decision
```

Candidate describes the mechanism and may have `local_problem: null`. Decision
alone owns the final disposition. Existing evidence may bind directly to a
claim. Final response is a first-class assertion surface. Fixture and expected
overlays are optional. Execution receipts are immutable; later human judgment
is a separate review bound to the receipt digest.

`subject_delivery`, actual host selection, and semantic content application are
independent evidence. The current adapter has no structured Skill-selection event:
report unknown, and treat case activation as declared. Trace reference mentions
are command-path evidence only. Keep `reference_reads_include` as a deprecated
schema-v2 alias; do not restore a read claim or add shell/syscall heuristics.
Selftest exercises only workspace/command oracles, with zero target invocations.

Keep origin, subject scope, comparison, verification methods, and independence
separate. `hermetic` is reserved. Never infer exclusive causation from a
workspace-scoped overlay.

## Installation

`scripts/install.py` is the sole installer. It must transactionally install the
app, launcher, both controllers, and receipt; preflight unknown collisions;
recognise the current and known v0.1 owned identities; preserve a recoverable
backup; restore prior targets after mid-commit failure; and support
`--cli-only`. Do not restore independent legacy copy scripts.

`fieldlab doctor` is read-only and starts no target model. Installed bytes,
next-turn controller discovery, live behavior, Git commit/push, and public
release are distinct proof layers.

## Documentation impact

Update:

- `README.md` and `README.zh-CN.md` when user-visible commands, capabilities,
  defaults, support, or boundaries change;
- this file when canonical paths, active compatibility, required verification,
  install, or spend/write authority changes;
- product/workspace/schema docs for accepted contract changes;
- architecture/evidence/adapter docs when their semantics change;
- installation or migration guides when operator behavior changes;
- case studies only from fresh subject evidence, with dated source identity;
  and
- `CHANGELOG.md`, bundle report, test report, and manifest at release-candidate
  closure.

Tracked docs use repo-relative links and public-safe placeholders. Private
continuity, raw traces, local absolute paths, credentials, and private subject
evidence stay outside Git.

## Verification

Use the narrow checks during development, then run before handoff:

```bash
python3 -m unittest discover -s tests -p 'test*.py'
python3 scripts/check_bundle.py
python3 /path/to/skill-creator/scripts/quick_validate.py skills/pattern-intake
python3 /path/to/skill-creator/scripts/quick_validate.py skills/skill-eval
git diff --check
```

The Skill validator may run in an isolated dependency environment when host
Python lacks PyYAML; do not add PyYAML to this stdlib-only project or retain the
environment as repository state.

Before commit/push, inspect `git status --short`, intended diff, and staged
diff; stage explicit public paths only. Tag, release, real target execution,
and subject-repository writes remain separate gates.

# Quota and spend contract

Target-agent invocation is an explicit external side effect.

## No additional target invocation

These actions start no target model:

- loading `pattern-intake` or explicit `skill-eval`;
- `doctor`, `init`, `validate`, `list`, `selftest`, `snapshot-git`, `observe`,
  `review`, `explain`, `plan`, `promote`, and `migrate-v1`;
- installation, upgrade preflight, backup, and doctor checks;
- unit tests and CI; and
- reading plans, receipts, reviews, or decisions.

They may execute deterministic repository-owned commands or run inside an
already active assistant task, so the precise claim is **zero additional
target-agent invocations**, not zero compute of every kind.

## Live gate

Live execution requires all of:

1. one saved immutable schema-v2 plan;
2. an explicit matrix of subjects, cases, and repeats;
3. an explicit requested model and reasoning effort;
4. `fieldlab run <plan>`;
5. `--live`;
6. `--max-invocations N` at least equal to the saved matrix count; and
7. a supported adapter and POSIX host.

The runner re-pins all planned identities immediately before execution. A
changed manifest, case, prompt, fixture, subject source, Field Lab source, or
available executable requires a new plan.

## No hidden spend

- no implicit all-cases mode;
- `repeat=1` unless explicitly increased in the plan;
- no automatic baseline or control insertion;
- no automatic retry;
- no LLM grader in v0.2;
- no background or scheduled run; and
- no mutable ambient smoke path.

## Existing evidence first

Before planning a synthetic case, inspect ordinary traces, diffs, tests, or
reviews. `observe` records them as observed evidence bound to a claim. Do not
relabel imported evidence as a Field Lab execution or matched comparison.

# Source carryover from Softpowers

The standalone bundle is a structural rewrite, with deliberate reuse of proven subject-level material.

## Retained as Softpowers-owned material

- `tiny-copy`, `stale-cursor`, and `spec-chain` prompts, fixtures, assertions, and expected overlays;
- the decision vocabulary `ADOPT`, `ADAPT`, `REJECT`, `DEFER`, and `ALREADY COVERED`;
- the principle that raw JSONL is authority and derived telemetry is limited;
- input, runner, executable, timeout, workspace, and resume identity as evidence concerns;
- known-fail / known-pass deterministic fixture testing.

## Rewritten into the standalone core

- pack and subject abstraction;
- controller–worker separation;
- candidate -> claim -> case -> plan -> attempt -> receipt -> decision records;
- no-spend planning and observed-dogfood import;
- explicit `--live` plus invocation cap;
- requested model and reasoning-effort identity;
- POSIX process-group quiescence for target and verifier commands;
- content-light receipt export;
- ambient versus repo-scoped attribution.

## Intentionally not carried forward

- a generated `soft-eval` skill containing the generic runner;
- `model=None` as ordinary comparison evidence;
- parent-only timeout cleanup;
- automatic full-suite or baseline behavior;
- an LLM grader;
- claims that repository overlay is hermetic isolation.

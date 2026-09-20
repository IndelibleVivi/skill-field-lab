# Source carryover from Softpowers

> Historical record — retained and retired mechanisms at the v0.2 rewrite.
> For current behavior, read the [Product spec](../PRODUCT_SPEC_V0.2.md);
> for current evidence and release status, read [Current state](../CURRENT_STATE.md).

Skill Field Lab is a standalone structural rewrite that retained proven
mechanisms while retiring the functional subject copy from current source.

## Retained mechanisms

- `ADOPT`, `ADAPT`, `REJECT`, `DEFER`, and `ALREADY COVERED`;
- raw JSONL as execution authority and derived summaries as bounded evidence;
- explicit input, executable, timeout, workspace, and resume identity;
- known-fail/known-pass deterministic fixture testing;
- controller/worker separation;
- no-spend plans and explicit capped live execution; and
- POSIX process-group quiescence for target and verifier processes.

## Rewritten for v0.2

- pack-first runtime became an external local lab workspace;
- v1 overlay subjects became explicit local-path, local-Git-ref, snapshot, or
  isolated-control subjects;
- candidate no longer owns a provisional final decision;
- observed evidence may bind directly to a claim;
- final agent response is a first-class assertion surface;
- verification methods are an array independent from subject scope;
- human review is separate from immutable execution receipts; and
- one transactional installer replaced independent CLI/Skill copy scripts.

## Retired from current source

- `softpowers-companion/` and its copied functional cases;
- `fieldlab-pack.json` as a normal runtime entrypoint;
- `selftest-pack`, `import-observed`, and environment-smoke aliases;
- ambient execution identity;
- generated or embedded `soft-eval` machinery; and
- claims that a workspace overlay proves hermetic or exclusive causation.

Tag `v0.1.0` preserves the exact retired projection and provenance. Softpowers
continues to own its current Skill source, cases, decisions, and release state.

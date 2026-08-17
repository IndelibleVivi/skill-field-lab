# Migration from Soft Eval

Status: completed in Softpowers commit `4180b49`. Phases 1–3 and 5 passed
without a real target-model invocation; the optional live canary in phase 4
was intentionally not required. The procedure below is retained as the
forward-only migration and recovery reference.

The migration must be staged. Do not delete an embedded runner before the
standalone fake-adapter regression passes.

## Phase 1 — Add the companion manifest

Copy into Softpowers:

- `softpowers-companion/fieldlab-pack.copy-into-softpowers-root.json` -> `fieldlab-pack.json` at the Softpowers repository root;
- any case files that differ from the current `evals/cases/` tree;
- empty `evals/claims/`, `evals/receipts/`, and `evals/decisions/` directories as needed.

Keep current cases and candidate records in place.

## Phase 2 — Validate without quota

From the Softpowers root, with Field Lab installed:

```bash
fieldlab validate fieldlab-pack.json
fieldlab selftest-pack fieldlab-pack.json
fieldlab list fieldlab-pack.json
python -m unittest discover -s /path/to/skill-field-lab/tests -v
```

## Phase 3 — Fake adapter migration check

Run Field Lab's bundled unit suite. It uses fake Codex executables and consumes no model quota. Confirm:

- model and effort drift fail resume identity;
- a timeout kills a real descendant process;
- no late sentinel or late trace append occurs;
- successful fake behavior remains stable.

## Phase 4 — Optional one-case real canary

Only when Faye chooses to spend quota, plan one `tiny-copy` run with an exact model and effort. Do not run all cases merely to prove the migration exists.

## Phase 5 — Remove the embedded machinery

After the migration check:

- remove `evals/run_behavior_evals.py`;
- stop projecting it into generated skills;
- retire `skills/soft-eval/` as a bundled executable skill;
- remove `methods/eval.md` from Softpowers routing or replace it with a short pointer to the optional companion;
- update build, manifest, validation, README, changelog, licensing map, and generated-tree checks together.

Preserve historical revisions. No history rewrite is required.

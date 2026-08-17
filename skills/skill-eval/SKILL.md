---
name: skill-eval
description: "Design or run a minimal evidence plan for one concrete reusable-agent behavior claim. Use explicitly for skill canaries, matched comparisons, release evidence, routing investigations, or importing real dogfood. Keep evaluator instructions outside the target worker context. Loading this skill grants analysis only; live target-agent execution requires an explicit saved plan, --live, and an invocation cap."
---

# Skill Eval

Evaluate one falsifiable behavior claim. Do not assign a general score to a skill or turn ordinary repository work into a mandatory benchmark.

## Keep controller and worker separate

The controller may inspect candidates, claims, assertions, and expected outcomes. The target worker receives only the ordinary prompt, disposable fixture, selected subject overlay, and allowed tools. Never leak hidden assertions or evaluator advice into the worker prompt.

## Select the weakest sufficient lane

1. **Inspect** — reason from source and deterministic state; no additional target invocation.
2. **Import dogfood** — hash existing trace, diff, tests, or review as observed unmatched evidence.
3. **Canary** — one subject and the smallest synthetic case.
4. **Matched** — multiple subjects with the same prompt, fixture, model, effort, permissions, and repeats.

Use the evidence vocabulary in `references/evidence-model.md`.

## Validate the case before spending

Use `fieldlab validate` for contracts and `fieldlab selftest-pack` when the case carries an `expected/` deterministic oracle. The unresolved fixture must fail and the expected overlay must pass. These checks may run repository-owned command assertions but start no target model.

## Plan before running

Use `fieldlab plan` and report:

- subjects;
- cases;
- repeats;
- target-agent invocations;
- LLM-grader invocations;
- model and effort selection;
- attribution level;
- sandbox, approval, and network boundary.

Planning does not authorize execution.

## Cross the live boundary only explicitly

A live run requires:

```bash
fieldlab run <plan.json> --live --max-invocations <N>
```

Do not infer consent from enthusiasm, skill activation, repository context, CI, a request to review a plan, or the existence of unused quota. Never add cases, repeats, graders, or retries beyond the saved matrix without a new plan.

## Interpret narrowly

A passing case supports the behavior and boundaries encoded by that case. A repaired case proves the repair. Broader claims need later comparable evidence. Preserve raw trace as authority and mark human inference as inference.

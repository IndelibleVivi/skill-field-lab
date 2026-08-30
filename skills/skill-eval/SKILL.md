---
name: skill-eval
description: "Design the weakest sufficient evidence path for one unresolved reusable-agent behavior claim. Use explicitly for ordinary-work evidence, bounded canaries, matched controls, release evidence, or routing investigations. Existing work comes first. Live execution requires a saved plan, --live, and an explicit invocation cap."
---

# Field Trial

Evaluate one falsifiable behavior claim. Do not assign a general score to a skill or turn ordinary repository work into a mandatory benchmark.

## Keep controller and worker separate

The controller may inspect candidates, claims, assertions, and expected outcomes. The target worker receives only the ordinary prompt, disposable fixture, selected subject overlay, and allowed tools. Never leak hidden assertions or evaluator advice into the worker prompt.

## Select the weakest sufficient lane

1. **Inspect** — reason from source and deterministic state; no additional target invocation.
2. **Observe ordinary work** — bind an existing trace, diff, test result, or review directly to the claim; a synthetic case is optional.
3. **Canary** — one subject and the smallest synthetic case.
4. **Matched** — multiple subjects with the same prompt, fixture, model, effort, permissions, and repeats.

Use the evidence vocabulary in `references/evidence-model.md`.

## Validate the case before spending

Use `fieldlab validate` for contracts and `fieldlab selftest` when the case carries an `expected/` deterministic oracle. The unresolved fixture must fail and the expected overlay must pass. Output-only and human-review cases may omit both `fixture/` and `expected/`. These checks may run repository-owned command assertions but start no target model.

## Plan before running

Use `fieldlab plan` and report:

- subjects;
- cases;
- repeats;
- target-agent invocations;
- LLM-grader invocations;
- model and effort selection;
- subject scope and verification methods;
- sandbox, approval, and network boundary.

Planning does not authorize execution.

## Cross the live boundary only explicitly

A live run requires:

```bash
fieldlab run <plan.json> --live --max-invocations <N>
```

Do not infer consent from enthusiasm, skill activation, repository context, CI, a request to review a plan, or the existence of unused quota. Never add cases, repeats, graders, or retries beyond the saved matrix without a new plan.

## Interpret narrowly

A passing case supports the behavior and boundaries encoded by that case. A repaired case proves the repair. Broader claims need later comparable evidence. Preserve raw trace as execution authority; attach later human judgment as a separate review record bound to the sealed receipt digest.

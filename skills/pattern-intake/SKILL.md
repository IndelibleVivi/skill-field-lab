---
name: pattern-intake
description: "Inspect a relevant external repository or framework, distill one reusable mechanism, compare it with a local skill or method, and record ADOPT, ADAPT, REJECT, DEFER, or ALREADY COVERED. Use when learning from adjacent agent, skill, workflow, harness, or engineering repositories. Analysis alone never authorizes a live behavior run, repository write, publication, or other external action."
---

# Pattern Intake

Use external work as evidence and contrast, not as automatic authority over the local system.

## Pin before judging

Record the repository, exact commit or release, applicable license, files actually reviewed, review date, and one narrow mechanism. Separate source facts from your inference.

## Distill the mechanism

Remove product names and marketing language. State the invariant in portable terms. Then name the local problem it may solve: an observed failure, repeated overhead, evidence gap, recovery problem, packaging boundary, or host-contract change.

No local problem means `DEFER`, `ALREADY COVERED`, or `REJECT: no demonstrated need` is legitimate.

## Choose the lowest landing plane

Prefer the lowest plane that can solve the problem:

- runtime method or routing;
- eval / maintainer tooling;
- packaging / distribution;
- documentation / provenance.

A useful harness pattern does not automatically belong in a daily skill runtime.

## Decide

Use one top-level value:

- `ADOPT`
- `ADAPT`
- `REJECT`
- `DEFER`
- `ALREADY COVERED`

Always preserve the accepted kernel and excluded machinery. A rejection is still a learning result.

## Stop before spend

First ask whether existing dogfood, deterministic inspection, or a known pass/fail fixture already answers the question. When an unresolved behavior claim remains, hand it to `$skill-eval` for a no-spend plan.

Do not call `fieldlab run`, start a target model, edit the local project, open a PR, commit, publish, or release unless the user explicitly authorizes that action.

Use the record shape in `references/decision-record.md` when a durable artifact is requested.

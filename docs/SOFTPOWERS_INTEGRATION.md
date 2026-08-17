# Softpowers integration

Softpowers is Field Lab's first deep dogfood subject, not a runtime dependency.

## Ownership split

Field Lab owns:

- pack, plan, attempt, receipt, candidate, claim, and decision contracts;
- bounded process execution;
- Codex adapter identity;
- generic file, command, and trace verifiers;
- explicit quota gates.

Softpowers owns:

- external-pattern intake history;
- its skill and method revisions;
- the `tiny-copy`, `stale-cursor`, and `spec-chain` cases;
- activation prompts;
- local claims and adjacent controls;
- accepted/rejected adaptation decisions;
- sanitized receipts selected for version control.

## Repository shape

```text
softpowers/
├── fieldlab-pack.json
├── skills/
├── methods/
└── evals/
    ├── activation-prompts.csv
    ├── candidates/
    ├── claims/
    ├── cases/
    ├── receipts/
    └── decisions/
```

`fieldlab-pack.json` lives at the repository root and overlays `skills/` into each disposable worker repository's `.agents/skills/`. The generic runner no longer needs to be projected into `skills/soft-eval/`.

## CI

Softpowers CI may run:

```bash
fieldlab validate fieldlab-pack.json
fieldlab selftest-pack fieldlab-pack.json
```

This validates contracts and fixture presence only. CI must not pass `--live` or start a target model.

## Typical intake path

1. Pin and inspect an external repository.
2. Record a candidate and provisional decision.
3. Name the local Softpowers problem.
4. Write one narrow claim.
5. Search existing dogfood.
6. Import observed evidence when sufficient.
7. Design a minimal canary only for a material unresolved claim.
8. Review the plan's invocation count.
9. Run explicitly.
10. Write the final Softpowers decision.

## Matched baseline versus candidate

Copy `softpowers-companion/fieldlab-pack.matched.copy-into-softpowers-root.json` to the Softpowers root as `fieldlab-pack.matched.json`. Keep `.fieldlab-subjects/` local, preferably in `.git/info/exclude`.

```bash
fieldlab snapshot-git \
  --repo . \
  --ref <baseline-commit> \
  --source skills \
  --output .fieldlab-subjects/baseline-skills

fieldlab validate fieldlab-pack.matched.json

fieldlab plan fieldlab-pack.matched.json \
  --subject softpowers-baseline \
  --subject softpowers-candidate \
  --case <smallest-relevant-case> \
  --mode matched \
  --model <exact-model-id> \
  --reasoning-effort <exact-effort> \
  --output /tmp/softpowers-matched-plan.json
```

The current `skills/` tree must be freshly built and synced before planning. Snapshot metadata pins the baseline commit and tree digest; the plan identity binds both overlay trees again at run time.

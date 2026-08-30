# Historical migration from embedded Soft Eval

Status: **completed historical record**. Softpowers commit `4180b49` removed
the embedded generic runner after standalone fake-adapter and process-boundary
verification. Do not execute the old copy/install procedure from v0.1.

Current authority:

- [One-shot v1-to-v2 migration](MIGRATION_V1_TO_V2.md) for an existing legacy
  `fieldlab-pack.json`;
- [Softpowers case study](../case-studies/softpowers.md) for the ownership and
  integration boundary; and
- [Installation](INSTALLATION.md) for the single current app/controller
  installation.

The durable historical decisions remain:

- generic process, quota, and receipt machinery belongs to standalone Skill
  Field Lab, not a generated `soft-eval` Skill;
- Softpowers owns its cases, candidates, claims, decisions, and activation
  materials;
- deterministic and fake-adapter migration checks require no target model;
- optional live evidence always needs a saved plan, `--live`, and an exact cap;
  and
- Git history, rather than an inert duplicate tree, preserves the retired
  implementation.

The former `softpowers-companion/` projection is preserved by tag `v0.1.0` and
removed from current source. No history rewrite occurred.

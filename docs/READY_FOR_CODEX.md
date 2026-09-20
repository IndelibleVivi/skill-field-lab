# Source readiness

Status: v0.2.1 release source verified through the deterministic checks reported
in [BUNDLE_REPORT.md](../BUNDLE_REPORT.md). The acceptance below also retains
dated v0.2.0 installation/live evidence; it is not new v0.2.1 proof.

The v0.2 release line is supported by these source checks and dated acceptance
surfaces:

- schema-v2 normal commands and one-shot v1 migration pass unit coverage;
- final-response, workspace, command, trace, receipt, review, drift, resume,
  and process-quiescence regressions pass;
- controller Skills pass the system Skill validator;
- the unified installer passes first-install, recognized replacement, backup,
  rollback, unknown-collision, `--cli-only`, and installed-doctor checks;
- bundled v2 examples validate and self-test with zero target invocations;
- real Softpowers and Repository Operational Truth Audit integrations are
  exercised in disposable external labs without changing either subject repo;
- one owner-authorized ROT `source-artifact-split` canary runs from a saved,
  one-invocation plan and closes its pinned claim with an immutable receipt plus
  a separate digest-bound human review;
- documentation and manifests describe only current commands and boundaries;
- the source diff passes `git diff --check`; and
- a transactional user install reports matching source/controller identities.

This file records source and historical release-acceptance readiness. It does
not infer remote tag/asset presence, installation in every environment,
automatic controller discovery in a new Codex task, or owner acceptance; those
states are read back and reported separately.

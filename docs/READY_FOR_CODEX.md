# Source readiness

Status: v0.2 implementation closure surface; revise with final verification.

The current source is intended to be ready when all of these are freshly true:

- schema-v2 normal commands and one-shot v1 migration pass unit coverage;
- final-response, workspace, command, trace, receipt, review, drift, resume,
  and process-quiescence regressions pass;
- controller Skills pass the system Skill validator;
- the unified installer passes first-install, recognized replacement, backup,
  rollback, unknown-collision, `--cli-only`, and installed-doctor checks;
- bundled v2 examples validate and self-test with zero target invocations;
- real Softpowers and Repository Operational Truth Audit integrations are
  exercised in disposable external labs without changing either subject repo;
- documentation and manifests describe only current commands and boundaries;
- the source diff passes `git diff --check`; and
- a transactional user install reports matching source/controller identities.

Source-ready does not mean tagged, released, installed in every environment,
discovered by a new Codex turn, or accepted through a real owner-controlled
live trial. Those states are reported separately.

# Skill Field Lab v0.2 implementation plan

Status: implementation verified; external release gate open

Spec authority: [PRODUCT_SPEC_V0.2.md](PRODUCT_SPEC_V0.2.md), accepted
2026-08-30

Normative companions:
[WORKSPACE_MODEL_V0.2.md](WORKSPACE_MODEL_V0.2.md) and
[SCHEMA_DELTA_V1_TO_V2.md](SCHEMA_DELTA_V1_TO_V2.md)

Repository baseline: `23ef2a5` (`v0.1.0`); source was clean and synchronized
with `origin/main` at implementation entry.

## Dependency order

```text
contract freeze
  -> v2 records + migration-only legacy reader
  -> source identity + materialization
  -> result verification + receipt/review
  -> runner integration
  -> CLI + installer
  -> examples/integrations/docs
  -> acceptance + install + Git closure
```

## Coverage ledger

| Requirements | Intended outcome | Slice | Verification | Status |
| --- | --- | --- | --- | --- |
| PS-01–PS-04 | product thesis and valid no-change study outcomes | contract/docs/controllers | docs reconciliation and controller validation | verified |
| PS-05–PS-07 | Level 0/1/2 operations with promotion as sole subject-write path | CLI/controllers | init/promote boundary tests | verified |
| PS-08–PS-11 | standalone v2 lab manifest and four local source types | schemas/contracts | contract and source-identity tests | verified |
| PS-12–PS-15 | corrected candidate/claim/decision authority; claim-only observe | record schemas/receipts/CLI | schema and observe tests | verified |
| PS-16–PS-21 | optional case chain, final-output checks, review records, evidence v2 | case verifier/receipts | output-only and review immutability tests | verified |
| PS-22–PS-28 | protected execution/evidence kernel | runner/process/adapter | existing plus v2 drift/process regressions | verified |
| PS-29–PS-31 | controller relationship and adapter registry seam | skills/adapter | Skill validation and registry tests | verified |
| PS-32–PS-34 | transactional install, doctor, canonical v0.2 CLI | installer/CLI | isolated install/replace/doctor tests plus installed doctor | verified |
| AC-01–AC-02 | one installation, two independent real subjects, no Level 1 subject writes | installed CLI + disposable external labs | installed validate/selftest plus fresh tree/HEAD/status identity checks | verified |
| AC-03 | intake closes without lab/execution | pattern-intake | contract inspection and installed Skill validation | verified |
| AC-04 | claim-only observed receipt | observe | CLI unit test | verified |
| AC-05 | output-only legal case passes | verifier/runner | bundled fake-adapter regression | verified |
| AC-06–AC-07 | matched control plan and drift rejection | plan/runner | plan plus fake-adapter live-boundary tests | verified |
| AC-08 | process containment unchanged | process/verify | real descendant-process suite | verified |
| AC-09 | one-shot v1 migration and receipt | migration-only reader | real Softpowers migration and nine-case selftest in disposable lab | verified |
| AC-10 | one real ROT Audit controlled receipt before release | external live acceptance | saved plan + owner-authorized capped run | not verified; release gate open |

`AC-10` remains a release gate, not an implementation shortcut. The existing
ROT public forward receipt lacks the v2 attempt identity and raw trace required
to close it. A new target invocation needs an exact saved plan, selected case,
model/effort, and invocation cap; the current build request did not choose that
matrix or authorize spend.

## Execution tranches

1. **Contract freeze** — product spec, workspace model, schema delta, complete
   coverage ledger, and non-contradictory future/current documentation.
2. **Schema and migration** — v2 manifest/records plus a one-shot v1 migrator;
   normal runtime commands are v2-only.
3. **Materialization** — local path, local Git ref, snapshot, control, zero-write
   proof, and drift identity.
4. **Verification and runner** — final response, optional fixture/expected,
   review records, receipt v2, matched execution, and containment regression.
5. **Operations** — init, observe, promote, doctor, unified transactional
   installer, retired legacy aliases, and controller updates.
6. **Integration and closure** — examples, Softpowers/ROT notes, public docs,
   validation, user-level install verification, commit, and push. Tag/release
   remain a separate gate.

## Scope and order deltas

The owner confirmed that v0.1 had no external users. V0.2 therefore has one
active runtime instead of the originally proposed compatibility loader. The
only legacy route is explicit, one-shot `migrate-v1`; this still satisfies
AC-09 through migration and avoids maintaining a false dual product surface.

The six owner-respec sessions were executed as dependency tranches inside one
program plan. The contract-freeze tranche did not narrow or replace the
accepted v0.2 outcome.

## Full acceptance

Every non-external ledger row is verified, so v0.2 implementation source is
complete. Release readiness still requires AC-10 and fresh public release
checks. The installed copy, Git commit, pushed branch, tag, release, and live
subject receipt remain separate states.

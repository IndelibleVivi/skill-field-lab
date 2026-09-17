# Skill Field Lab

[简体中文](README.zh-CN.md)

> **Study before you install. Test only what matters.**

Skill Field Lab is a local maintainer workbench for learning from external
agent Skills, evolving reusable behavior, and producing claim-bounded evidence
without turning every useful mechanism into a dependency.

One user-level installation can study or exercise any explicitly selected
local subject. The subject remains independently owned and usable: Field Lab
does not copy its runtime into subject repositories, install subjects, or make
them depend on this project.

Current release contract: **0.2.0**. Its source acceptance includes one real,
capped target-agent canary. A local installation, Git tag, published assets,
controller discovery in a later task, and owner acceptance remain separate
observable states.

Architecture maps: [English](docs/ARCHITECTURE.md) ·
[简体中文](docs/ARCHITECTURE.zh-CN.md).

## The working model

```text
external source
  -> Pattern Intake
       -> ADOPT | ADAPT | REJECT | DEFER | ALREADY COVERED
       -> no lab is a valid completed result
       -> one unresolved claim, only when stronger evidence would matter
            -> Field Trial
                 -> existing ordinary-work evidence first
                 -> smallest no-spend plan if still unresolved
                 -> explicit capped live run only when separately authorized
```

Field Lab has three intervention levels:

1. **Level 0 — intake only.** `$pattern-intake` pins and studies one external
   mechanism. It needs no manifest, fixture, subject write, or model run.
2. **Level 1 — external local lab.** `fieldlab init` creates an inspectable lab
   anywhere you choose. It reads or materializes selected local sources into
   disposable workspaces and leaves subject repositories unchanged.
3. **Level 2 — subject-owned evidence.** `fieldlab promote` copies explicitly
   selected records to a chosen subject evidence directory. It never promotes
   the Field Lab runtime, manifest, plans, or run workspaces.

`$skill-eval` is displayed as **Field Trial** and is explicit-only. It owns the
evidence-path decision, not a global Skill score.

## Install once

Python 3.10+, Git, and Codex CLI are required. Live execution is POSIX-only in
v0.2; Windows fails closed until equivalent process containment exists.

```bash
python3 scripts/install.py
~/.local/bin/fieldlab doctor
```

The transactional installer writes:

- the dependency-free app to `~/.local/share/skill-field-lab`;
- the launcher to `~/.local/bin/fieldlab`;
- `pattern-intake` and `skill-eval` to
  `${CODEX_HOME:-~/.codex}/skills`; and
- an installation receipt inside the app.

It refuses unknown collisions. Use `--replace` for an intentional recognized
upgrade; the prior app, launcher, and controllers are copied to a recoverable
backup before replacement. Use `--cli-only` when controller discovery must
remain untouched. See [Installation and recovery](docs/INSTALLATION.md) for
custom paths, rollback, and clean uninstall.

## Start a v2 lab

```bash
fieldlab init /path/to/my-study --lab-id my-study
fieldlab validate /path/to/my-study/fieldlab.json
fieldlab list /path/to/my-study/fieldlab.json
```

`init` creates an isolated control and empty record/case directories. Add an
explicit local Skill source to `fieldlab.json`:

```json
{
  "schema_version": 2,
  "lab_id": "my-study",
  "description": "Test one unresolved reusable-agent behavior claim.",
  "subjects": {
    "isolated-control": {"kind": "control"},
    "my-skill": {
      "kind": "agent-skill",
      "source": {"type": "local-path", "path": "/path/to/subject/skills/my-skill"}
    }
  },
  "cases_root": "cases",
  "defaults": {
    "adapter": "codex-exec",
    "approval_policy": "never",
    "network_access": false,
    "output_root": "runs",
    "keep_workspace": false
  }
}
```

Supported sources are `local-path`, `local-git-ref`, lab-owned `snapshot`, and
`control`. Field Lab does not auto-clone URLs, resolve a marketplace, or guess
installed Skills.

Cases may assert the final agent response, workspace files, bounded commands,
raw trace properties, or declared human-review needs. `fixture/` and
`expected/` are optional. When an `expected/` oracle exists, this no-spend gate
proves the unresolved fixture fails and the expected overlay passes:

```bash
fieldlab selftest /path/to/my-study/fieldlab.json
```

The bundled examples cover a file-edit oracle and a legal-research case that
passes solely through final-response assertions:

```bash
fieldlab validate examples/demo/fieldlab.json
fieldlab selftest examples/demo/fieldlab.json
fieldlab validate examples/legal-research/fieldlab.json
fieldlab selftest examples/legal-research/fieldlab.json
```

## Existing work comes first

An ordinary trace, diff, test result, or review can bind directly to a claim;
a synthetic case is not mandatory:

```bash
fieldlab observe /path/to/my-study/fieldlab.json \
  --subject my-skill \
  --claim one-bounded-claim \
  --outcome supported \
  --artifact review=/path/to/review.md \
  --note "What the artifact establishes, and its limit."
```

Observed evidence is content-light and starts no target agent. A later human
review is stored separately and binds the immutable receipt digest.

Create that review with a JSON object whose keys exactly match the receipt's
declared human-review requirements. Omit `--requirement-outcomes` only when the
receipt declares none:

```bash
fieldlab review /path/to/my-study/fieldlab.json \
  --review-id one-bounded-review \
  --receipt /path/to/my-study/runs/one-attempt/receipt.json \
  --independence separate-agent \
  --judgment supported \
  --rationale "What the review supports and what remains unverified." \
  --requirement-outcomes /path/to/requirement-outcomes.json
```

Each value must be `supported`, `not-supported`, or `inconclusive`. Missing,
extra, duplicate, malformed, symlinked, or oversized outcome input fails closed.
The review command starts no target agent and never edits the receipt.

## Explain one claim before trusting it

`fieldlab explain` is read-only. It recomputes one claim's evidence view from
its claims, immutable receipts, and separate reviews; it never trusts the
hand-maintained `claim.status` and never counts a `PASS` as a conclusion:

```bash
fieldlab explain /path/to/my-study/fieldlab.json --claim one-bounded-claim
```

The report keeps `supported`, `unsupported`, and `inconclusive` evidence apart,
adds `mixed` when bound reviews disagree, and shows subject identity, sealed
worker-final output, verifier attribution, declared review material, and
retention when the receipt recorded them. It deduplicates the same receipt
copied to several canonical locations, labels legacy receipts that lack the
worker-final boundary marker `legacy-ambiguous`, lists pending, failed, or
conflicting review requirements and missing or digest-drifted artifacts, and
names the smallest next evidence gap. `--json` emits the same structure for
tooling. It starts no target model and modifies neither the lab nor the subject.

## Plan before any spend

Planning is read-only with respect to subjects and starts no target model:

```bash
fieldlab plan /path/to/my-study/fieldlab.json \
  --subject isolated-control \
  --subject my-skill \
  --case one-case \
  --mode matched \
  --repeat 1 \
  --model gpt-5.6-sol \
  --reasoning-effort high \
  --output /path/to/my-study/plans/one-plan.json
```

The plan enumerates every invocation and pins the manifest, prompt, case,
fixture, subject source, Field Lab source, and available Codex executable.
Changed input fails closed. Planning does not authorize execution.

A live run requires all three gates together:

```bash
fieldlab run /path/to/my-study/plans/one-plan.json \
  --live \
  --max-invocations 2
```

There are no implicit retries, graders, repeats, baselines, or full suites.
Target and verifier processes run in dedicated POSIX groups; evidence seals only
after the group is quiescent.

The runner seals the worker-final changed-file set, diff, and tree digest
before any verifier process starts. Workspace assertions read those sealed
worker bytes. Each command assertion starts from that same sealed tree in its
own byte copy, so no command inherits another command's edit; a change inside a
copy is attributed as verifier-derived, cannot turn the worker result into a
clean `pass`, and the copy is removed after the attempt. Sealing a diff uses a
disposable Git index copy, so the workspace index bytes and cached diff are
never mutated. This is the protected-source/derived-output contract, not a
claim of OS-level containment.

A live worker workspace is not retained. When a case declares human-review
requirements it may also declare `human_review_material`: exact
workspace-relative file paths that the pending review actually needs. Globs,
directories, symlinks, escaping paths, missing files, and over-limit sets are
rejected. Declared files are copied atomically before any verifier runs into
attempt-owned `review-material/` plus a manifest recording exact path, digest,
byte size, and fixed limits; the manifest digest and status are bound into
`verification.json` and the immutable receipt. A capture failure is an
evidence-sealing error: no partial material set, no normal receipt, and a
distinct `evidence-failed` attempt/run state rather than `termination-failed`.
Cases with review requirements but no declared material rely on the standard
attempt artifacts (`case.json`, `prompt.md`, `trace.jsonl`, `stderr.log`,
`final-output.md`, `diff.patch`, `verification.json`). `keep_workspace=true`
remains the only whole-workspace retention switch.

## V1 is migration input, not a runtime

There are no external v0.1 users, so v0.2 does not carry a dual runtime or
legacy command aliases. Normal commands accept `fieldlab.json` schema v2 only.
For Faye's own old packs:

```bash
fieldlab migrate-v1 /path/to/fieldlab-pack.json \
  --output /path/to/new-external-lab/fieldlab.json
```

The migrator preserves the source pack, rewrites cases to schema v2, snapshots
legacy overlays into the new lab, and records any semantic change in a
migration receipt.

## Evidence ceiling

Receipts keep independent dimensions separate:

- origin: `observed | synthetic`;
- subject scope: `isolated-control | workspace-scoped | hermetic`;
- comparison: `unmatched | single | matched`;
- verification methods: `deterministic | human | llm`; and
- independence: `implementer-run | separate-agent | external-reviewer`.

`hermetic` is reserved. Workspace-scoped evidence does not prove the selected
Skill was the exclusive cause. Requested model and effort are caller-selection
evidence unless the provider exposes stronger runtime identity.

## Repository map

| Path | Authority |
| --- | --- |
| `docs/PRODUCT_SPEC_V0.2.md` | Accepted product and acceptance contract |
| `docs/WORKSPACE_MODEL_V0.2.md` | Source identity, materialization, drift, and write boundaries |
| `docs/SCHEMA_DELTA_V1_TO_V2.md` | V2 object authority and one-shot migration mapping |
| `docs/ARCHITECTURE.md` / `docs/ARCHITECTURE.zh-CN.md` | Paired Mermaid maps of controller, workspace, execution, evidence, installation, and subject-ownership boundaries |
| `docs/EVIDENCE_MODEL.md` | Claim ceilings and receipt/review interpretation |
| `docs/INSTALLATION.md` | Install, upgrade, rollback, uninstall, and doctor |
| `schemas/v2/` | Active JSON Schemas |
| `schemas/v1/` | Historical schemas used only to understand migration inputs |
| `examples/` | Self-contained v2 labs |
| `case-studies/` | Integration notes and screened receipts; never subject source |

Softpowers and Repository Operational Truth Audit remain independent subjects.
Their own repositories own their Skills and cases; Field Lab stores only
integration notes and bounded evidence.

## V0.2 release evidence

On 2026-08-30, the installed v0.2 launcher ran one explicit
`source-artifact-split` canary against a snapshot of Repository Operational
Truth Audit: one target invocation, zero LLM graders, requested
`gpt-5.6-sol` / `high`, network disabled, and no retry. The deterministic
receipt passed and a separate implementer review accepted only the pinned
synthetic false-green claim.

This does not prove provider-resolved model identity, exclusive causality,
installed or activated subject behavior, arbitrary repositories, owner
acceptance, comparison superiority, or longitudinal reliability. See the
[bundle report](BUNDLE_REPORT.md) and the screened
[case study](case-studies/repository-operational-truth-audit.md).

Separately, the subject published its own `v0.2.0` release on 2026-09-17 with a
public forward receipt covering routing, Audit, and one-request Operate
behavior, plus a maintainer-side source-owner gate. Field Lab records that as
imported, dated observed evidence with explicit ceilings: it is not a Field Lab
rerun, raw trace, or installed/discovery/fresh-host/publication proof. The
[case study](case-studies/repository-operational-truth-audit.md) keeps the
2026-08-30 history and adds the 2026-09-17/18 section.

## Development verification

```bash
python3 -m unittest discover -s tests -p 'test*.py'
python3 scripts/check_bundle.py
skill-validate skills/pattern-intake
skill-validate skills/skill-eval
git diff --check
```

The test suite uses fake adapters for runner coverage. No ordinary repository
test starts a target model.

## Licensing

Project-original functional materials are source-available under SUL-1.0;
project-original standalone documentation is under CC BY-NC-SA 4.0. See
[LICENSING.md](LICENSING.md) for the path map. Third-party and independently
owned subject material remains under its own terms.

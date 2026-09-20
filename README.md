# Skill Field Lab

[简体中文](README.zh-CN.md)

> **Study before you install. Test only what matters.**

Skill Field Lab is a local maintainer workbench for one job: study an external
agent mechanism, decide whether it belongs in your own system, and only then pay
for the evidence that decision actually needs.

It is for the maintainer who owns reusable agent behavior — Skills, prompts,
harnesses, routing — and has to answer questions like *should this borrowed
mechanism land here?*, *how do I know this Skill actually changed the outcome?*,
and *can I answer that without a full benchmark run?* Taking every interesting
external idea into the local runtime is one risk; paying target-model
invocations for a claim that source inspection, a diff, or one small case could
already settle is another.

Field Lab works on one claim at a time and tries the cheapest sufficient
evidence path first. An instrumented synthetic trial is one option, not the
default.

Current version: **0.2.1**, source-verified — schema v2 is active, the runtime
is Python-3.10+ standard library only, and `codex-exec` is the only implemented
adapter. What that verification covers, and what it does not, is in
[Current state](docs/CURRENT_STATE.md), [CHANGELOG.md](CHANGELOG.md), and
[BUNDLE_REPORT.md](BUNDLE_REPORT.md).

| If you want to… | Start with |
| --- | --- |
| Understand the product and its three roles | [The ordinary path](#the-ordinary-path) |
| Install the app and controllers | [Install once](#install-once) |
| Keep evidence for an unresolved claim | [Start a v2 lab](#start-a-v2-lab) → [Existing work comes first](#existing-work-comes-first) |
| Understand what a receipt can prove | [What each lane can and cannot show](#what-each-lane-can-and-cannot-show) → [docs/EVIDENCE_MODEL.md](docs/EVIDENCE_MODEL.md) |
| Find any document | [docs/README.md](docs/README.md), the bilingual reading map |

## The ordinary path

```text
external source
  -> Pattern Intake          study + decision (no target-agent invocation, no subject write)
       -> ADOPT | ADAPT | REJECT | DEFER | ALREADY COVERED
       -> one unresolved claim, only when stronger evidence would change the decision
            -> Field Trial  inspect / observe existing work first
                 -> smallest no-spend plan if still unresolved
                 -> explicit capped live run only when separately authorized
```

**Pattern Intake** (`$pattern-intake`) pins an external source, distils one
portable mechanism, names the local problem it would solve, picks the lowest
landing plane, and closes with `ADOPT`, `ADAPT`, `REJECT`, `DEFER`, or
`ALREADY COVERED`. It makes no additional target-agent invocation — no lab, no
case, no subject write — and a study ending in `REJECT` or `DEFER` is a
completed result, not a study that gave up.

**Field Trial** (`$skill-eval`, explicit-only) owns the evidence path for one
unresolved claim, chosen in this order: inspect the source; observe existing
ordinary work; run a single canary; or run a matched trial. It looks for the
smallest sufficient evidence path rather than the most thorough one, and it
assigns no global Skill score.

**`fieldlab`** is the CLI evidence kernel when a study needs structured lab
records. It binds ordinary-work artifacts with `observe`, keeps later `review`
separate, and recomputes a claim's evidence with `explain`. For synthetic trials,
`plan` enumerates every invocation before `run` executes within the authorized
cap. It also manages labs, validation, snapshots, migration and selected-record
promotion. Source study can finish without using the CLI.

## A small example

The following example is illustrative, not a recorded run.

You find an adjacent repository whose Skill keeps single-file edits direct, and
ask whether that mechanism belongs in yours. Pattern Intake pins the source and
distils the mechanism; it either closes the question — your system already
covers it, or the fit is poor — or leaves one unresolved claim about your own
Skill's behavior. Field Trial then looks for that claim in work you already
have: a diff, a trace, a test result, a review. If that settles it, one
`fieldlab observe` records the evidence, and you write the decision. Only when
the claim is still unresolved *and* stronger evidence would change the decision
does a bounded trial earn its target-agent invocations. The disposition is
yours; Field Lab only keeps the reasoning and the evidence apart.

## Install once

Run the installer from this repository checkout. Python 3.10+, Git, and Codex
CLI are required for the full workflow. Live execution is POSIX-only in
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

`init` creates an isolated control and empty record/case directories. `list`
and `validate` inspect the lab; `selftest` runs declared deterministic checks in
disposable copies without a target invocation. `snapshot-git` pins one local Git
ref/path into a lab-owned snapshot; `promote` copies selected records into a
chosen subject evidence directory. Add an explicit local Skill source to
`fieldlab.json`:

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

Selftest reports `deterministic_oracle_status`, exercised/unexercised surfaces
and zero target invocations. It checks workspace/command assertions only;
result, trace and human review remain untested. `oracle_status` is a
compatibility alias. Output-only cases report `not-applicable` here, so the
legal-research example below does not prove final-response behavior by selftest.

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
tooling. It makes no additional target-agent invocation and modifies neither the
lab nor the subject.

## Plan before any spend

Planning is read-only with respect to subjects and makes no additional
target-agent invocation:

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

Every attempt re-verifies the actual subject mount against the saved plan before
invocation, and Git subjects stay on the planned resolved commit. Delivery
mismatch stops the matrix as `input-drift` with zero target calls for that
attempt; a materialization error is `preflight-failed`. These failure receipts
seal only preflight artifacts and make no worker-final or process-quiescence
claim.

The runner also seals the worker-final changed-file set, diff, and tree digest
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

## What each lane can and cannot show

Receipts keep independent dimensions apart instead of collapsing them into a
score:

- origin: `observed | synthetic`;
- subject scope: `isolated-control | workspace-scoped | hermetic`;
- comparison: `unmatched | single | matched`;
- verification methods: `deterministic | human | llm`; and
- independence: `implementer-run | separate-agent | external-reviewer`.

`hermetic` is reserved, and workspace-scoped evidence does not prove exclusive
causation. Requested model and effort are caller-selection evidence unless a
provider exposes stronger runtime identity. A live run also keeps three delivery
layers apart: the verified subject mount (`subject_delivery`), host selection
(unknown with the current adapter), and content application (needs semantic
review). `activation` is a declared scenario, not proof that a host activated a
Skill: trace `command_reference_mentions` and its
`command_reference_mentions_include` assertion prove command-path mentions only
— `echo references/example.md` qualifies without reading that file.
`reference_reads_include` remains a deprecated v2 assertion alias.

## V1 is migration input, not a runtime

At the v0.2 design decision, v0.1 had no external users, so v0.2 carries no dual runtime or
legacy command aliases. Normal commands accept `fieldlab.json` schema v2 only.
For an existing v1 pack:

```bash
fieldlab migrate-v1 /path/to/fieldlab-pack.json \
  --output /path/to/new-external-lab/fieldlab.json
```

The migrator preserves the source pack, rewrites cases to schema v2, snapshots
legacy overlays into the new lab, and records any semantic change in a
migration receipt.

## Where things live

| Path | What it is |
| --- | --- |
| [`docs/README.md`](docs/README.md) | Bilingual reading map: which document answers which question |
| [`docs/PRODUCT_SPEC_V0.2.md`](docs/PRODUCT_SPEC_V0.2.md) | Accepted product and acceptance contract |
| [`docs/EVIDENCE_MODEL.md`](docs/EVIDENCE_MODEL.md) | Claim ceilings, evidence dimensions, receipt/review interpretation |
| [`docs/CURRENT_STATE.md`](docs/CURRENT_STATE.md) | What is verified now, with proof layers kept separate |
| `schemas/v2/` | Active JSON Schemas (`schemas/v1/` documents migration inputs only) |
| `examples/` | Self-contained v2 labs |
| `case-studies/` | Integration notes and screened receipts for independent subjects; never subject source |

[docs/README.md](docs/README.md) is the shared reading map for workspace,
architecture, adapter, installation, and historical documents.

Softpowers and Repository Operational Truth Audit remain independent subjects.
Their own repositories own their Skills and cases; Field Lab stores only
integration notes and bounded evidence. `promote` remains the only Field Lab
operation that intentionally copies selected records into a chosen subject
evidence directory.

The dated v0.2.0 canary (one explicit `source-artifact-split` run against a
Repository Operational Truth Audit snapshot, one target invocation, zero
graders, no retry) and its claim ceiling live in the
[bundle report](BUNDLE_REPORT.md) and the screened
[case study](case-studies/repository-operational-truth-audit.md), not here. It
does not prove provider-resolved model identity, exclusive causality, installed
or activated subject behavior, arbitrary repositories, owner acceptance,
comparison superiority, or longitudinal reliability.

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

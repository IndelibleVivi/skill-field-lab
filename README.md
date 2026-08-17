# Skill Field Lab

A standalone field lab for people who maintain reusable agent skills and need to decide what to learn from external repositories, what to adapt locally, and what evidence is worth paying for.

Its first real subject is Softpowers. Softpowers remains a skill pack; Field Lab owns the generic evaluation protocol, bounded execution adapter, evidence contracts, and quota boundary.

## Governing rule

> Activation grants analysis, not spend. Live execution requires an explicit run boundary.

Installing a skill, loading a controller method, validating a pack, listing cases, writing a plan, or importing existing dogfood never starts a target-agent run. A live run requires both `fieldlab run --live` and an invocation cap.

## What is in the bundle

- `skills/pattern-intake/`: inspect an external repository, distill a mechanism, and record `ADOPT`, `ADAPT`, `REJECT`, `DEFER`, or `ALREADY COVERED` without automatically launching an eval.
- `skills/skill-eval/`: turn one concrete behavior claim into the smallest defensible evidence plan.
- `fieldlab/`: dependency-free Python runner and the first `codex-exec` adapter.
- `schemas/`: portable contracts for packs, cases, plans, receipts, candidates, claims, and decisions.
- `examples/demo/`: deterministic starter pack.
- `examples/legal-research/`: a non-DevOps example proving the core vocabulary is not hard-coded to Git diffs.
- `softpowers-companion/`: the current three Softpowers canaries and a migration-ready pack manifest.

## Controller–worker separation

The controller may load `pattern-intake` and `skill-eval`. The target worker receives only its prompt, disposable fixture, selected subject overlay, and permitted tools. It does not receive hidden assertions, expected output, candidate rationale, or evaluator instructions.

```text
external source
  -> candidate
  -> claim
  -> case
  -> no-spend plan
  -> explicit live attempt (optional)
  -> receipt
  -> decision
```

A candidate can stop at any point. Documentation-only intake decisions and imported dogfood need no synthetic target invocation.

## Run locally

The repository runs directly with Python 3.10+ and has no runtime dependencies or build step:

```bash
python scripts/check_bundle.py
```

For a user-level `fieldlab` command without relying on `pip` or a build backend:

```bash
python scripts/install_cli.py
fieldlab validate examples/demo/fieldlab-pack.json
```

The installer defaults to `${FIELDLAB_HOME:-~/.local/share/skill-field-lab}` and `${FIELDLAB_BIN_DIR:-~/.local/bin}`. It refuses to overwrite an existing directory or launcher unless `--replace` is supplied, and only replaces application directories carrying its own install marker.

`validate` checks contracts and paths. `selftest-pack` goes further: it creates disposable Git workspaces, proves each unresolved fixture fails at least one deterministic assertion, applies `expected/`, and proves every deterministic assertion passes. It may execute repository-owned command assertions, but it never starts a target model.

To install the two controller skills into the current user skill directory:

```bash
python scripts/install_skills.py
```

The installer copies them to `${FIELDLAB_SKILLS_DIR:-~/.agents/skills}` only when explicitly run. Repository-scoped subjects are overlaid into disposable workspaces under `.agents/skills/`.

## No-spend workflow

```bash
fieldlab list examples/demo/fieldlab-pack.json

fieldlab plan examples/demo/fieldlab-pack.json \
  --subject demo-subject \
  --case tiny-copy \
  --mode canary \
  --model <exact-model-id> \
  --reasoning-effort high \
  --output /tmp/demo-plan.json
```

The plan command prints the exact target invocation count, model/effort selection, subject attribution, approval/network settings, and each case sandbox/timeout. It pins the pack, prompt, fixture, case contract, subject overlay, Field Lab source, and available Codex executable digests. Any drift before `run --live` is rejected and requires a new no-spend plan. Planning does not call Codex.

For a baseline-ref versus current-candidate comparison, materialize the old subject tree without a model call:

```bash
fieldlab snapshot-git \
  --repo /path/to/softpowers \
  --ref <baseline-commit> \
  --source skills \
  --output /path/to/softpowers/.fieldlab-subjects/baseline-skills
```

Then use the matched companion manifest with two explicit subjects. The snapshot command writes a content-light commit/tree receipt beside the output and reports `Target-agent invocations: 0`.

Existing real work can be imported without rerunning it:

```bash
fieldlab import-observed examples/demo/fieldlab-pack.json \
  --subject demo-subject \
  --case tiny-copy \
  --outcome pass \
  --artifact diff=/path/to/diff.patch \
  --artifact verification=/path/to/verification.json \
  --note "Observed during ordinary repository work; unmatched dogfood." \
  --output /tmp/observed-receipt.json
```

## Explicit live boundary

```bash
fieldlab run /tmp/demo-plan.json \
  --live \
  --max-invocations 1
```

The run refuses to start when `--live` is absent, when the cap is absent, or when the plan exceeds the cap. V0.1 has no LLM grader and never runs a full suite implicitly.

## Evidence strength

Receipts keep these dimensions separate:

- origin: `observed` or `synthetic`;
- attribution: `ambient` or `repo_scoped` in v0.1;
- comparison: `unmatched`, `single`, or `matched`;
- verification: `deterministic` or `human`;
- independence: currently `implementer-run`.

`repo_scoped` uses a disposable repository overlay, an isolated worker `HOME`, and `--ignore-user-config`. The isolated home hides the official user-skill location while the operator's `CODEX_HOME` remains available for authentication. This proves where the selected overlay was mounted and removes the ordinary user-home skill/config surface; administrator, system, or undocumented legacy surfaces may still exist. V0.1 therefore never claims exclusive or hermetic attribution and rejects a pack that claims `hermetic` attribution.

## Model and effort identity

Canary and matched plans require explicit model and reasoning effort. Receipts call these `requested_model` and `requested_reasoning_effort`; they do not pretend a caller override is provider-side proof of the actual resolved model. Ambient defaults are allowed only through `environment-smoke`, which is non-comparison evidence, `repeat=1`, and not resumable.

## Bounded execution

On POSIX hosts every target process and every command assertion starts in a dedicated process group. A timeout, interrupt, or surviving descendant triggers group cleanup. Evidence is sealed only after quiescence is confirmed. A parent that exits while descendants survive is an error, even if its return code was zero.

Fixture and subject-overlay trees reject absolute or escaping symlinks before entering the disposable workspace. Internal relative symlinks are preserved.

Windows live execution fails closed in v0.1. A Windows Job Object adapter is required before the project can claim equivalent process-tree containment.

## Softpowers

Softpowers completed this migration at commit `4180b49`: its root
`fieldlab-pack.json` now owns the subject mapping, the three canaries remain in
Softpowers, and the generic runner plus generated `soft-eval` payload have been
retired. The copies under `softpowers-companion/` remain reusable fixtures and
provenance evidence. See `docs/SOFTPOWERS_INTEGRATION.md` and
`docs/MIGRATION_FROM_SOFT_EVAL.md`.

## Deliberate limits of v0.1

- one execution adapter: local Codex CLI;
- case sandboxes are limited to `read-only` and `workspace-write`; `danger-full-access` is rejected in v0.1;
- POSIX live execution only;
- no cloud dashboard, background monitor, leaderboard, or scheduled spend;
- no LLM judge;
- no claim that repo-scoped isolation is hermetic;
- no automatic publication, commit, tag, release, or external action;

## License

Skill Field Lab uses layered licensing:

- functional material—including the Python runtime, controller skills,
  schemas, scripts, manifests, fixtures, and tests—is licensed under
  [SUL-1.0](LICENSE);
- original documentation is licensed under
  [CC BY-NC-SA 4.0](LICENSE-DOCUMENTATION.md).

See [LICENSING.md](LICENSING.md) for the authoritative path and provenance map.

Codex plugin and package-index distribution are intentionally deferred; the
v0.1 release surface is the public source repository and its release archive.
See `docs/PACKAGING.md`.

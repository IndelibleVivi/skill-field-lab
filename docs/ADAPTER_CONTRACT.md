# Adapter contract

Status: v0.2; implemented adapter: `codex-exec` only.

The registry seam prevents the runner from being hard-coded to one constructor.
It does not make Field Lab provider-agnostic.

An adapter must provide:

- a stable adapter name;
- executable discovery and identity read-back;
- one command built from the ordinary prompt, disposable workspace, selected
  subject scope, sandbox, approval, network, requested model, and requested
  effort;
- streaming stdout JSONL and stderr paths supplied by the runner; and
- a bounded process result whose quiescence and termination reason come from
  the shared process kernel.

The adapter must not receive candidate rationale, evaluator instructions,
hidden assertions, expected artifacts, human-review rubrics, or decision
advice. It must not add implicit retries, graders, baseline runs, or network
permissions.

`codex-exec` uses `--ephemeral`, `--json`, `--ignore-user-config`, the declared
sandbox and approval policy, and an isolated worker home. Codex authentication
remains in the operator's selected `CODEX_HOME`; this supports
workspace-scoped evidence and is not represented as hermetic isolation.

The executable path and digest are pinned in the no-spend plan and checked
again before live execution. `--model` and `model_reasoning_effort` remain
requested selection evidence unless raw provider events establish more.

Any future adapter must reuse or strengthen plan drift checks, spend gates,
worker/controller separation, and process quiescence. It cannot weaken those
contracts merely because another provider exposes a different CLI.

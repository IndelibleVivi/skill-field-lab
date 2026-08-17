# Skill Field Lab working contract

## Product boundary

Skill Field Lab is an optional maintainer companion for reusable agent skills. Subject packs such as Softpowers remain usable without it. Never move generic process, quota, or evidence machinery back into a subject pack merely because that pack is the first dogfood user.

## Runtime and compatibility

- Python 3.10+.
- Standard library only in v0.1. The supported local path is `python -m fieldlab` or `scripts/install_cli.py`; tests must not depend on downloading a build backend.
- POSIX live execution only until a real Windows Job Object adapter exists.
- Reject `danger-full-access` in v0.1; a subject case may request only `read-only` or `workspace-write`.
- `fieldlab/` is canonical source. There is no generated runtime tree.
- Git subject snapshots are deterministic local artifacts and never invoke a target model.
- Repository subject overlays target `.agents/skills/` inside disposable workspaces. Reject absolute or tree-escaping fixture/overlay symlinks.

## Spend boundary

Do not invoke a real target model during tests, CI, validation, planning, installation, or ordinary review. A live run requires a saved plan plus `--live --max-invocations N`. Never broaden the matrix or add retries after that boundary without creating a new plan.

## Evidence correctness

- A parent exit is insufficient; seal artifacts only after execution-group quiescence.
- Reuse the bounded-process helper for target workers and command assertions.
- Fail closed when cleanup cannot be confirmed.
- Record caller selection as `requested_model` and `requested_reasoning_effort`; do not call it actual runtime identity without raw evidence.
- Bind pack, case, prompt, fixture, subject-overlay, Field Lab source, and available Codex executable digests into the saved plan. Live execution must fail closed on post-plan drift.
- `repo_scoped` injects the subject at repository scope, isolates the worker `HOME`, preserves `CODEX_HOME` only for authentication, and ignores user config. It still does not prove administrator, system, or undocumented legacy skill surfaces are absent, so it never supports an exclusive-subject claim.
- Raw trace remains authority. Summaries and receipts are derived.

## Verification

Run before handoff:

```bash
python scripts/check_bundle.py
```

Use fake executables for adapter regression. Do not weaken descendant-survival tests into mocks of `terminate()` or `kill()`.

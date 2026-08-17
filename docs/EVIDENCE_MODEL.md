# Evidence model

Evidence dimensions are orthogonal. A receipt may be:

```text
synthetic + repo_scoped + matched + deterministic + implementer-run
```

or:

```text
observed + ambient + unmatched + human + implementer-run
```

## Origin

- `observed`: evidence arose during ordinary work and was imported later.
- `synthetic`: Field Lab deliberately launched a case.

## Attribution

- `ambient`: the current CLI environment, including mutable user configuration.
- `repo_scoped`: a disposable repository with subject overlays, an isolated worker `HOME`, the official user-skill path hidden, and `$CODEX_HOME/config.toml` ignored. The operator's `CODEX_HOME` is retained for authentication. Administrator, system, or undocumented legacy skill surfaces may still be visible.
- `hermetic`: reserved until an adapter can prove complete subject visibility and isolation. V0.1 rejects it.

## Comparison

- `unmatched`: no controlled counterpart.
- `single`: one controlled subject/case attempt.
- `matched`: multiple subjects with the same case and execution identity.

## Verification

- `deterministic`: file, command, trace, or structured checks.
- `human`: an explicit review judgment.
- `llm`: reserved; not implemented in v0.1.

## Model identity wording

The runner records the exact requested model and effort overrides. It does not claim those fields are provider-side proof of the final served model. An adapter may add stronger resolved identity only when raw runtime evidence supports it.

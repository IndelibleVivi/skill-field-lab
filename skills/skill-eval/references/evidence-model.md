# Evidence dimensions

Keep these dimensions separate:

- origin: `observed | synthetic`
- subject scope: `isolated-control | workspace-scoped | hermetic`
- comparison: `unmatched | single | matched`
- verification methods: any applicable subset of `deterministic | human | llm`
- independence: `implementer-run | separate-agent | external-reviewer`

V0.2 supports isolated controls and workspace-scoped Skill materialization. Do not claim hermetic evidence until an adapter can prove complete isolation. A workspace-scoped receipt does not prove that only the selected Skill caused the result.

Observed evidence can bind directly to a claim without a case. Human review never rewrites an immutable execution receipt; it is a separate record that cites the receipt digest.

Explicit model and reasoning-effort fields are caller selection evidence. Call them `requested_*` unless raw runtime evidence establishes a stronger resolved identity.

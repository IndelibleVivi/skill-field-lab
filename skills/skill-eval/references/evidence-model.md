# Evidence dimensions

Keep these dimensions separate:

- origin: `observed | synthetic`
- attribution: `ambient | repo_scoped | hermetic`
- comparison: `unmatched | single | matched`
- verification: `deterministic | human | llm`
- independence: `implementer-run | separate-agent | external-reviewer`

V0.1 supports ambient and repo-scoped attribution. Do not claim hermetic evidence until the adapter can prove complete isolation.

Explicit model and reasoning-effort fields are caller selection evidence. Call them `requested_*` unless raw runtime evidence establishes a stronger resolved identity.

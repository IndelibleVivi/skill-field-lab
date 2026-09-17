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

Sealed attempt evidence has two separate surfaces. Worker-final bytes are the changed-file set, diff, and tree digest captured before any verifier command runs; each command assertion then runs in its own fresh copy of that sealed tree, and any change there is verifier-derived attribution, not worker output. A verifier that had to mutate its copy cannot produce a clean pass. A live workspace is not retained: declare bounded `human_review_material` exact workspace-relative files when a pending review needs them. `fieldlab explain` recomputes attribution, conflicting-review, and requirement facts from receipts and reviews instead of trusting `claim.status`.

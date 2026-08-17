# Contributing

Keep changes narrow and evidence-bounded.

A contribution that changes live execution, identity, receipt sealing, or spend behavior must include a deterministic regression. Do not use real model quota in CI. Process cleanup tests must launch actual descendants; mocked parent signals are insufficient.

New adapters must state their host and containment guarantees. New verifiers must remain outside the target worker context. New subject packs belong under examples or their own repositories and must not add domain-specific fields to the universal core without a demonstrated cross-domain need.

Contributions are accepted under the license governing the affected path in
`LICENSING.md`. Contributors retain copyright in their contributions; this
does not transfer ownership or authorize relicensing unrelated material.

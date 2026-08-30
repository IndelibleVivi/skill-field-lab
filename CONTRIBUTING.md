# Contributing

Keep changes narrow and evidence-bounded.

A contribution that changes live execution, identity, receipt sealing, or spend behavior must include a deterministic regression. Do not use real model quota in CI. Process cleanup tests must launch actual descendants; mocked parent signals are insufficient.

New adapters must state their host and containment guarantees. New verifiers must remain outside the target worker context. Generic self-contained labs may live under `examples/`; production subject Skills and cases belong to their own repositories. Do not add domain-specific fields to the universal core without a demonstrated cross-domain need.

Normal development targets schema v2 only. The v1 parser is migration-only;
do not restore dual-runtime tests or command aliases. Run the full unit suite,
bundle check, both controller validators, and `git diff --check` before handoff.

Contributions are accepted under the license governing the affected path in
`LICENSING.md`. Contributors retain copyright in their contributions; this
does not transfer ownership or authorize relicensing unrelated material.

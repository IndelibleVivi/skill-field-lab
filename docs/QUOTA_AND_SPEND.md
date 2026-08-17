# Quota and spend contract

Field Lab treats target-agent invocation as an external side effect.

## Actions that never start a target agent

- loading either controller skill;
- `fieldlab validate`;
- `fieldlab selftest-pack` (may execute repository-owned deterministic command assertions);
- `fieldlab list`;
- `fieldlab plan`;
- `fieldlab import-observed`;
- `fieldlab snapshot-git`;
- CI and unit tests;
- installing or copying skills;
- reading receipts and decisions.

These actions may occur inside an already-running assistant session, so they are described as **no additional target-agent invocation**, not as universally free.

## Live gate

A live execution requires all of the following:

1. a saved plan;
2. `fieldlab run`;
3. the `--live` flag;
4. `--max-invocations N` at or above the plan matrix count;
5. a supported adapter and host.

The plan reports target-agent and LLM-grader invocation counts together with model, effort, attribution, approval, network, sandbox, and timeout boundaries. It pins exact input digests; changed prompts, fixtures, case contracts, manifests, or subject overlays require a new plan. V0.1's grader count is fixed at zero.

## Defaults

- no implicit `--all`;
- `repeat=1`;
- one subject for a canary;
- explicit model and effort for comparison-capable evidence;
- no background runs;
- no scheduled runs;
- no automatic baseline;
- no automatic retry that increases the declared matrix.

## Existing dogfood first

Before creating a synthetic case, check whether an ordinary task already left useful trace, diff, tests, or human review. Import it as `observed + unmatched` evidence. Do not relabel it as a controlled experiment.

# Architecture

## Product boundary

Field Lab is a maintainer companion for reusable agent behavior. It is not part of the subject skill pack's ordinary runtime and subjects do not depend on it after installation.

The system has three planes:

1. **Controller skills** reason about external mechanisms, claims, cases, and evidence sufficiency.
2. **Runner core** validates contracts, creates disposable workspaces, invokes an adapter only across an explicit spend boundary, and seals receipts.
3. **Subject packs** own their candidates, claims, fixtures, assertions, receipts, and final evolution decisions.

## Core records

### Candidate

A pinned external source and one narrow mechanism. It records the exact source revision, reviewed files, local problem, accepted kernel, excluded machinery, and a provisional intake decision.

### Claim

One falsifiable behavior statement. It names the subject, observable change, adjacent behavior that must remain intact, and sufficient evidence. Field Lab does not score an entire skill with one number.

### Case

A stimulus plus disposable fixture and verifier contract. Activation cases should use ordinary blind prompts. Explicit method cases must say they are explicit.

### Plan

An immutable no-spend matrix binding subjects, cases, repeats, adapter request, requested model, requested effort, sandbox, approval policy, network setting, timeout, output location, and exact pack/case/prompt/fixture/subject-overlay digests. Drift before the live boundary invalidates the plan.

### Attempt

One target-agent invocation. Raw artifacts stay local by default.

### Receipt

A content-light evidence envelope with hashes, identity, outcome, evidence dimensions, and a truthful model-selection claim.

### Decision

The maintainer's `ADOPT`, `ADAPT`, `REJECT`, `DEFER`, or `ALREADY COVERED` result. A passing repair can support the narrow repair claim; broad improvement requires later comparable evidence.

## Why the evaluator cannot enter the worker context

An evaluator that tells the target to read references, avoid unnecessary commands, or preserve provenance changes the behavior it claims to observe. Controller instructions, hidden assertions, expected files, and candidate rationale therefore stay outside the disposable worker repository.

Only subject overlays are copied into `.agents/skills/`. For repo-scoped execution the adapter gives the worker an isolated `HOME`, preserves the operator's `CODEX_HOME` for authentication, and ignores user config. This removes the ordinary user-home skill/config surface without claiming administrator or system isolation. Verifiers run after the target execution group is quiescent.

## Adapter contract

An adapter must provide:

- a content-light executable identity;
- an exact command construction record;
- bounded execution;
- a terminal quiescence result;
- raw stdout/stderr artifacts;
- no silent fallback from explicit to ambient model selection.

An adapter that cannot prove cleanup reports termination failure and may not emit a normal terminal receipt.

## Deterministic pack credibility

`fieldlab validate` checks structure and paths. `fieldlab selftest-pack` checks oracle credibility without a target agent: the unresolved fixture must fail at least one deterministic assertion, and the repository-owned `expected/` overlay must pass all deterministic assertions. Command assertions use the same bounded-process helper as target execution.

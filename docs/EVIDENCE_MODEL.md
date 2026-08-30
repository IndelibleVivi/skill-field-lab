# Evidence model

Status: current v0.2 evidence contract.

Field Lab answers one question at a time: what is the weakest evidence that can
resolve this claim without overstating what happened?

## Claim authority

A claim contains:

- one falsifiable `statement`;
- the `observable_delta` that would distinguish it;
- `preserved_behaviors[]` that must not regress;
- one or more `sufficient_evidence[]` routes; and
- a status that never substitutes for the underlying receipt.

Candidate records do not own a final disposition. Decision records are the
sole owner of `ADOPT | ADAPT | REJECT | DEFER | ALREADY COVERED` and cite the
evidence actually used.

## Weakest sufficient lane

Use these lanes in order:

1. **Source inspection.** The mechanism and local contrast already resolve the
   decision. No receipt or local change is mandatory.
2. **Observed ordinary work.** An existing trace, diff, test, review, or other
   durable artifact binds directly to a claim. A case is optional.
3. **Single canary.** One subject receives the smallest synthetic case.
4. **Matched trial.** An isolated control and workspace-scoped Skill subject
   receive identical non-subject inputs, model request, effort, permissions,
   and repeats.

Field Lab does not add an LLM grader in v0.2. Human judgment is declared before
execution and recorded later as a separate review.

## Independent evidence dimensions

Never collapse these into one score:

| Dimension | Values | Meaning |
| --- | --- | --- |
| `origin` | `observed`, `synthetic` | Whether Field Lab executed the attempt |
| `subject_scope` | `isolated-control`, `workspace-scoped`, `hermetic` | What subject material was present and isolated |
| `comparison` | `unmatched`, `single`, `matched` | Whether comparable alternatives were exercised |
| `verification_methods[]` | `deterministic`, `human`, `llm` | How the evidence was checked |
| `independence` | `implementer-run`, `separate-agent`, `external-reviewer` | Who performed the judgment |

`hermetic` is reserved. An isolated worker home and ignored user config support
workspace-scoped evidence; they do not prove that every host influence is gone
or that the selected Skill was the exclusive cause.

## Attempt outcomes

Synthetic attempts seal exactly one of:

- `pass`;
- `fail`;
- `error`;
- `timeout`;
- `termination-failure`; or
- `inconclusive`.

Observed claim assessments use `supported`, `not-supported`, or `inconclusive`
and map to receipt outcomes without pretending an imported artifact was a
Field Lab execution.

## Verification surfaces

A v2 case can check:

- final response text inclusion, exclusion, regular expressions, or a bounded
  JSON Schema subset;
- workspace file content and exact changed-file set;
- bounded repository-owned commands;
- raw trace ceilings and required reference reads; and
- named human-review requirements.

Final response is first-class. A valid case may change no file and have no
fixture. `expected/` exists only when a deterministic known-fail/known-pass
oracle is useful.

## Receipt and review boundary

An attempt receipt records identity, subject scope, selection evidence,
process-quiescence result, verification summary, and content-light artifact
digests. The raw trace, final output, diff, stderr, and detailed verification
stay in the attempt directory.

Receipts are immutable. A human reviewer creates a separate record containing
the receipt path and SHA-256, independence, judgment, rationale, and requirement
outcomes. The review adds interpretation; it does not edit history.

## Claim ceilings

- A passing deterministic case supports only the encoded prompt, subject,
  environment, assertions, and pinned identities.
- A matched result is stronger comparison evidence, not proof of exclusive
  causation.
- Requested model and effort describe caller selection unless provider trace
  proves an actual resolved identity.
- A green test proves only its executed entrypoint and assertions.
- A public-safe screened receipt may omit private raw artifacts, but every
  omitted layer must remain `UNKNOWN` or explicitly unverified.
- Source, committed code, installed bytes, activated discovery, live execution,
  and owner acceptance remain separate evidence gates.

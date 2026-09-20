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
- `termination-failure`;
- `input-drift` or `preflight-failed` before any target invocation; or
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
- raw trace ceilings and required command-path mentions; and
- named human-review requirements.

Final response is first-class. A valid case may change no file and have no
fixture. `expected/` exists only when a deterministic known-fail/known-pass
oracle is useful.

## Worker output and verifier derivation

An attempt has two distinct byte surfaces:

- the **worker-final** surface: the changed-file set, diff, and tree digest
  captured immediately after the worker process group is quiescent and before
  any verifier command runs; and
- the **verifier** surface: each deterministic command assertion runs in its
  own disposable byte copy of that sealed tree.

Workspace and file assertions read the sealed worker-final tree, so a verifier
cannot satisfy them by repairing the artifact under test. `diff.patch` and the
receipt's `changed_files` describe worker bytes only. Every command assertion
starts from the same sealed tree, so no command inherits another command's edit.
A change inside a copy is attributed in the verification record and, when
non-empty, written as a separate `verifier-diff-<index>.patch`; the copy is
removed after the attempt. Because a verifier that had to mutate its own copy is
not a clean oracle, such an attempt cannot be sealed as `pass`; it becomes
`inconclusive` unless a declared assertion already failed on the sealed worker
bytes. Sealing a diff uses a disposable Git index selected through
`GIT_INDEX_FILE`, so the workspace's own index bytes and cached diff are never
mutated.

This protects the actual worker-source/derived-output contract. It is not a
claim that verifier commands are contained by the operating system: they still
run with the case's declared sandbox and host tools.

## Receipt and review boundary

An attempt receipt records identity, subject scope, selection evidence,
process-quiescence result when a target ran, verification summary, and content-light artifact
digests. The raw trace, final output, diff, stderr, and detailed verification
stay in the attempt directory.

Receipts are immutable. A human reviewer creates a separate record containing
the receipt path and SHA-256, independence, judgment, rationale, and requirement
outcomes. The review adds interpretation; it does not edit history.

When the receipt declares human-review requirements, the public review command
requires one outcome for every exact requirement and rejects missing, extra, or
unsupported values. A receipt with no declared requirements uses an empty
mapping. This per-requirement record does not make the review rationale
self-authenticating or expand the claim beyond the inspected evidence.

Requirement-outcome input is read as a bounded regular file: invalid UTF-8,
duplicate keys, a non-object root, non-string or unrecognized values, an
oversized file, a symlinked file, or a file below a user-controlled symlinked
directory all fail as controlled configuration errors before any review record
is written. The file is opened non-blocking when the platform supports it and
then required to be regular, so a FIFO or other non-regular file is rejected
instead of stalling the command. Ordinary absolute paths are accepted even when
a system ancestor such as macOS `/var` is a symlink.

`fieldlab explain` computes a per-claim view from claims, receipts, and separate
reviews. It never reads `claim.status` as evidence and never counts a `PASS` as
a conclusion. It reports `supported`, `not-supported`, `inconclusive`, and
`mixed` separately, deduplicates the same receipt copied to several canonical
locations by raw receipt SHA-256 while keeping every location, and never picks a
latest winning review: bound reviews that disagree in judgment or in any exact
requirement outcome mark that receipt conflicting and the claim aggregate
`mixed`. Reviewer independence is displayed, not used as automatic weighting.
A required review that is absent stays pending, and digest-mismatched reviews do
not contribute. Attempt receipts that lack the worker-final boundary marker stay
readable but are labeled `legacy-ambiguous`; they are never described as sealed
before a verifier, and they cannot carry a claim to `supported` on their own.
The view also shows subject identity when the receipt recorded it, missing or
digest-drifted artifacts, and the smallest next evidence gap. It is read-only
and starts no target model.

## Retention and lifecycle

Raw attempt evidence lives in the attempt directory as a content-light receipt
plus sealed artifacts. A live worker workspace is large mutable state and is
not retained; `keep_workspace=true` is the only whole-workspace switch.

When a case declares human-review requirements it may also declare
`human_review_material`: a unique list of exact workspace-relative file paths.
Globs, directories, symlinks, escaping paths, missing files, and over-limit
sets are rejected, and the case contract refuses the field without declared
review requirements. After worker quiescence and before any verifier runs, the
declared files are copied atomically into attempt-owned `review-material/` plus
a manifest recording exact path, digest, byte size, and the fixed runtime
limits. The manifest digest and status are bound into `verification.json` and
the immutable receipt. A capture failure is an evidence-sealing error: no
partial material set remains and no normal receipt is written. Because the
worker process was already quiescent, the attempt metadata records
`state: evidence-failed`, `outcome: error`, and a bounded error reason, and the
run summary records `evidence-failed` rather than `termination-failed`; a
process-termination or cleanup failure keeps the existing `termination-failed`
path.

Cases with review requirements but no declared material rely on the standard
attempt artifacts (`case.json`, `prompt.md`, `trace.jsonl`, `stderr.log`,
`final-output.md`, `diff.patch`, `verification.json`).

## Subject identity and declared payloads

Subject identity is the exact raw tree digest of the mounted `local-path`,
`local-git-ref`, or `snapshot` source. It deliberately keeps exact-tree
meaning: every non-Git-metadata file below the source, including otherwise
ignorable build residue, is part of the digest, and undeclared entries are never
silently ignored. The existing digest excludes `.git` metadata and includes
relative file paths, bytes, executable markers, and symlink targets.

A subject may separately publish its own declared payload, such as an explicit
distributable file list with its own digest. That is a subject-owned
declaration about the subject's release surface. V0.2 adds no Field Lab payload
selection, no hard-coded subject file list, and no payload-identity receipt
field; narrowing a subject tree to a payload would need one declaration
governing validation, digest, materialization, and receipt provenance. When
present, a subject's declared payload is recorded as imported subject evidence,
not as a Field Lab subject identity.

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

## Delivery, selection, and application (0.2.1)

Do not substitute one layer for another:

| Surface | What it establishes | What it does not establish |
| --- | --- | --- |
| `subject_delivery` | Each materialized mount matches the saved plan, or failed before target invocation | Host Skill selection or semantic use |
| `host_selection` | Unknown with the current adapter; observed requires structured host evidence | A declared `activation` scenario alone proves nothing about selection |
| `content_application` | Requires semantic review of actual behavior | A command-path mention is not a content read or method application |

Delivery fields are `mount`, `source_type`, `expected_tree_sha256`,
`actual_tree_sha256`, `requested_ref`, `resolved_commit`, and `status`. Controls
verify no Field Lab overlay and carry null mount/digests; they do not certify an
instruction-free host. Missing historical delivery evidence stays `unknown` in
`explain`, separately from the legacy worker-final sealing boundary.

The parser reports `command_reference_mentions` extracted from command strings.
`echo references/worktree.md` is a mention without a content read. Host injection
can deliver a Skill without any command mention. Assert mentions with
`command_reference_mentions_include`; `reference_reads_include` remains a
deprecated v2 alias. When both are present, their union is asserted. The emitted
assertion result uses the canonical name. Old receipts are never rewritten.

Selftest's `deterministic_oracle_status` concerns known-fail/known-pass fixture
and overlay consistency only. `exercised_surfaces` lists the present workspace
and command assertions it evaluated; `unexercised_surfaces` includes result,
trace, human review, and any unexercised deterministic surface. A case without an
expected overlay has no exercised surfaces. Every case reports zero target
invocations. `oracle_status` is a compatibility alias for this limited status.

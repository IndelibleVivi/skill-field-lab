# Architecture

[简体中文](ARCHITECTURE.zh-CN.md)

Status: current v0.2 source contract.

This map answers one question: how does Skill Field Lab turn a source study
into claim-bounded evidence without hiding model spend or taking ownership of
the subject repository?

The boxes are logical responsibilities, not independently deployed services.
Skill Field Lab has no daemon, global registry, background scheduler, or
subject runtime dependency.

## System overview

```mermaid
flowchart TB
  %% Semantic node IDs are kept identical to the Simplified Chinese sibling.
  subgraph INSTALLED["User-level installation · derived deployment"]
    direction LR
    InstalledSurface["Maintainer-controlled installed surface<br/>transactional app + launcher + controllers<br/>doctor proves bytes + provenance only<br/>≠ discovery · live behavior · owner acceptance"]
  end

  ExternalSource["External mechanism source<br/>pin + inspect; never adopted by default"]

  subgraph LAB["Study + external v2 lab · visible Field Lab-owned state"]
    direction LR
    PatternIntake["Pattern Intake · Level 0<br/>source study · no target spend"]
    LabState["Visible schema-v2 lab state<br/>manifest · candidate · claim · optional case<br/>plans · attempts · evidence records"]
    LaneChoice{"Field Trial · explicit only<br/>weakest sufficient lane?"}
    ObservedLane[("Source conclusion or observed evidence<br/>claim-bound ordinary-work artifact<br/>no target invocation")]

    PatternIntake -->|unresolved candidate + claim| LabState
    LabState --> LaneChoice
    PatternIntake -->|source study is sufficient| ObservedLane
    LaneChoice -->|ordinary evidence is sufficient| ObservedLane
  end

  subgraph EXECUTION["Disposable execution boundary · synthetic lane only"]
    direction LR
    SyntheticLane["Immutable no-spend plan → explicit live gate<br/>--live · exact cap · authorization · drift re-pin<br/>read/pin subject → disposable workspace · isolated HOME<br/>ordinary worker context → deterministic verification<br/>quiescent immutable receipt; raw artifacts stay in lab"]
  end

  subgraph EVIDENCE["Evidence and decision authority"]
    direction LR
    EvidenceDecision["Immutable observed or synthetic record<br/>human review remains separate + digest-bound<br/>Decision: ADOPT · ADAPT · REJECT<br/>DEFER · ALREADY COVERED"]
  end

  subgraph SUBJECT["Independent subject repository · subject-owned"]
    direction LR
    SubjectRepo["Canonical Skill + cases + docs<br/>subject owns source + release state<br/>and any selected evidence directory"]
  end

  ExternalSource -->|pin + study| PatternIntake
  InstalledSurface -->|Pattern Intake controller| PatternIntake
  InstalledSurface -->|fieldlab CLI + Field Trial controller| LabState

  LaneChoice -->|synthetic evidence is still needed| SyntheticLane
  ObservedLane --> EvidenceDecision
  SyntheticLane --> EvidenceDecision
  EvidenceDecision ==>|promote · only intentional subject write<br/>selected records only| SubjectRepo

  classDef entry fill:#eef2ff,stroke:#4f46e5,color:#111827,stroke-width:1.5px;
  classDef action fill:#eff6ff,stroke:#2563eb,color:#111827,stroke-width:1.5px;
  classDef state fill:#ecfdf5,stroke:#059669,color:#111827,stroke-width:1.5px;
  classDef gate fill:#fff7ed,stroke:#ea580c,color:#111827,stroke-width:2px;
  classDef execution fill:#f0fdfa,stroke:#0f766e,color:#111827,stroke-width:1.5px;
  classDef authority fill:#fdf2f8,stroke:#be185d,color:#111827,stroke-width:2px;
  classDef subject fill:#f5f3ff,stroke:#7c3aed,color:#111827,stroke-width:1.5px;

  class ExternalSource entry;
  class InstalledSurface,PatternIntake action;
  class LabState,ObservedLane state;
  class LaneChoice gate;
  class SyntheticLane execution;
  class EvidenceDecision authority;
  class SubjectRepo subject;

  style INSTALLED fill:#f8fafc,stroke:#64748b,stroke-width:1px;
  style LAB fill:#f7fee7,stroke:#65a30d,stroke-width:1px;
  style EXECUTION fill:#f0fdfa,stroke:#0f766e,stroke-width:1px;
  style EVIDENCE fill:#fdf4ff,stroke:#a21caf,stroke-width:1px;
  style SUBJECT fill:#faf5ff,stroke:#7c3aed,stroke-width:1px;
```

## How to read the map

1. **Study can finish before a lab exists.** Pattern Intake may resolve the
   question from source evidence and produce a decision or no-change result
   with no target invocation.
2. **The lab owns evidence state, not subject source.** `fieldlab.json`, cases,
   plans, attempts, receipts, reviews, and decisions remain in a visible
   external v2 lab.
3. **Planning and execution are different gates.** A plan starts no target
   model. Synthetic execution additionally requires the saved plan, `--live`,
   an exact invocation cap, and separate maintainer authorization.
4. **Evaluator-only material stays out of worker context.** The target receives
   the ordinary case prompt and disposable workspace; hidden assertions,
   expected artifacts, and review rubrics remain controller-side.
5. **Receipts do not absorb later judgment.** Attempt evidence seals only after
   process-group quiescence. Human review is a separate digest-bound record;
   Decision alone owns final disposition.
6. **Subject source enters execution read-only.** The synthetic-lane node calls
   out its pin-and-materialize boundary. The thick `promote` edge is the only
   intentional subject write, and it carries selected records only—never the
   runtime, manifest, plans, or run workspaces.

## Controller plane

`pattern-intake` studies one mechanism and may finish with `ADOPT`, `ADAPT`,
`REJECT`, `DEFER`, or `ALREADY COVERED` without creating a lab. It is allowed
to invoke implicitly because it starts no target model and grants no write or
installation authority.

`skill-eval`, displayed as **Field Trial**, is explicit-only. It receives one
unresolved claim, looks for existing ordinary-work evidence first, then designs
the weakest sufficient synthetic path only if the decision still needs it.
Controller instructions, hidden assertions, expected artifacts, and evaluator
advice never enter the target-worker prompt.

## Workspace plane

`fieldlab.json` owns one inspectable lab. The active loader accepts schema v2
only. A lab can point to:

- an external `local-path`;
- one `local-git-ref` plus repository-relative subpath;
- a lab-owned immutable `snapshot`; or
- an `isolated-control` with no subject overlay.

All execution happens in disposable Git workspaces. Fixture and source
symlinks are checked before copy. Local paths and Git refs are content-pinned
into the plan; drift before execution rejects the plan. Level 1 operations do
not write to the subject repository.

## Execution plane

The adapter registry currently exposes one real adapter: `codex-exec`.
Provider independence is not claimed. The adapter:

- passes only the ordinary case prompt and disposable workspace to the worker;
- ignores user config and isolates worker `HOME` while retaining the operator's
  Codex authentication directory;
- uses the declared sandbox, approval, network, requested model, and requested
  reasoning effort; and
- streams raw JSONL trace and stderr into the attempt directory.

The runner preserves the v0.1 execution kernel:

1. `plan` starts no target model and enumerates every invocation.
2. `run` requires a saved plan, `--live`, and `--max-invocations`.
3. Manifest, case, prompt, fixture, subject, Field Lab source, and available
   executable identity are re-pinned immediately before execution.
4. Target and command-verifier processes use dedicated POSIX process groups.
5. Timeout, interrupt, parent-exit-with-child, and cleanup failure all converge
   on bounded group termination.
6. Evidence seals only after group quiescence. A termination failure cannot be
   represented as a normal pass.

Windows live execution remains unsupported because v0.2 has no equivalent Job
Object containment adapter.

## Evidence plane

The record chain is:

```text
source -> candidate -> claim -> [case -> plan -> attempt -> receipt] -> decision
```

The bracketed synthetic chain is optional. `observe` may bind an existing
artifact directly to a claim. Candidate describes a mechanism and local fit;
Decision alone owns the final disposition. A sealed receipt is immutable;
later human judgment lives in a separate review record bound to its digest.

Raw attempt artifacts stay in the lab. Receipts are content-light digests and
bounded summaries. `promote` copies only selected candidates, claims, cases,
receipts, reviews, and decisions. It never promotes the runtime, lab manifest,
plans, or run workspaces.

## Installation plane

`scripts/install.py` stages the app, launcher, and controllers before any
replacement. It recognises only its own marker, launcher, current controller
digests, or the two known v0.1 controller digests. Existing targets are copied
to a recoverable backup; adjacent rollback identities remain available until
the entire replacement commits. A mid-commit failure restores prior targets.

The installed app carries source controller copies so `fieldlab doctor` can
compare installed discovery bytes with the installation source. Installed
bytes still do not prove next-turn Skill discovery or any target behavior.

## Legacy boundary

V1 is not an alternate architecture. `migrate-v1` is an offline parser that
creates a separate v2 lab, rewrites legacy cases, snapshots overlay sources,
and records semantic changes. Every normal command thereafter uses the single
v2 object and execution model.

# V0.2 workspace model

Status: normative companion to
[PRODUCT_SPEC_V0.2.md](PRODUCT_SPEC_V0.2.md).

## Local lab

`fieldlab init <directory>` creates a visible, ordinary directory:

```text
<lab>/
├── fieldlab.json
├── candidates/
├── claims/
├── cases/
├── plans/
├── runs/
├── receipts/
├── reviews/
└── decisions/
```

The manifest and records are the registry. Field Lab creates no hidden global
database and does not enroll subject repositories.

## Subject sources

Each v2 subject is either `kind: agent-skill` with one structured `source`, or
`kind: control`.

### `local-path`

```json
{
  "kind": "agent-skill",
  "source": {
    "type": "local-path",
    "path": "../repository/skills/example"
  }
}
```

The path is resolved relative to the lab root and may intentionally resolve
outside it. Plan identity records the physical resolved path, tree digest, and
the containing Git repository identity when one exists. Run-time identity is
recomputed; content or Git identity drift rejects execution.

### `local-git-ref`

```json
{
  "kind": "agent-skill",
  "source": {
    "type": "local-git-ref",
    "repo": "../repository",
    "ref": "v1.2.0",
    "subpath": "skills/example"
  }
}
```

The repository must already be local. Planning resolves `ref` to a commit and
computes the selected archived tree digest. Materialization uses that exact
local Git object rather than the mutable working tree. A moved ref causes plan
drift and requires a new plan.

### `snapshot`

```json
{
  "kind": "agent-skill",
  "source": {
    "type": "snapshot",
    "path": "snapshots/example"
  }
}
```

Snapshots must remain inside the lab root. Their tree digest is pinned at plan
time and checked again before execution. `snapshot-git` remains the supported
way to create a commit-pinned local tree and sidecar receipt.

### `control`

```json
{
  "kind": "control"
}
```

A control has no subject overlay. It still receives a disposable Git workspace,
isolated worker home, ignored user config, the same prompt/fixture/model/effort,
and the same permissions as its matched Skill subject. Its evidence scope is
`isolated-control`; it is not an ambient default.

## Subject mounting

An `agent-skill` source defaults to `.agents/skills/<subject-id>` in the
disposable worker. A manifest may set `mount` to another safe workspace-relative
path, including `.agents/skills` for a source tree containing several Skills.
The mount never changes the source repository.

## Identity and drift

Every saved plan binds:

- canonical manifest content and manifest schema version;
- selected case contract, prompt, optional fixture, and activation mode;
- every selected subject source type, resolved physical locator, Git identity
  where applicable, tree digest, mount, and subject scope;
- Field Lab Python source;
- the requested and currently resolved adapter executable; and
- the exact matrix and execution boundary.

Immediately before live execution, Field Lab recomputes these inputs. Any
difference rejects the run and names a new no-spend plan as the recovery path.

This identity is the **exact raw tree digest** of the mounted source. Every file
below the source belongs to it, including otherwise ignorable build residue;
undeclared entries are never silently skipped. A subject may separately publish
its own declared payload identity for its distributable files. That declaration
belongs to the subject: v0.2 selects no Field Lab payload subset, hard-codes no
subject file list, and records no payload-identity receipt field. Narrowing a
tree to a declared payload would require one declaration governing validation,
digest, materialization, and receipt provenance.

## Materialization safety

- Level 1 materialization only reads subjects and writes disposable run state.
- Absolute symlinks and symlinks escaping a fixture or source tree are rejected.
- `snapshot` paths must stay within the lab root.
- `local-git-ref` archive members must remain under the requested subpath and
  must be regular files or directories.
- Control materialization has no subject source to copy.
- A missing optional `fixture/` produces an empty disposable Git repository.
- Field Lab never follows a remote URL, installs a referenced subject, or
  writes a lockfile into the subject repository.

## Verifier copy

After the worker process group is quiescent, the runner seals the worker-final
changed-file set, diff, and tree digest. Workspace assertions read that sealed
tree. Each command assertion then runs in its own disposable byte copy of the
same sealed tree, so no command inherits another command's edits. Any derived
change is attributed in `verification.json` and written as a separate
`verifier-diff-<index>.patch` when non-empty; it cannot by itself produce a
`pass`. Each copy is deleted after its command and is never sealed as evidence.
Diff sealing uses a disposable Git index via `GIT_INDEX_FILE`, so the workspace
index and cached diff stay untouched.

## Retention and declared review material

The attempt directory always keeps the content-light receipt plus sealed
artifacts (`case.json`, `prompt.md`, `trace.jsonl`, `stderr.log`,
`final-output.md`, `diff.patch`, `verification.json`, `metadata.json`, and any
`verifier-diff-<index>.patch`).

The live worker `workspace/` is large mutable state and is not retained. The
plan-level `keep_workspace` switch is the only way to keep the whole workspace.

A case that declares human-review requirements may declare exactly what the
pending review needs through `human_review_material`: a unique list of exact
workspace-relative file paths. The field is omitted from normalization when it
is absent, so existing case identities and plans do not drift. Globs,
directories, symlinks, escaping paths, missing files, non-regular files,
unreadable files, and over-limit sets are rejected; the field is refused when
the case declares no review requirements.

After worker quiescence and before any verifier runs, the declared files are
copied atomically into attempt-owned `review-material/` with a manifest that
records the exact source path, digest, byte size, and the fixed runtime bounds.
The manifest path, digest, and status are bound into `verification.json` and the
immutable receipt. A capture failure is an evidence-sealing error: the staging
tree and any installed material directory are removed, no normal receipt is
written, and the attempt cannot pass. The attempt metadata records
`state: evidence-failed`, `outcome: error`, and a bounded error reason, and the
run summary records `evidence-failed`; process-termination and cleanup failures
stay on the existing `termination-failed` path.

Cases with review requirements but no declared material rely on the standard
attempt artifacts rather than a retained workspace.

## Promotion boundary

`fieldlab promote` copies only selected lab records from recognised record
directories. It rejects runtime, plans, mutable run workspaces, launchers,
unrecognised source paths, destination collisions, and a destination equal to
the lab root. It never commits or pushes. Promotion is the explicit Level 2
write boundary; source inspection, validation, listing, planning, observing,
and running remain Level 1 operations.

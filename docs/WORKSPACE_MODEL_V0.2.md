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

## Promotion boundary

`fieldlab promote` copies only selected lab records from recognised record
directories. It rejects runtime, plans, mutable run workspaces, launchers,
unrecognised source paths, destination collisions, and a destination equal to
the lab root. It never commits or pushes. Promotion is the explicit Level 2
write boundary; source inspection, validation, listing, planning, observing,
and running remain Level 1 operations.

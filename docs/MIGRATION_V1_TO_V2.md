# One-shot migration from v1

Status: current v0.2 operator guide.

V0.2 has one active runtime contract: schema-v2 `fieldlab.json`. The legacy
reader exists only inside `migrate-v1`; normal commands reject v1 packs.

```bash
fieldlab migrate-v1 /path/to/fieldlab-pack.json \
  --output /path/to/new-lab/fieldlab.json
```

Preconditions:

- the source is a valid schema-v1 pack;
- every overlay source exists;
- the output file is named `fieldlab.json`;
- the output parent does not yet exist; and
- the output lab is separate from the source pack root.

The migrator:

1. validates the legacy manifest, subjects, paths, cases, prompts, and
   deterministic assertions;
2. creates a new lab transactionally;
3. rewrites every v1 case to schema v2, including split workspace/command
   assertions and `activation: implicit`;
4. copies legacy overlay sources into lab-owned snapshot subjects;
5. maps a legacy ambient subject to `isolated-control` and marks that semantic
   change explicitly;
6. validates the completed v2 manifest and cases before publication; and
7. writes a migration receipt with source/output identities, subject mappings,
   case-tree identity, and zero target invocations.

The source manifest and source subject are never modified or deleted. A
migrated snapshot is a point-in-time copy; later source changes do not silently
enter the lab. Create a deliberate new snapshot or use an explicit local source
when later drift should be studied.

After migration, use only canonical commands:

```bash
fieldlab validate /path/to/new-lab/fieldlab.json
fieldlab selftest /path/to/new-lab/fieldlab.json
fieldlab list /path/to/new-lab/fieldlab.json
```

Review any `semantic_change: true` entry before planning. Migration preserves
data and provenance; it does not claim that ambient and isolated-control
evidence mean the same thing.

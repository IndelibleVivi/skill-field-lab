# Packaging and distribution

Status: v0.2 source contract; no v0.2 tag or public release is implied here.

The supported local distribution surface is the stdlib-only transactional
installer:

```bash
python3 scripts/install.py
```

It installs one app, launcher, both controller Skills, and a provenance
receipt. `pyproject.toml` remains valid Python packaging metadata but is not
required for the ordinary local path. Subject Skills and cases stay in their
own repositories and are never bundled into the app.

The installed app includes `fieldlab/`, controller source, active/historical
schemas, templates, version, and licensing files so `doctor` can verify the
installation without relying on the source checkout.

A future Codex plugin or marketplace projection is a separate distribution
decision. Do not add a plugin manifest until its current host contract,
permissions, update model, uninstall behavior, and source/install provenance
have been checked. Any projection must preserve the independent CLI, the
explicit spend gate, and subject ownership.

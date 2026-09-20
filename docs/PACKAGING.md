# Packaging and distribution

Status: latest published packaging is v0.2.0; current source is an unreleased
0.2.1 candidate. The archive names below describe the published v0.2.0 assets.

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

The GitHub Release distribution consists of an exact tagged source archive and
its checksum:

```text
skill-field-lab-v0.2.0.zip
skill-field-lab-v0.2.0.zip.sha256
```

The archive is generated from tag `v0.2.0` with the top-level prefix
`skill-field-lab-v0.2.0/`. Verify the adjacent checksum before extraction;
after extraction, `shasum -a 256 -c BUNDLE_MANIFEST.sha256` and
`python3 scripts/check_bundle.py` validate tracked bundle identity and behavior.

A future Codex plugin or marketplace projection is a separate distribution
decision. Do not add a plugin manifest until its current host contract,
permissions, update model, uninstall behavior, and source/install provenance
have been checked. Any projection must preserve the independent CLI, the
explicit spend gate, and subject ownership.

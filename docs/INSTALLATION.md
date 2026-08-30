# Installation, recovery, and uninstall

Status: current v0.2 operator guide.

## Default install

```bash
python3 scripts/install.py
```

Default targets:

| Surface | Path |
| --- | --- |
| application | `~/.local/share/skill-field-lab` |
| launcher | `~/.local/bin/fieldlab` |
| controllers | `${CODEX_HOME:-~/.codex}/skills/{pattern-intake,skill-eval}` |
| backups | `~/.local/share/skill-field-lab-backups/<timestamp>-<id>/` |

Ensure `~/.local/bin` is on `PATH`, or invoke the launcher by its full path.

Verify the exact installed layer:

```bash
~/.local/bin/fieldlab doctor --json
```

`doctor` is read-only. It checks marker and receipt provenance, installed
Field Lab version/source, controller digest equality, Python, Git, Codex,
POSIX support, and the selected Skill discovery path. It reports zero target
invocations. It does not prove next-turn Skill discovery.

## Custom paths

```bash
python3 scripts/install.py \
  --app-dir /chosen/app \
  --bin-dir /chosen/bin \
  --skills-dir /chosen/codex/skills \
  --backup-dir /chosen/backups
```

Equivalent environment inputs are `FIELDLAB_HOME`, `FIELDLAB_BIN_DIR`,
`FIELDLAB_SKILLS_DIR`, and `FIELDLAB_BACKUP_DIR`. Command-line values win.

Use `--cli-only` to install the app and launcher while leaving the controller
discovery directory untouched. A full `doctor` will correctly report missing or
mismatched controllers until they are installed separately.

## Recognized upgrade

```bash
python3 scripts/install.py --replace
```

Preflight completes before mutation. Replacement is allowed only when:

- the application contains the Field Lab ownership marker;
- the launcher points to that application's `launcher.py`; and
- each controller matches current source, its prior installation receipt, or
  the known v0.1 controller identity.

Unknown collisions fail closed. A replacement first copies every existing
target to one recoverable backup. Staged targets then replace existing targets
atomically within their parent filesystems. If a later target fails, already
replaced targets are rolled back before the installer exits.

The successful command prints the exact backup path. Keep that directory until
the new `doctor` result and ordinary Codex discovery are accepted.

## Roll back an upgrade

1. Stop using the new launcher.
2. Read `<backup>/backup-manifest.json` and confirm every `source`/`backup`
   mapping.
3. Move each current Field Lab-owned target to a separate quarantine directory;
   do not overwrite it.
4. Move the exact backed-up app, launcher, and controller directories back to
   the recorded source paths.
5. Run the restored launcher with `doctor --json`.

Do not restore only the app while leaving controllers from another version.
The backup is a coherent pre-upgrade set.

## Clean uninstall

There is deliberately no broad recursive uninstall command.

1. Run `fieldlab doctor --json` and record the app, launcher, discovery path,
   controller digests, and latest backup.
2. Confirm the app has `.skill-field-lab-install`, the launcher references that
   app, and both controller `matches_source` values are true.
3. Create one new quarantine directory outside the install targets.
4. Move these four exact targets into it: the app directory, launcher,
   `pattern-intake`, and `skill-eval`.
5. Start a fresh Codex task and confirm the controllers are no longer
   discovered.
6. Delete the quarantine only after that acceptance, or restore by moving the
   four exact targets back.

Never remove the whole Codex Skill directory, `~/.local/share`, or
`~/.local/bin`. Field Lab owns only the exact targets listed above.

## Boundary report

Installation changes local app, launcher, and Skill discovery bytes. It does
not modify a subject repository, activate a target run, commit or push Git,
publish a release, or prove owner acceptance.

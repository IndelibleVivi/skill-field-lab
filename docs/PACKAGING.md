# Packaging direction

V0.1 is published as a standalone GitHub source repository and release archive
for local authoring and dogfood:

- the source tree runs directly with `python -m fieldlab`; `scripts/install_cli.py` provides a build-backend-free local launcher;
- `pyproject.toml` remains future packaging metadata rather than a required local install path;
- the two controller skills can be copied into the user's local skill directory;
- subject packs stay in their own repositories.

For a future Codex marketplace-style distribution, package `pattern-intake`
and `skill-eval` as a plugin rather than treating the local copy script as the
final distribution surface. Keep the Python CLI independently installable so
users can inspect and plan without installing subject packs. Do not add a
plugin manifest until its current contract has been checked against the
intended distribution surface.

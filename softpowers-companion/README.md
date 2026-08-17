# Softpowers companion

This directory is a copy-into-project overlay, not a runnable subject by itself.

Copy `fieldlab-pack.copy-into-softpowers-root.json` to the Softpowers repository root as `fieldlab-pack.json`. In that location, the manifest's `skills` source resolves to the real generated Softpowers skill tree. Copy or compare the bundled cases against the current `evals/cases/` tree.

Do not run the manifest from inside this bundle: there is intentionally no fake Softpowers skill tree here that could be mistaken for the real subject.

For controlled baseline/candidate work, use `fieldlab-pack.matched.copy-into-softpowers-root.json` after creating `.fieldlab-subjects/baseline-skills` with `fieldlab snapshot-git`.

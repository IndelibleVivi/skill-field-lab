# Changelog

## Unreleased

- Sealed the worker-final changed-file set, diff, and tree digest before any
  verifier command runs. Workspace assertions now read the sealed worker tree
  and every command assertion starts from its own fresh copy of that tree, so a
  verifier repair cannot satisfy the worker-completion claim and no command
  inherits another command's edit. Verifier-derived changes are attributed in
  `verification.json` and `verifier-diff-<index>.patch`, and diff sealing now
  uses a disposable Git index so the workspace index and cached diff are never
  mutated.
- Replaced whole-workspace retention with declared, bounded review material. A
  case may declare `human_review_material` exact workspace-relative files that
  are copied atomically into attempt-owned `review-material/` with a manifest
  whose digest and status bind into `verification.json` and the receipt;
  missing, symlinked, non-regular, escaping, or over-limit material fails
  closed with no partial set. Cases with review requirements but no declared
  material rely on the standard attempt artifacts, and `keep_workspace` remains
  the only whole-workspace switch. The interim `reclaim` lifecycle is removed.
  A capture failure after a quiescent worker is recorded as a distinct
  `evidence-failed` attempt/run state with a bounded reason instead of
  `termination-failed`; process cleanup failures keep the termination path.
- Reject a FIFO or other non-regular requirement-outcome file by opening it
  non-blocking before the regular-file check, so a special file cannot stall
  the review command before the controlled configuration error is raised.
- Hardened requirement-outcome file reading: invalid UTF-8, wrong root type,
  non-string or unrecognized values, duplicate keys, oversized files, symlinked
  files, and user-controlled symlinked ancestors all fail as controlled
  configuration errors before any review record is written, while ordinary
  absolute paths with a system symlink ancestor still work.
- Added the read-only `fieldlab explain <manifest> --claim <id>` command, which
  recomputes one claim's supported/unsupported/inconclusive evidence from
  claims, immutable receipts, and separate reviews. It adds `mixed` for
  disagreeing bound reviews instead of latest-wins, deduplicates the same
  receipt across canonical locations by raw digest, labels receipts without the
  worker-final boundary marker `legacy-ambiguous`, binds review digests to the
  exact bytes validated, reports pending, failed, or conflicting requirements
  and missing or digest-drifted artifacts, and names the smallest next evidence
  gap without invoking a target model.
- Documented the exact-tree subject identity versus a subject-owned declared
  payload distinction, and added a dated 2026-09-17/18 Repo Truth Audit v0.2.0
  forward-evidence section without rewriting the 2026-08-30 history.
- Added exact per-requirement JSON input to the public `fieldlab review` command,
  with bounded-file, duplicate-key, receipt-key, and outcome-value validation;
  reviews remain separate from immutable receipts and start no target model.
- Added paired English and Simplified Chinese Mermaid architecture maps that
  make the live-spend gate, worker context ceiling, evidence authority,
  installation proof ceiling, and sole subject-write path explicit.

## 0.2.0 — 2026-08-30

- Reframed Field Lab as one local maintainer workbench with Level 0 intake,
  Level 1 external labs, and explicit Level 2 evidence promotion.
- Made schema-v2 `fieldlab.json` the only active runtime contract; v1 is now an
  explicit one-shot migration input with case rewriting and a migration receipt.
- Added local-path, local-Git-ref, snapshot, and isolated-control subjects,
  matched control plans, subject/source drift rejection, and a registry seam for
  the single `codex-exec` adapter.
- Corrected candidate/claim/decision authority, added claim-only observed
  evidence, final-response and bounded JSON verification, immutable execution
  receipts, and separate digest-bound human reviews.
- Added `doctor`, `init`, canonical `selftest`, `observe`, `review`, `promote`,
  and `migrate-v1`; removed `selftest-pack`, `import-observed`, ambient
  environment-smoke, and the v1 runner path.
- Replaced independent CLI/Skill copy scripts with one transactional installer
  supporting recognized upgrades, recoverable backups, rollback, `--cli-only`,
  and installed source/controller verification.
- Renamed the explicit-only `skill-eval` display surface to **Field Trial** and
  taught Pattern Intake to finish successfully with no lab or local change.
- Added v2 demo and final-response-only legal-research labs; removed the
  top-level Softpowers functional copy in favor of source-backed case studies.
- Preserved the process containment kernel and expanded fake-adapter, drift,
  installer, migration, review, and final-response regressions.
- Closed release acceptance with one owner-authorized, one-invocation
  Repository Operational Truth Audit `source-artifact-split` canary plus a
  separate digest-bound human ceiling review. The receipt supports only the
  pinned synthetic fixture claim; it does not establish installed/runtime or
  arbitrary-repository behavior.

## 0.1.0 — 2026-08-17

- Split external pattern intake from executable skill evaluation.
- Added controller–worker separation and subject-pack contracts.
- Added no-spend planning, exact input/executable-digest pinning, explicit live/cap gate, and observed-dogfood import.
- Added a POSIX Codex adapter with process-group quiescence for success, timeout, interrupt, orphan-descendant, and command-assertion paths.
- Bound comparison-capable plans to explicit requested model and reasoning effort.
- Added content-light receipts, evidence dimensions, and fixture/overlay symlink escape rejection.
- Added Softpowers companion cases plus a non-DevOps legal-research example.
- Added known-fail/known-pass pack selftests, fake-Codex, plan-input drift, resume-drift, local-installer, companion-materialization, and real descendant regressions.
- Increased the real-descendant timeout regression's startup and late-write
  margins so scheduler contention cannot turn a cleanup assertion into an
  empty-trace parsing error; process-group quiescence checks remain unchanged.
- Established layered licensing: SUL-1.0 for functional material and CC
  BY-NC-SA 4.0 for documentation.

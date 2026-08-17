# Codex handoff

Implement or review this bundle as an independent repository. Do not modify the connected Softpowers repository unless Faye explicitly asks for that write.

Priority order:

1. Run the deterministic unit suite.
2. Fix runner defects found by tests without weakening the spend boundary.
3. Confirm process-group cleanup on macOS and Linux.
4. Review current Codex CLI flags against official documentation.
5. Validate the Softpowers companion after copying it into a clean Softpowers worktree.
6. Perform no live model invocation without an explicit plan, `--live`, and a stated cap.

Non-goals: cloud dashboard, leaderboard, automatic LLM judge, background monitor, scheduled evals, all-provider abstraction, or public release.

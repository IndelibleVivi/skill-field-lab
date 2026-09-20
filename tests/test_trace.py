from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from fieldlab.trace import parse_trace
from fieldlab.verify import evaluate_trace_assertions


class TraceTests(unittest.TestCase):
    def test_echo_is_only_a_mention_and_old_assertion_is_an_alias(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "trace.jsonl"
            path.write_text(json.dumps({
                "type": "item.completed",
                "item": {"id": "echo", "type": "command_execution",
                         "command": "echo references/worktree.md"},
            }) + "\n")
            summary = parse_trace(path)
        self.assertEqual(summary["command_reference_mentions"], ["worktree.md"])
        self.assertNotIn("reference_reads", summary)
        results = evaluate_trace_assertions({"trace_assertions": {
            "reference_reads_include": ["worktree.md"],
            "command_reference_mentions_include": ["worktree.md", "missing.md"],
        }}, summary)
        mentions = [row for row in results if row["type"] == "command_reference_mentions_include"]
        self.assertEqual(len(mentions), 2)
        self.assertEqual([row["passed"] for row in mentions], [True, False])

    def test_context_injection_does_not_manufacture_a_command_mention(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "trace.jsonl"
            path.write_text(json.dumps({
                "type": "item.completed",
                "item": {"id": "message", "type": "agent_message",
                         "text": "Host supplied .agents/skills/worktree/SKILL.md and references/worktree.md."},
            }) + "\n")
            summary = parse_trace(path)
        self.assertEqual(summary["command_reference_mentions"], [])
        self.assertNotIn("host_selection", summary)

    def test_unknown_and_malformed_events_are_preserved_as_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "trace.jsonl"
            path.write_text(
                "\n".join(
                    [
                        json.dumps({"type": "thread.started", "thread_id": "t"}),
                        json.dumps(
                            {
                                "type": "item.completed",
                                "item": {
                                    "id": "c",
                                    "type": "command_execution",
                                    "command": "cat .agents/skills/x/references/spec-chain.md",
                                },
                            }
                        ),
                        json.dumps(
                            {
                                "type": "item.completed",
                                "item": {"id": "m", "type": "agent_message", "text": "done"},
                            }
                        ),
                        json.dumps({"type": "future.event", "payload": {"kept": True}}),
                        json.dumps({"type": "turn.completed", "usage": {"input_tokens": 1}}),
                        "{malformed",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            summary = parse_trace(path)
        self.assertEqual(summary["final_message"], "done")
        self.assertEqual(summary["command_reference_mentions"], ["spec-chain.md"])
        self.assertEqual(summary["unknown_event_types"], ["future.event"])
        self.assertEqual(summary["malformed_lines"], 1)
        self.assertTrue(summary["turn_completed"])


if __name__ == "__main__":
    unittest.main()

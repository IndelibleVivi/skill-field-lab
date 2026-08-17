from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from fieldlab.trace import parse_trace


class TraceTests(unittest.TestCase):
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
        self.assertEqual(summary["reference_reads"], ["spec-chain.md"])
        self.assertEqual(summary["unknown_event_types"], ["future.event"])
        self.assertEqual(summary["malformed_lines"], 1)
        self.assertTrue(summary["turn_completed"])


if __name__ == "__main__":
    unittest.main()

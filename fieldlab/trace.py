from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

REFERENCE_RE = re.compile(r"references[/\\]([A-Za-z0-9._-]+\.md)")


def parse_trace(trace_path: Path) -> dict[str, Any]:
    event_types: dict[str, int] = {}
    item_types: dict[str, int] = {}
    unknown_event_types: set[str] = set()
    unknown_item_types: set[str] = set()
    command_ids: set[str] = set()
    plan_ids: set[str] = set()
    subagent_ids: set[str] = set()
    command_texts: list[str] = []
    reference_reads: set[str] = set()
    final_messages: list[str] = []
    errors: list[str] = []
    malformed_lines = 0
    thread_started = False
    turn_completed = False
    usage: dict[str, Any] | None = None
    known_item_types = {
        "agent_message",
        "reasoning",
        "command_execution",
        "file_change",
        "mcp_tool_call",
        "web_search",
        "todo_list",
        "error",
    }

    if not trace_path.is_file():
        return {
            "event_types": {},
            "item_types": {},
            "unknown_event_types": [],
            "unknown_item_types": [],
            "command_executions": 0,
            "commands": [],
            "plan_updates": 0,
            "subagent_events": 0,
            "reference_reads": [],
            "final_message": "",
            "usage": None,
            "errors": ["trace file missing"],
            "malformed_lines": 0,
            "thread_started": False,
            "turn_completed": False,
        }

    for line_number, raw_line in enumerate(trace_path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        try:
            event = json.loads(raw_line)
        except json.JSONDecodeError:
            malformed_lines += 1
            continue
        if not isinstance(event, dict):
            malformed_lines += 1
            continue
        event_type = str(event.get("type", "<missing>"))
        event_types[event_type] = event_types.get(event_type, 0) + 1
        if not (
            event_type.startswith("thread.")
            or event_type.startswith("turn.")
            or event_type.startswith("item.")
            or event_type == "error"
        ):
            unknown_event_types.add(event_type)
        if event_type == "thread.started":
            thread_started = True
        if event_type == "turn.completed":
            turn_completed = True
            if isinstance(event.get("usage"), dict):
                usage = dict(event["usage"])
        if event_type in {"turn.failed", "error"}:
            errors.append(json.dumps(event, ensure_ascii=False))

        item = event.get("item")
        if not isinstance(item, dict):
            continue
        item_type = str(item.get("type", "<missing>"))
        item_types[item_type] = item_types.get(item_type, 0) + 1
        if item_type not in known_item_types and not any(marker in item_type for marker in ("plan", "agent", "collab")):
            unknown_item_types.add(item_type)
        item_id = str(item.get("id", f"line-{line_number}"))

        if item_type == "command_execution":
            command_ids.add(item_id)
            command = item.get("command")
            if isinstance(command, str) and command not in command_texts:
                command_texts.append(command)
                reference_reads.update(REFERENCE_RE.findall(command))
        if "plan" in item_type or item_type == "todo_list":
            plan_ids.add(item_id)
        if any(marker in item_type for marker in ("subagent", "collab")):
            subagent_ids.add(item_id)
        if item_type == "mcp_tool_call":
            name = " ".join(str(item.get(key, "")) for key in ("server", "tool", "name")).lower()
            if any(marker in name for marker in ("spawn_agent", "subagent", "collaboration")):
                subagent_ids.add(item_id)
        if event_type == "item.completed" and item_type == "agent_message":
            text = item.get("text")
            if isinstance(text, str):
                final_messages.append(text)

    return {
        "event_types": dict(sorted(event_types.items())),
        "item_types": dict(sorted(item_types.items())),
        "unknown_event_types": sorted(unknown_event_types),
        "unknown_item_types": sorted(unknown_item_types),
        "command_executions": len(command_ids),
        "commands": command_texts,
        "plan_updates": len(plan_ids),
        "subagent_events": len(subagent_ids),
        "reference_reads": sorted(reference_reads),
        "final_message": final_messages[-1] if final_messages else "",
        "usage": usage,
        "errors": errors,
        "malformed_lines": malformed_lines,
        "thread_started": thread_started,
        "turn_completed": turn_completed,
    }

from __future__ import annotations

from app.codex_runner import _event_is_denied
from app.providers.codex_cli import PHASES, phase_schema


def test_codex_adapter_defines_all_eleven_contract_phases() -> None:
    assert len(PHASES) == 11
    assert len(set(PHASES)) == 11
    for phase in PHASES:
        schema = phase_schema(phase)
        assert schema["properties"]["phase"]["const"] == phase
        assert schema["additionalProperties"] is False


def test_codex_runner_rejects_tool_command_mcp_web_and_file_events() -> None:
    for event_type in ("command_execution", "tool_call", "mcp_call", "web_search", "file_change"):
        assert _event_is_denied({"type": "item.started", "item": {"type": event_type}})
    assert not _event_is_denied({"type": "item.completed", "item": {"type": "agent_message"}})

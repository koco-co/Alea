from __future__ import annotations

import os
from pathlib import Path

import pytest

from app.providers.cli import BUSINESS_METHODS, CliProvider, phase_schema
from app.providers.cli_catalog import CLI_RUNTIME_CATALOG, get_cli_runtime
from app.providers.cli_executor import (
    _event_is_denied,
    probe_cli_runtime,
    validate_cli_path,
)
from app.providers.contract import ProviderFailure


def _write_executable(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")
    path.chmod(path.stat().st_mode | 0o111)


def test_cli_catalog_is_unique_and_exposes_required_baseline() -> None:
    keys = [definition.key for definition in CLI_RUNTIME_CATALOG]
    assert len(keys) == len(set(keys))
    assert {
        "codex",
        "claude",
        "gemini",
        "copilot",
        "cursor",
        "opencode",
        "hermes",
        "kimi",
        "qwen",
        "aider",
        "amp",
    }.issubset(keys)


def test_cli_provider_defines_all_eleven_contract_phases() -> None:
    assert len(BUSINESS_METHODS) == 11
    assert len(set(BUSINESS_METHODS)) == 11
    for definition in CLI_RUNTIME_CATALOG:
        provider = CliProvider(runtime_key=definition.key, executable_path="/not-invoked")
        for phase in BUSINESS_METHODS:
            assert callable(getattr(provider, phase))
            schema = phase_schema(phase)
            assert schema["properties"]["phase"]["const"] == phase
            assert schema["additionalProperties"] is False


def test_cli_event_guard_rejects_tool_command_mcp_web_and_file_events() -> None:
    for event_type in (
        "command_execution",
        "tool_call",
        "mcp_call",
        "web_search",
        "file_change",
    ):
        assert _event_is_denied({"type": "item.started", "item": {"type": event_type}})
    assert not _event_is_denied({"type": "item.completed", "item": {"type": "agent_message"}})


def test_cli_path_requires_absolute_matching_executable(tmp_path: Path) -> None:
    executable = tmp_path / "codex"
    _write_executable(executable, "#!/bin/sh\nexit 0\n")
    assert validate_cli_path("codex", str(executable)) == executable.resolve()

    with pytest.raises(ProviderFailure) as relative_error:
        validate_cli_path("codex", "codex")
    assert relative_error.value.code == "cli_path_not_absolute"

    mismatched = tmp_path / "claude"
    _write_executable(mismatched, "#!/bin/sh\nexit 0\n")
    with pytest.raises(ProviderFailure) as mismatch_error:
        validate_cli_path("codex", str(mismatched))
    assert mismatch_error.value.code == "cli_path_runtime_mismatch"

    non_executable = tmp_path / "not-executable" / "codex"
    non_executable.parent.mkdir()
    non_executable.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    non_executable.chmod(0o600)
    with pytest.raises(ProviderFailure) as permission_error:
        validate_cli_path("codex", str(non_executable))
    assert permission_error.value.code == "cli_path_not_executable"


@pytest.mark.asyncio
async def test_cli_probe_reports_version_auth_and_models(tmp_path: Path) -> None:
    executable = tmp_path / "codex"
    _write_executable(
        executable,
        """#!/bin/sh
if [ "$1" = "--version" ]; then
  echo "codex-cli 1.2.3"
elif [ "$1" = "login" ] && [ "$2" = "status" ]; then
  echo "Logged in using ChatGPT"
elif [ "$1" = "debug" ] && [ "$2" = "models" ]; then
  echo '{"models":[{"slug":"gpt-test","display_name":"GPT Test"}]}'
else
  exit 2
fi
""",
    )
    result = await probe_cli_runtime("codex", str(executable))
    assert result.status == "passed"
    assert result.version == "codex-cli 1.2.3"
    assert result.auth_status == "authenticated"
    assert result.models == ("default", "gpt-test")
    assert result.error_code is None


@pytest.mark.asyncio
async def test_cli_probe_masks_failure_details(tmp_path: Path) -> None:
    executable = tmp_path / "codex"
    _write_executable(
        executable,
        "#!/bin/sh\necho 'secret diagnostic' >&2\nexit 9\n",
    )
    result = await probe_cli_runtime("codex", str(executable))
    assert result.status == "failed"
    assert result.error_code == "cli_probe_failed"
    assert "secret" not in repr(result)


def test_cli_catalog_rejects_unknown_runtime() -> None:
    with pytest.raises(ValueError, match="unsupported_cli_runtime"):
        get_cli_runtime("shell")


def test_cli_path_uses_os_executable_permission(tmp_path: Path) -> None:
    executable = tmp_path / "codex"
    _write_executable(executable, "#!/bin/sh\nexit 0\n")
    assert os.access(validate_cli_path("codex", str(executable)), os.X_OK)

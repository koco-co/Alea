from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Literal


ModelParser = Literal["codex_json", "line_separated"]
StreamFormat = Literal[
    "codex_jsonl",
    "claude_stream_json",
    "json_event_stream",
    "copilot_stream_json",
    "acp_json_rpc",
    "single_json",
    "plain",
]


@dataclass(frozen=True, slots=True)
class CliRuntimeDefinition:
    key: str
    display_name: str
    binary_names: tuple[str, ...]
    version_args: tuple[str, ...]
    auth_probe_args: tuple[str, ...] | None
    model_probe_args: tuple[str, ...] | None
    model_parser: ModelParser | None
    fallback_models: tuple[str, ...]
    stream_format: StreamFormat
    prompt_via_stdin: bool
    supports_custom_model: bool = True
    supports_reasoning: bool = False
    roundtable_capable: bool = False


# This is a declarative runtime catalog. The generic executor owns validation,
# probing and process lifecycle; adding a CLI does not change business models.
CLI_RUNTIME_CATALOG: Final[tuple[CliRuntimeDefinition, ...]] = (
    CliRuntimeDefinition(
        key="codex",
        display_name="Codex CLI",
        binary_names=("codex",),
        version_args=("--version",),
        auth_probe_args=("login", "status"),
        model_probe_args=("debug", "models"),
        model_parser="codex_json",
        fallback_models=("gpt-5.6-sol", "gpt-5.5", "gpt-5.4", "gpt-5.4-mini", "o3"),
        stream_format="codex_jsonl",
        prompt_via_stdin=True,
        supports_reasoning=True,
        roundtable_capable=True,
    ),
    CliRuntimeDefinition(
        key="claude",
        display_name="Claude Code",
        binary_names=("claude", "openclaude"),
        version_args=("--version",),
        auth_probe_args=("auth", "status"),
        model_probe_args=None,
        model_parser=None,
        fallback_models=("default", "sonnet", "opus", "haiku"),
        stream_format="claude_stream_json",
        prompt_via_stdin=True,
        supports_reasoning=True,
    ),
    CliRuntimeDefinition(
        key="gemini",
        display_name="Gemini CLI",
        binary_names=("gemini",),
        version_args=("--version",),
        auth_probe_args=None,
        model_probe_args=None,
        model_parser=None,
        fallback_models=("auto", "gemini-3-pro-preview", "gemini-3-flash-preview"),
        stream_format="single_json",
        prompt_via_stdin=True,
        supports_reasoning=True,
    ),
    CliRuntimeDefinition(
        key="copilot",
        display_name="GitHub Copilot CLI",
        binary_names=("copilot",),
        version_args=("--version",),
        auth_probe_args=None,
        model_probe_args=None,
        model_parser=None,
        fallback_models=("default", "claude-sonnet-4.6", "gpt-5.2"),
        stream_format="copilot_stream_json",
        prompt_via_stdin=True,
    ),
    CliRuntimeDefinition(
        key="cursor",
        display_name="Cursor Agent",
        binary_names=("cursor-agent",),
        version_args=("--version",),
        auth_probe_args=("status",),
        model_probe_args=("models",),
        model_parser="line_separated",
        fallback_models=("auto", "sonnet-4", "sonnet-4-thinking", "gpt-5"),
        stream_format="json_event_stream",
        prompt_via_stdin=True,
        supports_reasoning=True,
    ),
    CliRuntimeDefinition(
        key="opencode",
        display_name="OpenCode",
        binary_names=("opencode-cli", "opencode"),
        version_args=("--version",),
        auth_probe_args=None,
        model_probe_args=("models",),
        model_parser="line_separated",
        fallback_models=(
            "default",
            "anthropic/claude-sonnet-4-5",
            "openai/gpt-5",
            "google/gemini-2.5-pro",
        ),
        stream_format="json_event_stream",
        prompt_via_stdin=True,
    ),
    CliRuntimeDefinition(
        key="hermes",
        display_name="Hermes",
        binary_names=("hermes",),
        version_args=("--version",),
        auth_probe_args=None,
        model_probe_args=None,
        model_parser=None,
        fallback_models=("default", "grok-4.3", "openai-codex:gpt-5.4"),
        stream_format="acp_json_rpc",
        prompt_via_stdin=True,
        supports_reasoning=True,
    ),
    CliRuntimeDefinition(
        key="kimi",
        display_name="Kimi CLI",
        binary_names=("kimi",),
        version_args=("--version",),
        auth_probe_args=None,
        model_probe_args=None,
        model_parser=None,
        fallback_models=("default", "kimi-k2-turbo-preview", "moonshot-v1-32k"),
        stream_format="acp_json_rpc",
        prompt_via_stdin=True,
        supports_reasoning=True,
    ),
    CliRuntimeDefinition(
        key="qwen",
        display_name="Qwen Code",
        binary_names=("qwen",),
        version_args=("--version",),
        auth_probe_args=None,
        model_probe_args=None,
        model_parser=None,
        fallback_models=("default", "qwen3-coder-plus", "qwen3-coder-flash"),
        stream_format="plain",
        prompt_via_stdin=True,
    ),
    CliRuntimeDefinition(
        key="aider",
        display_name="Aider",
        binary_names=("aider",),
        version_args=("--version",),
        auth_probe_args=None,
        model_probe_args=None,
        model_parser=None,
        fallback_models=(
            "default",
            "sonnet",
            "gpt-4o",
            "deepseek/deepseek-chat",
            "gemini/gemini-2.0-flash",
        ),
        stream_format="plain",
        prompt_via_stdin=False,
    ),
    CliRuntimeDefinition(
        key="amp",
        display_name="Amp",
        binary_names=("amp",),
        version_args=("--version",),
        auth_probe_args=None,
        model_probe_args=None,
        model_parser=None,
        fallback_models=("default", "smart", "deep", "rush"),
        stream_format="claude_stream_json",
        prompt_via_stdin=True,
        supports_custom_model=False,
    ),
)

_CLI_BY_KEY: Final = {definition.key: definition for definition in CLI_RUNTIME_CATALOG}


def get_cli_runtime(runtime_key: str) -> CliRuntimeDefinition:
    try:
        return _CLI_BY_KEY[runtime_key]
    except KeyError as exc:
        raise ValueError("unsupported_cli_runtime") from exc


def cli_catalog_payload() -> list[dict[str, object]]:
    return [
        {
            "key": definition.key,
            "display_name": definition.display_name,
            "binary_names": list(definition.binary_names),
            "fallback_models": list(definition.fallback_models),
            "stream_format": definition.stream_format,
            "supports_custom_model": definition.supports_custom_model,
            "supports_reasoning": definition.supports_reasoning,
            "roundtable_capable": definition.roundtable_capable,
        }
        for definition in CLI_RUNTIME_CATALOG
    ]

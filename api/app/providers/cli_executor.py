from __future__ import annotations

import asyncio
import json
import os
import re
import signal
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final
from uuid import uuid4

from jsonschema import ValidationError, validate

from app.providers.cli_catalog import CliRuntimeDefinition, get_cli_runtime
from app.providers.contract import ProviderFailure, Usage


MODEL_ID: Final = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")
DENIED_EVENT_FRAGMENTS: Final = ("command", "tool", "mcp", "web_search", "file_change")
SAFE_ENV_NAMES: Final = (
    "PATH",
    "CODEX_HOME",
    "LANG",
    "LC_ALL",
    "SSL_CERT_FILE",
    "SSL_CERT_DIR",
    "ALL_PROXY",
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "NO_PROXY",
    "all_proxy",
    "http_proxy",
    "https_proxy",
    "no_proxy",
)
MAX_PROBE_OUTPUT_BYTES: Final = 1_000_000


@dataclass(frozen=True, slots=True)
class CliProbeResult:
    runtime_key: str
    executable_path: str
    version: str | None
    auth_status: str
    models: tuple[str, ...]
    status: str
    error_code: str | None = None


@dataclass(frozen=True, slots=True)
class CliExecutionResult:
    execution_id: str
    output: dict[str, Any]
    usage: Usage
    latency_ms: int


def validate_cli_path(runtime_key: str, executable_path: str) -> Path:
    definition = get_cli_runtime(runtime_key)
    candidate = Path(executable_path)
    if not candidate.is_absolute():
        raise ProviderFailure(
            "cli_path_not_absolute", "CLI executable path must be absolute", retryable=False
        )
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise ProviderFailure(
            "cli_path_not_found", "CLI executable does not exist", retryable=False
        ) from exc
    if not resolved.is_file():
        raise ProviderFailure(
            "cli_path_not_file", "CLI executable path is not a file", retryable=False
        )
    if not os.access(resolved, os.X_OK):
        raise ProviderFailure(
            "cli_path_not_executable", "CLI executable is not executable", retryable=False
        )
    if (
        candidate.name not in definition.binary_names
        and resolved.name not in definition.binary_names
    ):
        raise ProviderFailure(
            "cli_path_runtime_mismatch",
            "CLI executable does not match the selected runtime",
            retryable=False,
        )
    return resolved


async def probe_cli_runtime(
    runtime_key: str,
    executable_path: str,
    *,
    timeout_seconds: int = 15,
) -> CliProbeResult:
    definition = get_cli_runtime(runtime_key)
    try:
        executable = validate_cli_path(runtime_key, executable_path)
        version_output = await _run_probe(
            executable, definition.version_args, timeout_seconds=timeout_seconds
        )
        auth_status = await _probe_auth(executable, definition, timeout_seconds=timeout_seconds)
        models = await _probe_models(executable, definition, timeout_seconds=timeout_seconds)
    except ProviderFailure as exc:
        return CliProbeResult(
            runtime_key=runtime_key,
            executable_path=executable_path,
            version=None,
            auth_status="error",
            models=(),
            status="failed",
            error_code=exc.code,
        )
    return CliProbeResult(
        runtime_key=runtime_key,
        executable_path=str(executable),
        version=_first_nonempty_line(version_output),
        auth_status=auth_status,
        models=models,
        status="passed" if auth_status != "unauthenticated" else "failed",
        error_code=None if auth_status != "unauthenticated" else "cli_not_authenticated",
    )


async def execute_cli_phase(
    *,
    runtime_key: str,
    executable_path: str,
    model_id: str,
    prompt: str,
    output_schema: dict[str, Any],
    timeout_seconds: int,
) -> CliExecutionResult:
    definition = get_cli_runtime(runtime_key)
    if not definition.roundtable_capable:
        raise ProviderFailure(
            "cli_runtime_not_roundtable_capable",
            "CLI runtime has not passed Alea structured-output qualification",
            retryable=False,
        )
    if runtime_key != "codex":
        raise ProviderFailure(
            "cli_runtime_not_implemented",
            "CLI runtime invocation is not implemented",
            retryable=False,
        )
    executable = validate_cli_path(runtime_key, executable_path)
    if not MODEL_ID.fullmatch(model_id) or model_id.startswith("-"):
        raise ProviderFailure("invalid_model_id", "CLI model id is invalid", retryable=False)
    return await _execute_codex(
        executable=executable,
        model_id=model_id,
        prompt=prompt,
        output_schema=output_schema,
        timeout_seconds=timeout_seconds,
    )


async def _execute_codex(
    *,
    executable: Path,
    model_id: str,
    prompt: str,
    output_schema: dict[str, Any],
    timeout_seconds: int,
) -> CliExecutionResult:
    started = time.monotonic()
    execution_id = str(uuid4())
    with tempfile.TemporaryDirectory(prefix="alea-cli-codex-") as directory:
        root = Path(directory)
        schema_path = root / "output.schema.json"
        output_path = root / "output.json"
        schema_path.write_text(json.dumps(output_schema), encoding="utf-8")
        command = [
            str(executable),
            "exec",
            "--json",
            "--output-schema",
            str(schema_path),
            "--output-last-message",
            str(output_path),
            "--ephemeral",
            "--ignore-user-config",
            "--ignore-rules",
            "--disable",
            "plugins",
            "--sandbox",
            "read-only",
            "--skip-git-repo-check",
            "--cd",
            str(root),
            "--model",
            model_id,
        ]
        process = await asyncio.create_subprocess_exec(
            *command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=_safe_codex_environment(directory),
            start_new_session=True,
        )
        stdout, _stderr = await _communicate(
            process, prompt.encode(), timeout_seconds=timeout_seconds, timeout_code="cli_timeout"
        )
        if process.returncode != 0:
            raise ProviderFailure("cli_execution_failed", "CLI execution failed", retryable=True)
        usage = _parse_codex_events(stdout)
        try:
            output = json.loads(output_path.read_text(encoding="utf-8"))
            validate(instance=output, schema=output_schema)
        except (OSError, json.JSONDecodeError, ValidationError) as exc:
            raise ProviderFailure(
                "cli_schema_validation_failed",
                "CLI output failed schema validation",
                retryable=False,
            ) from exc
        if not isinstance(output, dict):
            raise ProviderFailure(
                "cli_schema_validation_failed",
                "CLI output root must be an object",
                retryable=False,
            )
    return CliExecutionResult(
        execution_id=execution_id,
        output=output,
        usage=usage,
        latency_ms=max(0, int((time.monotonic() - started) * 1000)),
    )


async def _run_probe(
    executable: Path,
    args: tuple[str, ...],
    *,
    timeout_seconds: int,
) -> str:
    with tempfile.TemporaryDirectory(prefix="alea-cli-probe-") as directory:
        process = await asyncio.create_subprocess_exec(
            str(executable),
            *args,
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=directory,
            env=_probe_environment(),
            start_new_session=True,
        )
        stdout, _stderr = await _communicate(
            process,
            None,
            timeout_seconds=timeout_seconds,
            timeout_code="cli_probe_timeout",
        )
    if process.returncode != 0:
        raise ProviderFailure("cli_probe_failed", "CLI probe failed", retryable=True)
    if len(stdout) > MAX_PROBE_OUTPUT_BYTES:
        raise ProviderFailure(
            "cli_probe_output_too_large", "CLI probe output is too large", retryable=False
        )
    return stdout.decode("utf-8", errors="replace").strip()


async def _probe_auth(
    executable: Path,
    definition: CliRuntimeDefinition,
    *,
    timeout_seconds: int,
) -> str:
    if definition.auth_probe_args is None:
        return "unknown"
    try:
        output = await _run_probe(
            executable, definition.auth_probe_args, timeout_seconds=timeout_seconds
        )
    except ProviderFailure:
        return "unauthenticated"
    normalized = output.casefold()
    if any(marker in normalized for marker in ("not logged", "unauth", "login required")):
        return "unauthenticated"
    return "authenticated"


async def _probe_models(
    executable: Path,
    definition: CliRuntimeDefinition,
    *,
    timeout_seconds: int,
) -> tuple[str, ...]:
    fallback = definition.fallback_models
    if definition.model_probe_args is None or definition.model_parser is None:
        return fallback
    try:
        output = await _run_probe(
            executable, definition.model_probe_args, timeout_seconds=timeout_seconds
        )
        if definition.model_parser == "codex_json":
            models = _parse_codex_models(output)
        else:
            models = _parse_line_models(output)
    except ProviderFailure:
        return fallback
    return models or fallback


async def _communicate(
    process: asyncio.subprocess.Process,
    input_bytes: bytes | None,
    *,
    timeout_seconds: int,
    timeout_code: str,
) -> tuple[bytes, bytes]:
    try:
        return await asyncio.wait_for(
            process.communicate(input_bytes),
            timeout=timeout_seconds,
        )
    except TimeoutError as exc:
        _kill_process_group(process)
        await process.wait()
        raise ProviderFailure(timeout_code, "CLI process timed out", retryable=True) from exc
    except asyncio.CancelledError:
        _kill_process_group(process)
        await process.wait()
        raise


def _kill_process_group(process: asyncio.subprocess.Process) -> None:
    if process.returncode is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        return


def _safe_codex_environment(temporary_home: str) -> dict[str, str]:
    env = {name: value for name in SAFE_ENV_NAMES if (value := os.getenv(name))}
    env["CODEX_HOME"] = os.getenv("CODEX_HOME", str(Path.home() / ".codex"))
    env["HOME"] = temporary_home
    env["TMPDIR"] = temporary_home
    return env


def _probe_environment() -> dict[str, str]:
    allowed = (*SAFE_ENV_NAMES, "HOME", "TMPDIR")
    return {name: value for name in allowed if (value := os.getenv(name))}


def _event_is_denied(event: Any) -> bool:
    if not isinstance(event, dict):
        return False
    candidates = [event.get("type")]
    item = event.get("item")
    if isinstance(item, dict):
        candidates.append(item.get("type"))
    normalized = " ".join(str(item).casefold() for item in candidates if item)
    return any(fragment in normalized for fragment in DENIED_EVENT_FRAGMENTS)


def _parse_codex_events(stdout: bytes) -> Usage:
    usage: dict[str, int | None] = {
        "input_tokens": None,
        "output_tokens": None,
        "total_tokens": None,
    }
    for line in stdout.decode("utf-8", errors="replace").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ProviderFailure(
                "cli_invalid_jsonl", "CLI emitted invalid JSONL", retryable=False
            ) from exc
        if _event_is_denied(event):
            raise ProviderFailure(
                "cli_disallowed_event",
                "CLI attempted a disallowed tool action",
                retryable=False,
            )
        event_usage = event.get("usage") if isinstance(event, dict) else None
        if isinstance(event_usage, dict):
            usage = {
                "input_tokens": _optional_nonnegative_int(event_usage.get("input_tokens")),
                "output_tokens": _optional_nonnegative_int(event_usage.get("output_tokens")),
                "total_tokens": _optional_nonnegative_int(event_usage.get("total_tokens")),
            }
    return Usage.model_validate(usage)


def _parse_codex_models(output: str) -> tuple[str, ...]:
    try:
        body = json.loads(output)
    except json.JSONDecodeError:
        return ()
    if not isinstance(body, dict) or not isinstance(body.get("models"), list):
        return ()
    models: list[str] = ["default"]
    for raw in body["models"]:
        if not isinstance(raw, dict) or raw.get("visibility") == "hidden":
            continue
        identifier = raw.get("slug") or raw.get("id")
        if isinstance(identifier, str) and identifier and identifier not in models:
            models.append(identifier)
    return tuple(models)


def _parse_line_models(output: str) -> tuple[str, ...]:
    models = ["default"]
    for line in output.splitlines():
        value = line.strip().split(maxsplit=1)[0] if line.strip() else ""
        if MODEL_ID.fullmatch(value) and value not in models:
            models.append(value)
    return tuple(models)


def _first_nonempty_line(output: str) -> str | None:
    return next((line.strip() for line in output.splitlines() if line.strip()), None)


def _optional_nonnegative_int(value: Any) -> int | None:
    return value if isinstance(value, int) and value >= 0 else None

from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
import signal
import tempfile
import time
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from fastapi import FastAPI, Header, HTTPException
from jsonschema import ValidationError, validate
from pydantic import BaseModel, ConfigDict, Field


MODEL_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")
DENIED_EVENT_FRAGMENTS = ("command", "tool", "mcp", "web_search", "file_change")
SAFE_ENV_NAMES = (
    "PATH",
    "HOME",
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


class ExecuteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: UUID
    phase: str = Field(min_length=1, max_length=80)
    model: str = Field(min_length=1, max_length=128)
    timeout_seconds: int = Field(ge=1, le=900)
    prompt: str = Field(min_length=1, max_length=100_000)
    output_schema: dict[str, Any]


class ExecuteResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    execution_id: str
    model: str
    output: dict[str, Any]
    usage: dict[str, int | None]
    latency_ms: int


app = FastAPI(title="Alea Codex Runner", version="1")


def _authorize(token: str | None) -> None:
    expected = os.getenv("ALEA_RUNNER_TOKEN")
    if not expected or token != expected:
        raise HTTPException(status_code=401, detail="runner_authentication_failed")


def _safe_environment(home: str) -> dict[str, str]:
    env = {name: value for name in SAFE_ENV_NAMES if (value := os.getenv(name))}
    env["CODEX_HOME"] = os.getenv("CODEX_HOME", str(Path.home() / ".codex"))
    env["HOME"] = home
    env["TMPDIR"] = home
    return env


def _event_is_denied(event: Any) -> bool:
    if not isinstance(event, dict):
        return False
    candidates = [event.get("type")]
    item = event.get("item")
    if isinstance(item, dict):
        candidates.append(item.get("type"))
    normalized = " ".join(str(item).casefold() for item in candidates if item)
    return any(fragment in normalized for fragment in DENIED_EVENT_FRAGMENTS)


@app.get("/health")
async def health() -> dict[str, str | bool]:
    return {
        "service": "alea-codex-runner",
        "status": "ok" if shutil.which("codex") else "unavailable",
        "codex_available": bool(shutil.which("codex")),
    }


@app.get("/models")
async def models(x_alea_runner_token: str | None = Header(default=None)) -> dict[str, Any]:
    _authorize(x_alea_runner_token)
    configured = [
        item.strip() for item in os.getenv("CODEX_MODELS", "gpt-5.6-sol").split(",") if item.strip()
    ]
    return {"runtime_key": "codex", "models": configured, "source": "operator_config"}


@app.post("/internal/v1/execute", response_model=ExecuteResponse)
async def execute(
    request: ExecuteRequest,
    x_alea_runner_token: str | None = Header(default=None),
) -> ExecuteResponse:
    _authorize(x_alea_runner_token)
    if not MODEL_ID.fullmatch(request.model) or request.model.startswith("-"):
        raise HTTPException(status_code=422, detail="invalid_model_id")
    codex = shutil.which("codex")
    if not codex:
        raise HTTPException(status_code=503, detail="codex_not_installed")

    execution_id = str(uuid4())
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="alea-codex-") as directory:
        root = Path(directory)
        schema_path = root / "output.schema.json"
        output_path = root / "output.json"
        schema_path.write_text(json.dumps(request.output_schema), encoding="utf-8")
        command = [
            codex,
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
            request.model,
            "-",
        ]
        process = await asyncio.create_subprocess_exec(
            *command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=_safe_environment(directory),
            start_new_session=True,
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(request.prompt.encode()),
                timeout=request.timeout_seconds,
            )
        except TimeoutError as exc:
            os.killpg(process.pid, signal.SIGKILL)
            await process.wait()
            raise HTTPException(status_code=504, detail="codex_timeout") from exc
        except asyncio.CancelledError:
            os.killpg(process.pid, signal.SIGKILL)
            await process.wait()
            raise

        if process.returncode != 0:
            del stderr
            raise HTTPException(status_code=502, detail="codex_execution_failed")

        usage: dict[str, int | None] = {
            "input_tokens": None,
            "output_tokens": None,
            "total_tokens": None,
        }
        for line in stdout.decode("utf-8", errors="replace").splitlines():
            try:
                event = json.loads(line)
            except json.JSONDecodeError as exc:
                raise HTTPException(status_code=502, detail="codex_invalid_jsonl") from exc
            if _event_is_denied(event):
                raise HTTPException(status_code=502, detail="codex_disallowed_event")
            event_usage = event.get("usage") if isinstance(event, dict) else None
            if isinstance(event_usage, dict):
                usage = {
                    "input_tokens": event_usage.get("input_tokens"),
                    "output_tokens": event_usage.get("output_tokens"),
                    "total_tokens": event_usage.get("total_tokens"),
                }
        try:
            output = json.loads(output_path.read_text(encoding="utf-8"))
            validate(instance=output, schema=request.output_schema)
        except (OSError, json.JSONDecodeError, ValidationError) as exc:
            raise HTTPException(status_code=502, detail="codex_schema_validation_failed") from exc
        if not isinstance(output, dict):
            raise HTTPException(status_code=502, detail="codex_schema_validation_failed")
        return ExecuteResponse(
            execution_id=execution_id,
            model=request.model,
            output=output,
            usage=usage,
            latency_ms=int((time.monotonic() - started) * 1000),
        )

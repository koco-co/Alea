from __future__ import annotations

import asyncio
import os
from enum import StrEnum
from typing import Annotated, Any, Literal, Mapping, Protocol
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, ConfigDict, Field

from app.security import AuthenticatedPrincipal
from app.secrets.envelope import EnvelopeEncryption


router = APIRouter(prefix="/v1/admin", tags=["admin"])


class AdminGatewayError(RuntimeError):
    """A stable administrative command failure safe to map to an API response."""

    def __init__(self, code: str, *, status_code: int = 409) -> None:
        super().__init__(code)
        self.code = code
        self.status_code = status_code


class AdminGateway(Protocol):
    """Database boundary for admin RPCs.

    Every command implementation must perform the domain mutation and append its
    ``admin_audit_logs`` row in the same database transaction.
    """

    async def query(
        self,
        operation: str,
        *,
        actor_id: str,
        params: Mapping[str, Any],
    ) -> Mapping[str, Any]: ...

    async def command(
        self,
        operation: str,
        *,
        actor_id: str,
        request_id: str,
        payload: Mapping[str, Any],
    ) -> Mapping[str, Any]: ...


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class QualitySeverity(StrEnum):
    BLOCK = "block"
    WARNING = "warning"


class PublicationQualityContext(StrictModel):
    quorum_met: bool
    legal_bet: bool
    minutes_to_sales_cutoff: int
    duplicate_active_card: bool
    odds_age_minutes: int = Field(ge=0)
    unsupported_fact_count: int = Field(default=0, ge=0)
    missing_critical_fields: list[str] = Field(default_factory=list)


class PublicationQualityItem(StrictModel):
    code: str
    severity: QualitySeverity
    passed: bool
    message: str


class PublicationQualityReport(StrictModel):
    publishable: bool
    items: list[PublicationQualityItem]


class PublishPredictionRequest(StrictModel):
    confirm_content_lock: bool
    acknowledged_warning_codes: list[str] = Field(default_factory=list)
    admin_note: str | None = Field(default=None, max_length=2000)


class WithdrawPredictionRequest(StrictModel):
    reason: str = Field(min_length=1, max_length=1000)


class AddPublicationNoteRequest(StrictModel):
    note: str = Field(min_length=1, max_length=2000)


class RefreshPublicProjectionsRequest(StrictModel):
    cutoff_at_or_before: str | None = None


class RestAnnouncementRequest(StrictModel):
    confirmed: bool
    admin_note: str | None = Field(default=None, max_length=2000)


class WithdrawAnnouncementRequest(StrictModel):
    reason: str = Field(min_length=1, max_length=1000)


class SettingGroup(StrEnum):
    SCORING_RULES = "scoring_rules"
    LEDGER_RISK = "ledger_risk"
    DATA_AUTOMATION = "data_automation"
    USER_MANAGEMENT = "user_management"
    PROMPTS_METHODOLOGY = "prompts_methodology"


class SaveSettingsRequest(StrictModel):
    expected_version: int | None = Field(default=None, ge=1)
    value: dict[str, Any]
    change_note: str = Field(min_length=1, max_length=1000)


class UserStatusRequest(StrictModel):
    reason: str = Field(min_length=1, max_length=1000)
    confirmed: bool


class SyncScope(StrEnum):
    TODAY = "today"
    DATE = "date"
    MATCH = "match"


class TriggerSyncRequest(StrictModel):
    scope: SyncScope
    business_date: str | None = None
    match_id: UUID | None = None


class AdjudicateResultRequest(StrictModel):
    result_version_id: UUID
    source_record_ids: list[str] = Field(min_length=1)
    reason: str = Field(min_length=1, max_length=1000)
    confirmed: bool


class RoundtableControlRequest(StrictModel):
    match_run_id: UUID | None = None
    expected_state_version: int = Field(ge=0)
    reason: str = Field(min_length=1, max_length=1000)
    confirmed: bool


class ProviderExecutionMode(StrEnum):
    API = "api"
    CODEX_CLI = "codex_cli"


class SaveProviderRequest(StrictModel):
    provider_id: UUID | None = None
    connection_id: UUID
    connection_version: int = Field(ge=1)
    display_name: str = Field(min_length=1, max_length=100)
    execution_mode: ProviderExecutionMode
    protocol: str = Field(min_length=1, max_length=80)
    api_url: str | None = None
    runtime_key: Literal["codex"] | None = None
    model_id: str = Field(min_length=1, max_length=128)
    allowed_api_domains: list[str] = Field(default_factory=list, max_length=20)
    api_key: str | None = Field(default=None, min_length=2, max_length=10_000)
    clear_secret: bool = False
    enabled: bool = False


class SaveProviderInstanceRequest(StrictModel):
    nickname: str = Field(min_length=1, max_length=100)
    instance_number: int = Field(ge=1, le=3)
    model_id: str = Field(min_length=1, max_length=128)
    reasoning_level: str | None = Field(default=None, max_length=40)
    timeout_seconds: int = Field(default=120, ge=1, le=900)
    max_concurrency: int = Field(default=1, ge=1, le=16)
    prompt_version: str = Field(min_length=1, max_length=100)
    enabled: bool = False


def run_publication_quality_checks(
    context: PublicationQualityContext,
) -> PublicationQualityReport:
    """Apply the complete PRD 15.3 red/yellow publication checklist."""

    items = [
        PublicationQualityItem(
            code="quorum_not_met",
            severity=QualitySeverity.BLOCK,
            passed=context.quorum_met,
            message="法定人数已满足" if context.quorum_met else "未达到法定人数",
        ),
        PublicationQualityItem(
            code="illegal_bet",
            severity=QualitySeverity.BLOCK,
            passed=context.legal_bet,
            message=("玩法与串关组合合法" if context.legal_bet else "方案含非法玩法或串关组合"),
        ),
        PublicationQualityItem(
            code="sales_cutoff_too_close",
            severity=QualitySeverity.BLOCK,
            passed=context.minutes_to_sales_cutoff >= 10,
            message=(
                "距停售时间充足" if context.minutes_to_sales_cutoff >= 10 else "距停售不足 10 分钟"
            ),
        ),
        PublicationQualityItem(
            code="duplicate_active_card",
            severity=QualitySeverity.BLOCK,
            passed=not context.duplicate_active_card,
            message=(
                "没有重复在售卡片" if not context.duplicate_active_card else "同场次已有在售卡片"
            ),
        ),
        PublicationQualityItem(
            code="stale_odds",
            severity=QualitySeverity.WARNING,
            passed=context.odds_age_minutes <= 60,
            message=("赔率快照有效" if context.odds_age_minutes <= 60 else "赔率快照超过 60 分钟"),
        ),
        PublicationQualityItem(
            code="unsupported_facts",
            severity=QualitySeverity.WARNING,
            passed=context.unsupported_fact_count == 0,
            message=(
                "事实性陈述均有来源"
                if context.unsupported_fact_count == 0
                else "辩论理由含无来源事实性陈述"
            ),
        ),
        PublicationQualityItem(
            code="missing_critical_data",
            severity=QualitySeverity.WARNING,
            passed=not context.missing_critical_fields,
            message=(
                "关键数据完整"
                if not context.missing_critical_fields
                else "关键数据暂缺：" + "、".join(context.missing_critical_fields)
            ),
        ),
    ]
    return PublicationQualityReport(
        publishable=all(item.passed for item in items if item.severity is QualitySeverity.BLOCK),
        items=items,
    )


def require_admin(request: Request) -> AuthenticatedPrincipal:
    principal = getattr(request.state, "principal", None)
    if not isinstance(principal, AuthenticatedPrincipal):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="authentication_required",
        )
    if principal.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="administrator_required")
    return principal


def get_admin_gateway(request: Request) -> AdminGateway:
    gateway = getattr(request.app.state, "admin_gateway", None)
    if gateway is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="admin_gateway_unavailable",
        )
    return gateway


AdminPrincipal = Annotated[AuthenticatedPrincipal, Depends(require_admin)]
Gateway = Annotated[AdminGateway, Depends(get_admin_gateway)]


@router.get("/publish/{prediction_id}/quality-check")
async def publication_quality_check(
    prediction_id: UUID,
    principal: AdminPrincipal,
    gateway: Gateway,
) -> Mapping[str, Any]:
    data = await _query(
        gateway,
        "publication_quality_context",
        principal,
        {"prediction_id": str(prediction_id)},
    )
    try:
        report = run_publication_quality_checks(PublicationQualityContext.model_validate(data))
    except ValueError as exc:
        raise HTTPException(status_code=502, detail="invalid_quality_context") from exc
    return report.model_dump(mode="json")


@router.get("/publish/{prediction_id}")
async def read_publication_review(
    prediction_id: UUID,
    principal: AdminPrincipal,
    gateway: Gateway,
) -> Mapping[str, Any]:
    """Read immutable notarized content plus mutable publication metadata."""

    return await _query(
        gateway,
        "read_notarized_publication_review",
        principal,
        {"prediction_id": str(prediction_id)},
    )


@router.post("/publish/{prediction_id}")
async def publish_prediction(
    prediction_id: UUID,
    body: PublishPredictionRequest,
    request: Request,
    principal: AdminPrincipal,
    gateway: Gateway,
) -> Mapping[str, Any]:
    if not body.confirm_content_lock:
        raise HTTPException(status_code=409, detail="content_lock_confirmation_required")
    context = await _query(
        gateway,
        "publication_quality_context",
        principal,
        {"prediction_id": str(prediction_id)},
    )
    try:
        report = run_publication_quality_checks(PublicationQualityContext.model_validate(context))
    except ValueError as exc:
        raise HTTPException(status_code=502, detail="invalid_quality_context") from exc
    if not report.publishable:
        raise HTTPException(status_code=409, detail="publication_quality_blocked")
    warning_codes = {
        item.code
        for item in report.items
        if item.severity is QualitySeverity.WARNING and not item.passed
    }
    if not warning_codes.issubset(body.acknowledged_warning_codes):
        raise HTTPException(status_code=409, detail="publication_warnings_not_acknowledged")
    return await _command(
        gateway,
        "publish_prediction",
        principal,
        request,
        {"prediction_id": str(prediction_id), **body.model_dump(mode="json")},
    )


@router.post("/publish/{prediction_id}/note", status_code=201)
async def add_publication_note(
    prediction_id: UUID,
    body: AddPublicationNoteRequest,
    request: Request,
    principal: AdminPrincipal,
    gateway: Gateway,
) -> Mapping[str, Any]:
    """Append a note without mutating any notarized score, vote, odds, or stake field."""

    return await _command(
        gateway,
        "append_publication_note",
        principal,
        request,
        {"prediction_id": str(prediction_id), **body.model_dump(mode="json")},
    )


@router.post("/publish/{prediction_id}/withdraw")
async def withdraw_prediction(
    prediction_id: UUID,
    body: WithdrawPredictionRequest,
    request: Request,
    principal: AdminPrincipal,
    gateway: Gateway,
) -> Mapping[str, Any]:
    return await _command(
        gateway,
        "withdraw_prediction",
        principal,
        request,
        {"prediction_id": str(prediction_id), **body.model_dump(mode="json")},
    )


@router.post("/publication-projections/refresh", status_code=202)
async def refresh_auto_public_projections(
    body: RefreshPublicProjectionsRequest,
    request: Request,
    principal: AdminPrincipal,
    gateway: Gateway,
) -> Mapping[str, Any]:
    """Generate registered-user projections for unpublished notarized records after cutoff."""

    return await _command(
        gateway,
        "refresh_cutoff_public_projections",
        principal,
        request,
        body.model_dump(mode="json"),
    )


@router.get("/announcements/rest")
async def list_rest_announcements(
    principal: AdminPrincipal,
    gateway: Gateway,
    publication_status: Literal["draft", "published", "withdrawn"] | None = Query(
        default=None, alias="status"
    ),
) -> Mapping[str, Any]:
    return await _query(
        gateway,
        "list_rest_announcements",
        principal,
        {"status": publication_status},
    )


@router.post("/announcements/rest/{announcement_id}/publish")
async def publish_rest_announcement(
    announcement_id: UUID,
    body: RestAnnouncementRequest,
    request: Request,
    principal: AdminPrincipal,
    gateway: Gateway,
) -> Mapping[str, Any]:
    if not body.confirmed:
        raise HTTPException(status_code=409, detail="announcement_confirmation_required")
    return await _command(
        gateway,
        "publish_rest_announcement",
        principal,
        request,
        {"announcement_id": str(announcement_id), **body.model_dump(mode="json")},
    )


@router.post("/announcements/rest/{announcement_id}/withdraw")
async def withdraw_rest_announcement(
    announcement_id: UUID,
    body: WithdrawAnnouncementRequest,
    request: Request,
    principal: AdminPrincipal,
    gateway: Gateway,
) -> Mapping[str, Any]:
    return await _command(
        gateway,
        "withdraw_rest_announcement",
        principal,
        request,
        {"announcement_id": str(announcement_id), **body.model_dump(mode="json")},
    )


@router.get("/settings/{group}")
async def read_settings(
    group: SettingGroup,
    principal: AdminPrincipal,
    gateway: Gateway,
) -> Mapping[str, Any]:
    return await _query(gateway, "read_settings", principal, {"group": group.value})


@router.post("/settings/{group}", status_code=201)
async def save_settings(
    group: SettingGroup,
    body: SaveSettingsRequest,
    request: Request,
    principal: AdminPrincipal,
    gateway: Gateway,
) -> Mapping[str, Any]:
    return await _command(
        gateway,
        "save_settings_version",
        principal,
        request,
        {"group": group.value, **body.model_dump(mode="json")},
    )


@router.get("/users")
async def list_users(
    principal: AdminPrincipal,
    gateway: Gateway,
    search: str | None = Query(default=None, max_length=200),
    profile_status: Literal["active", "pending_consent", "disabled"] | None = Query(
        default=None, alias="status"
    ),
    cursor: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
) -> Mapping[str, Any]:
    return await _query(
        gateway,
        "list_users",
        principal,
        {"search": search, "status": profile_status, "cursor": cursor, "limit": limit},
    )


@router.post("/users/{user_id}/disable")
async def disable_user(
    user_id: UUID,
    body: UserStatusRequest,
    request: Request,
    principal: AdminPrincipal,
    gateway: Gateway,
) -> Mapping[str, Any]:
    return await _confirmed_user_command("disable_user", user_id, body, request, principal, gateway)


@router.post("/users/{user_id}/restore")
async def restore_user(
    user_id: UUID,
    body: UserStatusRequest,
    request: Request,
    principal: AdminPrincipal,
    gateway: Gateway,
) -> Mapping[str, Any]:
    return await _confirmed_user_command("restore_user", user_id, body, request, principal, gateway)


@router.post("/sync", status_code=202)
async def trigger_sync(
    body: TriggerSyncRequest,
    request: Request,
    principal: AdminPrincipal,
    gateway: Gateway,
) -> Mapping[str, Any]:
    if body.scope is SyncScope.DATE and not body.business_date:
        raise HTTPException(status_code=422, detail="business_date_required")
    if body.scope is SyncScope.MATCH and not body.match_id:
        raise HTTPException(status_code=422, detail="match_id_required")
    return await _command(gateway, "trigger_sync", principal, request, body.model_dump(mode="json"))


@router.get("/sync/runs")
async def list_sync_runs(
    principal: AdminPrincipal,
    gateway: Gateway,
    cursor: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
) -> Mapping[str, Any]:
    return await _query(gateway, "list_sync_runs", principal, {"cursor": cursor, "limit": limit})


@router.post("/sync/runs/{run_id}/retry", status_code=202)
async def retry_sync_run(
    run_id: UUID,
    request: Request,
    principal: AdminPrincipal,
    gateway: Gateway,
) -> Mapping[str, Any]:
    return await _command(gateway, "retry_sync_run", principal, request, {"run_id": str(run_id)})


@router.get("/results/conflicts")
async def list_result_conflicts(
    principal: AdminPrincipal,
    gateway: Gateway,
) -> Mapping[str, Any]:
    return await _query(gateway, "list_result_conflicts", principal, {})


@router.post("/results/conflicts/{conflict_id}/adjudicate")
async def adjudicate_result(
    conflict_id: UUID,
    body: AdjudicateResultRequest,
    request: Request,
    principal: AdminPrincipal,
    gateway: Gateway,
) -> Mapping[str, Any]:
    if not body.confirmed:
        raise HTTPException(status_code=409, detail="adjudication_confirmation_required")
    return await _command(
        gateway,
        "adjudicate_result",
        principal,
        request,
        {"conflict_id": str(conflict_id), **body.model_dump(mode="json")},
    )


@router.post("/roundtables/{job_id}/skip-debate")
async def skip_roundtable_debate(
    job_id: UUID,
    body: RoundtableControlRequest,
    request: Request,
    principal: AdminPrincipal,
    gateway: Gateway,
) -> Mapping[str, Any]:
    return await _roundtable_control(
        "skip_roundtable_debate", job_id, body, request, principal, gateway
    )


@router.post("/roundtables/{job_id}/terminate")
async def terminate_roundtable(
    job_id: UUID,
    body: RoundtableControlRequest,
    request: Request,
    principal: AdminPrincipal,
    gateway: Gateway,
) -> Mapping[str, Any]:
    return await _roundtable_control(
        "terminate_roundtable", job_id, body, request, principal, gateway
    )


@router.get("/providers")
async def list_providers(
    principal: AdminPrincipal,
    gateway: Gateway,
) -> Mapping[str, Any]:
    return await _query(gateway, "list_providers", principal, {})


@router.get("/providers/runtime/codex")
async def inspect_codex_runtime(principal: AdminPrincipal) -> Mapping[str, Any]:
    del principal
    runner_url = os.getenv("CODEX_RUNNER_URL", "http://127.0.0.1:8765").rstrip("/")
    token = os.getenv("ALEA_RUNNER_TOKEN", "")
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            health_response, models_response = await asyncio.gather(
                client.get(f"{runner_url}/health"),
                client.get(
                    f"{runner_url}/models",
                    headers={"X-Alea-Runner-Token": token},
                ),
            )
        health_response.raise_for_status()
        models_response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail="codex_runner_unavailable") from exc
    return {
        "runtime_key": "codex",
        "health": health_response.json(),
        "catalog": models_response.json(),
    }


@router.put("/providers/{connection_id}")
async def save_provider(
    connection_id: UUID,
    body: SaveProviderRequest,
    request: Request,
    principal: AdminPrincipal,
    gateway: Gateway,
) -> Mapping[str, Any]:
    if connection_id != body.connection_id:
        raise HTTPException(status_code=422, detail="connection_id_mismatch")
    if body.clear_secret and body.api_key:
        raise HTTPException(status_code=422, detail="secret_action_conflict")
    if body.execution_mode is ProviderExecutionMode.CODEX_CLI:
        if body.runtime_key != "codex" or body.api_url or body.api_key or body.allowed_api_domains:
            raise HTTPException(status_code=422, detail="invalid_codex_cli_configuration")
    elif (
        body.runtime_key is not None
        or not body.api_url
        or not body.api_url.startswith("https://")
        or not body.allowed_api_domains
    ):
        raise HTTPException(status_code=422, detail="invalid_api_provider_configuration")

    payload = body.model_dump(mode="json", exclude={"api_key"})
    if body.api_key is not None:
        envelope = EnvelopeEncryption().encrypt(
            body.api_key,
            connection_id=body.connection_id,
            connection_version=body.connection_version,
        )
        payload["encrypted_secret"] = {
            key: value.hex() if isinstance(value, bytes) else value
            for key, value in envelope.as_record().items()
        }
    return await _command(gateway, "save_provider", principal, request, payload)


@router.post("/providers/{connection_id}/test")
async def test_provider_connection(
    connection_id: UUID,
    request: Request,
    principal: AdminPrincipal,
    gateway: Gateway,
) -> Mapping[str, Any]:
    return await _command(
        gateway,
        "test_provider_connection",
        principal,
        request,
        {"connection_id": str(connection_id)},
    )


@router.delete("/providers/{connection_id}/secret")
async def clear_provider_secret(
    connection_id: UUID,
    request: Request,
    principal: AdminPrincipal,
    gateway: Gateway,
) -> Mapping[str, Any]:
    return await _command(
        gateway,
        "clear_provider_secret",
        principal,
        request,
        {"connection_id": str(connection_id)},
    )


@router.post("/providers/{provider_id}/instances", status_code=201)
async def create_provider_instance(
    provider_id: UUID,
    body: SaveProviderInstanceRequest,
    request: Request,
    principal: AdminPrincipal,
    gateway: Gateway,
) -> Mapping[str, Any]:
    return await _command(
        gateway,
        "create_provider_instance",
        principal,
        request,
        {"provider_id": str(provider_id), **body.model_dump(mode="json")},
    )


@router.put("/providers/{provider_id}/instances/{instance_id}")
async def update_provider_instance(
    provider_id: UUID,
    instance_id: UUID,
    body: SaveProviderInstanceRequest,
    request: Request,
    principal: AdminPrincipal,
    gateway: Gateway,
) -> Mapping[str, Any]:
    return await _command(
        gateway,
        "update_provider_instance",
        principal,
        request,
        {
            "provider_id": str(provider_id),
            "instance_id": str(instance_id),
            **body.model_dump(mode="json"),
        },
    )


@router.delete("/providers/{provider_id}/instances/{instance_id}")
async def delete_provider_instance(
    provider_id: UUID,
    instance_id: UUID,
    request: Request,
    principal: AdminPrincipal,
    gateway: Gateway,
) -> Mapping[str, Any]:
    return await _command(
        gateway,
        "delete_provider_instance",
        principal,
        request,
        {"provider_id": str(provider_id), "instance_id": str(instance_id)},
    )


async def _confirmed_user_command(
    operation: str,
    user_id: UUID,
    body: UserStatusRequest,
    request: Request,
    principal: AuthenticatedPrincipal,
    gateway: AdminGateway,
) -> Mapping[str, Any]:
    if not body.confirmed:
        raise HTTPException(status_code=409, detail="user_status_confirmation_required")
    return await _command(
        gateway,
        operation,
        principal,
        request,
        {"user_id": str(user_id), **body.model_dump(mode="json")},
    )


async def _roundtable_control(
    operation: str,
    job_id: UUID,
    body: RoundtableControlRequest,
    request: Request,
    principal: AuthenticatedPrincipal,
    gateway: AdminGateway,
) -> Mapping[str, Any]:
    if not body.confirmed:
        raise HTTPException(status_code=409, detail="roundtable_control_confirmation_required")
    return await _command(
        gateway,
        operation,
        principal,
        request,
        {"job_id": str(job_id), **body.model_dump(mode="json")},
    )


async def _query(
    gateway: AdminGateway,
    operation: str,
    principal: AuthenticatedPrincipal,
    params: Mapping[str, Any],
) -> Mapping[str, Any]:
    try:
        return await gateway.query(operation, actor_id=principal.subject, params=params)
    except AdminGatewayError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.code) from exc


async def _command(
    gateway: AdminGateway,
    operation: str,
    principal: AuthenticatedPrincipal,
    request: Request,
    payload: Mapping[str, Any],
) -> Mapping[str, Any]:
    try:
        if not isinstance(payload, Mapping):
            raise AdminGatewayError("invalid_admin_command_payload", status_code=500)
        # The gateway needs the encrypted Provider envelope to persist it.
        # Redaction belongs only on the audit/log copy inside the gateway's
        # transaction; applying it here would replace `encrypted_secret`.
        return await gateway.command(
            operation,
            actor_id=principal.subject,
            request_id=str(getattr(request.state, "request_id", "missing-request-id")),
            payload=payload,
        )
    except AdminGatewayError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.code) from exc

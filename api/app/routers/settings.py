from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Mapping, Protocol, Sequence
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field

from app.security import AuthenticatedPrincipal


router = APIRouter(prefix="/v1/settings", tags=["settings"])
messages_router = APIRouter(prefix="/v1/messages", tags=["messages"])
admin_settings_router = APIRouter(prefix="/v1/admin/settings", tags=["admin-settings"])


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class NotificationPreferences(StrictModel):
    prediction_published: bool = True
    followed_settled: bool = True
    followed_review_published: bool = True


class PersonalSettings(StrictModel):
    display_name: str = Field(min_length=1, max_length=100)
    avatar_path: str | None = Field(default=None, max_length=500)
    notification_preferences: NotificationPreferences


class MessageProjection(StrictModel):
    message_id: UUID
    kind: str
    title: str
    body: str
    target_path: str
    created_at: datetime
    read_at: datetime | None = None


class MessagePage(StrictModel):
    items: list[MessageProjection]
    unread_count: int = Field(ge=0)
    next_cursor: str | None = None


class SystemSettingVersion(StrictModel):
    setting_key: str
    version: int = Field(ge=1)
    value: dict[str, Any]
    change_note: str
    created_by: str
    created_at: datetime
    read_only: bool = True


class SaveSystemSettingRequest(StrictModel):
    expected_version: int | None = Field(default=None, ge=1)
    value: dict[str, Any]
    change_note: str = Field(min_length=1, max_length=1000)


class FollowRequest(StrictModel):
    target_type: str = Field(pattern="^(match|prediction)$")
    target_id: UUID


class AccountDeletionRequest(StrictModel):
    confirmation: str


class SettingsGateway(Protocol):
    async def query(
        self, operation: str, *, actor_id: str, params: Mapping[str, Any]
    ) -> Mapping[str, Any] | Sequence[Mapping[str, Any]] | None: ...

    async def command(
        self,
        operation: str,
        *,
        actor_id: str,
        request_id: str,
        payload: Mapping[str, Any],
    ) -> Mapping[str, Any] | None: ...


def require_user(request: Request) -> AuthenticatedPrincipal:
    principal = getattr(request.state, "principal", None)
    if not isinstance(principal, AuthenticatedPrincipal):
        raise HTTPException(status_code=401, detail="authentication_required")
    return principal


def require_admin(request: Request) -> AuthenticatedPrincipal:
    principal = require_user(request)
    if principal.role != "admin":
        raise HTTPException(status_code=403, detail="administrator_required")
    return principal


def get_gateway(request: Request) -> SettingsGateway:
    gateway = getattr(request.app.state, "settings_gateway", None)
    if gateway is None:
        raise HTTPException(status_code=503, detail="settings_gateway_unavailable")
    return gateway


User = Annotated[AuthenticatedPrincipal, Depends(require_user)]
Admin = Annotated[AuthenticatedPrincipal, Depends(require_admin)]
Gateway = Annotated[SettingsGateway, Depends(get_gateway)]
RequestId = Annotated[str, Header(alias="X-Request-ID", min_length=1, max_length=200)]


@router.get("/me", response_model=PersonalSettings)
async def get_personal_settings(user: User, gateway: Gateway) -> PersonalSettings:
    return _model(
        await gateway.query("get_personal_settings", actor_id=user.subject, params={}),
        PersonalSettings,
        "personal_settings_not_found",
    )


@router.put("/notifications", response_model=NotificationPreferences)
async def save_notification_preferences(
    body: NotificationPreferences,
    user: User,
    gateway: Gateway,
    request_id: RequestId,
) -> NotificationPreferences:
    value = await gateway.command(
        "save_notification_preferences",
        actor_id=user.subject,
        request_id=request_id,
        payload=body.model_dump(mode="json"),
    )
    return _model(value, NotificationPreferences, "notification_preferences_not_found")


@router.post("/follows", status_code=201)
async def create_follow(
    body: FollowRequest, user: User, gateway: Gateway, request_id: RequestId
) -> dict[str, Any]:
    value = await gateway.command(
        "create_follow",
        actor_id=user.subject,
        request_id=request_id,
        payload=body.model_dump(mode="json"),
    )
    return dict(value or {})


@router.delete("/follows/{target_type}/{target_id}", status_code=204)
async def delete_follow(
    target_type: str,
    target_id: UUID,
    user: User,
    gateway: Gateway,
    request_id: RequestId,
) -> None:
    if target_type not in {"match", "prediction"}:
        raise HTTPException(status_code=422, detail="invalid_follow_target_type")
    await gateway.command(
        "delete_follow",
        actor_id=user.subject,
        request_id=request_id,
        payload={"target_type": target_type, "target_id": str(target_id)},
    )


@router.post("/account-deletion", status_code=202)
async def request_account_deletion(
    body: AccountDeletionRequest,
    user: User,
    gateway: Gateway,
    request_id: RequestId,
) -> dict[str, Any]:
    if body.confirmation != "注销账户":
        raise HTTPException(status_code=422, detail="account_deletion_confirmation_mismatch")
    value = await gateway.command(
        "request_account_deletion",
        actor_id=user.subject,
        request_id=request_id,
        payload=body.model_dump(mode="json"),
    )
    return dict(value or {"status": "pending_reauthentication"})


@messages_router.get("", response_model=MessagePage)
async def list_messages(
    user: User,
    gateway: Gateway,
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
) -> MessagePage:
    return _model(
        await gateway.query(
            "list_messages",
            actor_id=user.subject,
            params={"cursor": cursor, "limit": limit},
        ),
        MessagePage,
        "messages_not_found",
    )


@messages_router.post("/{message_id}/read", response_model=MessageProjection)
async def mark_message_read(
    message_id: UUID, user: User, gateway: Gateway, request_id: RequestId
) -> MessageProjection:
    value = await gateway.command(
        "mark_message_read",
        actor_id=user.subject,
        request_id=request_id,
        payload={"message_id": str(message_id)},
    )
    return _model(value, MessageProjection, "message_not_found")


@messages_router.post("/read-all", status_code=204)
async def mark_all_messages_read(user: User, gateway: Gateway, request_id: RequestId) -> None:
    await gateway.command(
        "mark_all_messages_read",
        actor_id=user.subject,
        request_id=request_id,
        payload={},
    )


@admin_settings_router.get("/{setting_key}", response_model=SystemSettingVersion)
async def get_system_setting(
    setting_key: str, admin: Admin, gateway: Gateway
) -> SystemSettingVersion:
    return _model(
        await gateway.query(
            "get_system_setting", actor_id=admin.subject, params={"setting_key": setting_key}
        ),
        SystemSettingVersion,
        "system_setting_not_found",
    )


@admin_settings_router.get("/{setting_key}/history", response_model=list[SystemSettingVersion])
async def system_setting_history(
    setting_key: str, admin: Admin, gateway: Gateway
) -> list[SystemSettingVersion]:
    values = await gateway.query(
        "system_setting_history", actor_id=admin.subject, params={"setting_key": setting_key}
    )
    if not isinstance(values, Sequence) or isinstance(values, (str, bytes, bytearray)):
        raise HTTPException(status_code=502, detail="invalid_system_setting_projection")
    return [_model(value, SystemSettingVersion, "system_setting_not_found") for value in values]


@admin_settings_router.put("/{setting_key}", response_model=SystemSettingVersion)
async def save_system_setting(
    setting_key: str,
    body: SaveSystemSettingRequest,
    admin: Admin,
    gateway: Gateway,
    request_id: RequestId,
) -> SystemSettingVersion:
    value = await gateway.command(
        "save_system_setting_version",
        actor_id=admin.subject,
        request_id=request_id,
        payload={"setting_key": setting_key, **body.model_dump(mode="json")},
    )
    return _model(value, SystemSettingVersion, "system_setting_not_found")


def _model(value: Any, model: type[BaseModel], not_found_detail: str) -> Any:
    if value is None:
        raise HTTPException(status_code=404, detail=not_found_detail)
    try:
        return model.model_validate(value)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=502, detail="invalid_settings_projection") from exc

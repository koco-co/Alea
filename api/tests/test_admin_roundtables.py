from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Mapping
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.routers import admin
from app.security import AuthenticatedPrincipal


class RoundtableGateway:
    def __init__(self) -> None:
        self.operation: str | None = None
        self.actor_id: str | None = None
        self.request_id: str | None = None
        self.payload: Mapping[str, Any] | None = None

    async def query(
        self,
        operation: str,
        *,
        actor_id: str,
        params: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        del operation, actor_id, params
        return {"job": {"id": str(uuid4())}}

    async def command(
        self,
        operation: str,
        *,
        actor_id: str,
        request_id: str,
        payload: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        self.operation = operation
        self.actor_id = actor_id
        self.request_id = request_id
        self.payload = payload
        return {"job_id": str(uuid4()), "state": "pending"}


@pytest.fixture()
def admin_principal() -> AuthenticatedPrincipal:
    return AuthenticatedPrincipal(
        subject="00000000-0000-0000-0000-000000000001",
        role="admin",
        email="admin@example.test",
        claims={},
    )


@pytest.mark.asyncio
async def test_start_roundtable_forwards_a_transactional_snapshot(
    admin_principal: AuthenticatedPrincipal,
) -> None:
    gateway = RoundtableGateway()
    instance_ids = [uuid4(), uuid4(), uuid4()]
    body = admin.StartRoundtableRequest(
        mode="autonomous",
        business_date="2030-01-02",
        competition_scope="all",
        instance_ids=instance_ids,
        rounds=2,
        candidate_limit=4,
        scheduled=False,
        schedule_time="08:30",
    )

    result = await admin.start_roundtable(
        body,
        SimpleNamespace(state=SimpleNamespace(request_id="roundtable-request-1")),
        admin_principal,
        gateway,
    )

    assert result["state"] == "pending"
    assert gateway.operation == "start_roundtable"
    assert gateway.actor_id == admin_principal.subject
    assert gateway.request_id == "roundtable-request-1"
    assert gateway.payload is not None
    assert gateway.payload["business_date"] == "2030-01-02"
    assert gateway.payload["instance_ids"] == [str(item) for item in instance_ids]
    assert gateway.payload["candidate_limit"] == 4


@pytest.mark.asyncio
async def test_specified_roundtable_requires_match_ids(
    admin_principal: AuthenticatedPrincipal,
) -> None:
    with pytest.raises(HTTPException) as error:
        await admin.start_roundtable(
            admin.StartRoundtableRequest(
                mode="specified",
                business_date="2030-01-02",
                instance_ids=[uuid4(), uuid4(), uuid4()],
            ),
            SimpleNamespace(state=SimpleNamespace(request_id="roundtable-request-2")),
            admin_principal,
            RoundtableGateway(),
        )

    assert error.value.status_code == 422
    assert error.value.detail == "specified_mode_requires_matches"


@pytest.mark.asyncio
async def test_local_fixture_roundtable_requires_explicit_local_flag(
    admin_principal: AuthenticatedPrincipal,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ALEA_ALLOW_LOCAL_FIXTURE_ROUNDTABLE", raising=False)
    body = admin.StartRoundtableRequest(
        mode="specified",
        business_date="2030-01-02",
        match_ids=[uuid4()],
        instance_ids=[uuid4(), uuid4(), uuid4()],
        fixture_mode=True,
    )

    with pytest.raises(HTTPException) as error:
        await admin.start_roundtable(
            body,
            SimpleNamespace(state=SimpleNamespace(request_id="fixture-request-1")),
            admin_principal,
            RoundtableGateway(),
        )

    assert error.value.status_code == 422
    assert error.value.detail == "local_fixture_roundtable_disabled"


@pytest.mark.asyncio
async def test_local_fixture_roundtable_forwards_explicit_mode(
    admin_principal: AuthenticatedPrincipal,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ALEA_ALLOW_LOCAL_FIXTURE_ROUNDTABLE", "true")
    gateway = RoundtableGateway()
    body = admin.StartRoundtableRequest(
        mode="specified",
        business_date="2030-01-02",
        match_ids=[uuid4()],
        instance_ids=[uuid4(), uuid4(), uuid4()],
        fixture_mode=True,
    )

    await admin.start_roundtable(
        body,
        SimpleNamespace(state=SimpleNamespace(request_id="fixture-request-2")),
        admin_principal,
        gateway,
    )

    assert gateway.payload is not None
    assert gateway.payload["fixture_mode"] is True


@pytest.mark.asyncio
async def test_read_roundtable_returns_not_found_for_missing_projection(
    admin_principal: AuthenticatedPrincipal,
) -> None:
    class EmptyGateway(RoundtableGateway):
        async def query(
            self,
            operation: str,
            *,
            actor_id: str,
            params: Mapping[str, Any],
        ) -> Mapping[str, Any]:
            del operation, actor_id, params
            return {"job": None}

    with pytest.raises(HTTPException) as error:
        await admin.read_roundtable(uuid4(), admin_principal, EmptyGateway())

    assert error.value.status_code == 404
    assert error.value.detail == "roundtable_not_found"

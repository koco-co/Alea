from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

from app.datasources.contract import DataSourceAdapter, DeploymentMode, MatchDataService
from app.providers.anthropic import AnthropicProvider
from app.providers.codex_cli import CodexCliProvider
from app.providers.google import GoogleProvider
from app.providers.openai import OpenAIProvider
from app.providers.openai_compat import OpenAICompatProvider


_OPERATION_NAME = re.compile(r"^[a-z][a-z0-9_]{0,99}$")


class DatasourceFactory:
    """Build the licensed degradation chain used by request and worker services."""

    def create(
        self,
        *,
        deployment_mode: DeploymentMode,
        sources: Sequence[DataSourceAdapter] = (),
    ) -> MatchDataService:
        return MatchDataService(deployment_mode=deployment_mode, sources=tuple(sources))


class ProviderFactory:
    """Create only the provider adapters supported by Alea's runtime contract."""

    def create(self, provider_type: str, **configuration: Any) -> Any:
        providers = {
            "anthropic": AnthropicProvider,
            "codex_cli": CodexCliProvider,
            "google": GoogleProvider,
            "openai": OpenAIProvider,
            "openai_compat": OpenAICompatProvider,
        }
        provider_class = providers.get(provider_type)
        if provider_class is None:
            raise ValueError("unsupported_provider_type")
        return provider_class(**configuration)


class BusinessGateway:
    """Runtime boundary shared by FastAPI routers.

    The event reader is deliberately explicit because it crosses the internal/public
    projection boundary. Other business operations are routed through versioned
    database functions named ``alea_query_*`` and ``alea_command_*``; this keeps SQL
    and auditing in the database instead of interpolating table names from requests.
    """

    def __init__(
        self,
        database: Any,
        *,
        datasource_factory: DatasourceFactory,
        provider_factory: ProviderFactory,
    ) -> None:
        self.database = database
        self.datasource_factory = datasource_factory
        self.provider_factory = provider_factory

    async def read_events(
        self,
        job_id: str,
        *,
        after_seq: int,
        limit: int,
        visibility: str,
        viewer_id: str,
    ) -> list[Mapping[str, Any]]:
        del viewer_id  # Authentication and role selection happen at the router boundary.
        if visibility == "internal":
            statement = """
                select id, job_id, event_seq, event_type, payload, created_at
                from roundtable_events
                where job_id = %s and event_seq > %s
                order by event_seq asc
                limit %s
            """
        elif visibility == "public":
            statement = """
                select source_event_id as id, job_id, event_seq, event_type,
                       public_payload as payload, created_at
                from public_roundtable_events
                where job_id = %s and event_seq > %s
                order by event_seq asc
                limit %s
            """
        else:
            raise ValueError("invalid_roundtable_event_visibility")
        return await self._fetch_rows(statement, (job_id, after_seq, limit))

    async def query(
        self,
        operation: str,
        *,
        params: Mapping[str, Any],
        actor_id: str | None = None,
        viewer_id: str | None = None,
    ) -> Mapping[str, Any] | Sequence[Mapping[str, Any]] | None:
        identity = actor_id or viewer_id
        return await self._call_business_function(
            "query", operation, identity=identity, request_id=None, payload=params
        )

    async def list_matches(
        self,
        *,
        business_date: str | None,
        state: str | None,
        cursor: str | None,
        limit: int,
        viewer_id: str,
    ) -> Mapping[str, Any]:
        value = await self.query(
            "list_matches",
            viewer_id=viewer_id,
            params={
                "business_date": business_date,
                "state": state,
                "cursor": cursor,
                "limit": limit,
            },
        )
        if not isinstance(value, Mapping):
            raise TypeError("invalid_match_page_projection")
        return value

    async def get_match(
        self, match_id: str, *, viewer_id: str
    ) -> Mapping[str, Any] | None:
        value = await self.query(
            "get_match", viewer_id=viewer_id, params={"match_id": match_id}
        )
        if value is None or isinstance(value, Mapping):
            return value
        raise TypeError("invalid_match_projection")

    async def get_match_sources(
        self, match_id: str, *, viewer_id: str
    ) -> Sequence[Mapping[str, Any]]:
        value = await self.query(
            "get_match_sources", viewer_id=viewer_id, params={"match_id": match_id}
        )
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
            return value
        raise TypeError("invalid_match_source_projection")

    async def command(
        self,
        operation: str,
        *,
        actor_id: str,
        request_id: str,
        payload: Mapping[str, Any],
    ) -> Mapping[str, Any] | None:
        value = await self._call_business_function(
            "command",
            operation,
            identity=actor_id,
            request_id=request_id,
            payload=payload,
        )
        if value is None or isinstance(value, Mapping):
            return value
        raise TypeError("invalid_business_command_projection")

    async def _call_business_function(
        self,
        kind: str,
        operation: str,
        *,
        identity: str | None,
        request_id: str | None,
        payload: Mapping[str, Any],
    ) -> Any:
        if not _OPERATION_NAME.fullmatch(operation):
            raise ValueError("invalid_business_operation")
        function_name = f"alea_{kind}_{operation}"
        if kind == "query":
            statement = f"select {function_name}(%s, %s::jsonb) as value"
            parameters = (identity, _json_payload(payload))
        else:
            statement = f"select {function_name}(%s, %s, %s::jsonb) as value"
            parameters = (identity, request_id, _json_payload(payload))
        rows = await self._fetch_rows(statement, parameters)
        return rows[0].get("value") if rows else None

    async def _fetch_rows(
        self, statement: str, parameters: Sequence[Any]
    ) -> list[Mapping[str, Any]]:
        async with self.database.cursor() as cursor:
            await cursor.execute(statement, parameters)
            rows = await cursor.fetchall()
            if all(isinstance(row, Mapping) for row in rows):
                return list(rows)
            columns = [column.name for column in cursor.description or ()]
            return [dict(zip(columns, row, strict=True)) for row in rows]


def _json_payload(value: Mapping[str, Any]) -> str:
    import json

    return json.dumps(dict(value), separators=(",", ":"), ensure_ascii=False, default=str)

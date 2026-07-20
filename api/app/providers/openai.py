from __future__ import annotations

from collections.abc import Mapping

import httpx

from app.providers.openai_compat import OpenAICompatProvider


class OpenAIProvider(OpenAICompatProvider):
    """OpenAI native adapter using the shared structured-output contract."""

    provider_name = "openai"

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        organization: str | None = None,
        project: str | None = None,
        client: httpx.AsyncClient | None = None,
        default_headers: Mapping[str, str] | None = None,
    ) -> None:
        headers = dict(default_headers or {})
        if organization:
            headers["OpenAI-Organization"] = organization
        if project:
            headers["OpenAI-Project"] = project
        super().__init__(api_key=api_key, base_url=base_url, client=client, default_headers=headers)


OpenAIAdapter = OpenAIProvider

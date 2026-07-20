from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict, Field


EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


class SignupRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=256)
    age_confirmed: bool
    terms_accepted: bool


class SignupFailure(RuntimeError):
    def __init__(self, code: str, status_code: int) -> None:
        super().__init__(code)
        self.code = code
        self.status_code = status_code


@dataclass(frozen=True)
class SignupResult:
    user_id: str
    requires_email_confirmation: bool


class SupabaseAuthGateway:
    def __init__(
        self,
        *,
        url: str,
        publishable_key: str,
        secret_key: str,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        if not url.startswith("https://") or not url.rstrip("/").endswith(".supabase.co"):
            raise ValueError("SUPABASE_URL must be an HTTPS supabase.co project URL")
        self.url = url.rstrip("/")
        self.publishable_key = publishable_key
        self.secret_key = secret_key
        self._owns_client = client is None
        self.client = client or httpx.AsyncClient(timeout=15, follow_redirects=False)

    async def signup(self, request: SignupRequest) -> SignupResult:
        email = request.email.strip().casefold()
        if not EMAIL_PATTERN.fullmatch(email):
            raise SignupFailure("invalid_email", 400)
        if not request.age_confirmed or not request.terms_accepted:
            raise SignupFailure("consent_required", 422)
        try:
            response = await self.client.post(
                f"{self.url}/auth/v1/signup",
                headers={"apikey": self.publishable_key, "Content-Type": "application/json"},
                json={"email": email, "password": request.password},
            )
        except httpx.HTTPError as exc:
            raise SignupFailure("auth_upstream_unavailable", 503) from exc
        if response.status_code not in {200, 201}:
            raise SignupFailure("signup_rejected", 400)
        try:
            payload: dict[str, Any] = response.json()
        except ValueError as exc:
            raise SignupFailure("signup_incomplete", 502) from exc
        user = payload.get("user")
        user_id = user.get("id") if isinstance(user, dict) else None
        if not isinstance(user_id, str):
            raise SignupFailure("signup_incomplete", 502)
        consent = await self.client.post(
            f"{self.url}/rest/v1/rpc/record_user_consent_from_signup",
            headers={
                "apikey": self.secret_key,
                "Authorization": f"Bearer {self.secret_key}",
                "Content-Type": "application/json",
            },
            json={
                "p_user_id": user_id,
                "p_terms_version": "terms-v1",
                "p_privacy_version": "privacy-v1",
                "p_risk_version": "risk-v1",
            },
        )
        if consent.status_code not in {200, 204}:
            await self._delete_incomplete_user(user_id)
            raise SignupFailure("consent_persistence_failed", 503)
        return SignupResult(
            user_id=user_id,
            requires_email_confirmation=not isinstance(payload.get("access_token"), str),
        )

    async def _delete_incomplete_user(self, user_id: str) -> None:
        try:
            await self.client.delete(
                f"{self.url}/auth/v1/admin/users/{user_id}",
                headers={
                    "apikey": self.secret_key,
                    "Authorization": f"Bearer {self.secret_key}",
                },
            )
        except httpx.HTTPError:
            return

    async def close(self) -> None:
        if self._owns_client:
            await self.client.aclose()

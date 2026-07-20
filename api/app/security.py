from __future__ import annotations

import ipaddress
import json
import re
import socket
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import httpx
import jwt
from jwt import PyJWKClient


class SecurityError(ValueError):
    """A stable, non-sensitive security validation failure."""


@dataclass(frozen=True)
class AuthenticatedPrincipal:
    subject: str
    role: str
    email: str | None
    claims: Mapping[str, Any]


class JWTVerifier:
    def __init__(
        self,
        *,
        issuer: str,
        audience: str = "authenticated",
        jwks_url: str | None = None,
        key_resolver: Callable[[str], Any] | None = None,
    ) -> None:
        self.issuer = issuer.rstrip("/")
        self.audience = audience
        self._key_resolver = key_resolver
        self._jwks_client = PyJWKClient(
            jwks_url or f"{self.issuer}/.well-known/jwks.json",
            cache_keys=True,
            lifespan=300,
        )

    def verify(self, token: str) -> AuthenticatedPrincipal:
        try:
            key = (
                self._key_resolver(token)
                if self._key_resolver
                else self._jwks_client.get_signing_key_from_jwt(token).key
            )
            claims = jwt.decode(
                token,
                key,
                algorithms=["RS256", "ES256"],
                issuer=self.issuer,
                audience=self.audience,
                options={"require": ["exp", "iat", "iss", "aud", "sub"]},
            )
        except jwt.PyJWTError as exc:
            raise SecurityError("invalid_access_token") from exc

        subject = claims.get("sub")
        if not isinstance(subject, str) or not subject:
            raise SecurityError("invalid_access_token")
        app_metadata = claims.get("app_metadata")
        trusted_role = app_metadata.get("role") if isinstance(app_metadata, dict) else None
        role = trusted_role if trusted_role in {"user", "admin"} else "user"
        email = claims.get("email") if isinstance(claims.get("email"), str) else None
        return AuthenticatedPrincipal(subject=subject, role=role, email=email, claims=claims)


SENSITIVE_KEY = re.compile(
    r"(?i)(authorization|cookie|set-cookie|api[-_]?key|secret|token|password|provider.*body)"
)
BEARER = re.compile(r"(?i)\bbearer\s+[a-z0-9._~+/=-]+")
API_KEY = re.compile(r"(?i)\b(?:sk|key|token)[-_][a-z0-9_-]{8,}\b")


def redact_sensitive(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): "[REDACTED]" if SENSITIVE_KEY.search(str(key)) else redact_sensitive(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_sensitive(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact_sensitive(item) for item in value)
    if isinstance(value, str):
        sanitized = BEARER.sub("Bearer [REDACTED]", value)
        sanitized = API_KEY.sub("[REDACTED]", sanitized)
        try:
            parsed = urlsplit(sanitized)
        except ValueError:
            return sanitized
        if parsed.scheme and parsed.netloc and parsed.query:
            query = [
                (key, "[REDACTED]" if SENSITIVE_KEY.search(key) else item)
                for key, item in parse_qsl(parsed.query, keep_blank_values=True)
            ]
            return urlunsplit(
                (parsed.scheme, parsed.netloc, parsed.path, urlencode(query), parsed.fragment)
            )
        return sanitized
    return value


DENIED_HOSTS = {
    "localhost",
    "metadata.google.internal",
    "metadata.azure.internal",
    "instance-data.ec2.internal",
}


def _is_forbidden_ip(address: str) -> bool:
    ip = ipaddress.ip_address(address)
    return any(
        (
            ip.is_private,
            ip.is_loopback,
            ip.is_link_local,
            ip.is_multicast,
            ip.is_reserved,
            ip.is_unspecified,
        )
    )


def validate_outbound_url(
    value: str,
    *,
    allowed_hosts: set[str] | None = None,
    resolver: Callable[..., list[tuple[Any, ...]]] = socket.getaddrinfo,
    allow_proxy_synthetic_dns: bool = False,
) -> str:
    try:
        parsed = urlsplit(value)
    except ValueError as exc:
        raise SecurityError("invalid_outbound_url") from exc
    hostname = parsed.hostname.casefold().rstrip(".") if parsed.hostname else ""
    if parsed.scheme != "https" or not hostname or parsed.username or parsed.password:
        raise SecurityError("outbound_url_requires_https_host")
    if hostname in DENIED_HOSTS or hostname.endswith(".localhost"):
        raise SecurityError("outbound_host_forbidden")
    if allowed_hosts is not None and hostname not in {host.casefold() for host in allowed_hosts}:
        raise SecurityError("outbound_host_not_allowlisted")
    try:
        literal = ipaddress.ip_address(hostname.strip("[]"))
    except ValueError:
        try:
            answers = resolver(hostname, parsed.port or 443, type=socket.SOCK_STREAM)
        except OSError as exc:
            raise SecurityError("outbound_host_unresolvable") from exc
        addresses = {answer[4][0] for answer in answers}
    else:
        addresses = {str(literal)}
    synthetic_proxy_network = ipaddress.ip_network("198.18.0.0/15")
    proxy_synthetic_only = bool(addresses) and all(
        ipaddress.ip_address(address) in synthetic_proxy_network for address in addresses
    )
    if (
        not addresses
        or any(_is_forbidden_ip(address) for address in addresses)
        and not (
            allow_proxy_synthetic_dns
            and allowed_hosts is not None
            and hostname in {host.casefold() for host in allowed_hosts}
            and proxy_synthetic_only
        )
    ):
        raise SecurityError("outbound_address_forbidden")
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path or "/", parsed.query, ""))


def safe_json(value: Any) -> str:
    return json.dumps(redact_sensitive(value), ensure_ascii=False, separators=(",", ":"))


class SafeHttpClient:
    def __init__(
        self,
        *,
        allowed_hosts: set[str],
        client: httpx.AsyncClient | None = None,
        max_redirects: int = 2,
        max_response_bytes: int = 2_000_000,
        resolver: Callable[..., list[tuple[Any, ...]]] = socket.getaddrinfo,
    ) -> None:
        self.allowed_hosts = allowed_hosts
        self.client = client or httpx.AsyncClient(timeout=20, follow_redirects=False)
        self._owns_client = client is None
        self.max_redirects = max_redirects
        self.max_response_bytes = max_response_bytes
        self.resolver = resolver

    async def get(self, url: str, *, allowed_content_types: set[str]) -> bytes:
        current = url
        for redirect_count in range(self.max_redirects + 1):
            safe_url = validate_outbound_url(
                current,
                allowed_hosts=self.allowed_hosts,
                resolver=self.resolver,
            )
            async with self.client.stream("GET", safe_url) as response:
                if response.status_code in {301, 302, 303, 307, 308}:
                    location = response.headers.get("location")
                    if not location or redirect_count >= self.max_redirects:
                        raise SecurityError("outbound_redirect_rejected")
                    current = str(httpx.URL(safe_url).join(location))
                    continue
                if response.status_code >= 400:
                    raise SecurityError("outbound_request_failed")
                content_type = response.headers.get("content-type", "").split(";", 1)[0].casefold()
                if content_type not in {item.casefold() for item in allowed_content_types}:
                    raise SecurityError("outbound_content_type_rejected")
                chunks: list[bytes] = []
                size = 0
                async for chunk in response.aiter_bytes():
                    size += len(chunk)
                    if size > self.max_response_bytes:
                        raise SecurityError("outbound_response_too_large")
                    chunks.append(chunk)
                return b"".join(chunks)
        raise SecurityError("outbound_redirect_rejected")

    async def close(self) -> None:
        if self._owns_client:
            await self.client.aclose()

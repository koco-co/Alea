from __future__ import annotations

import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from typing import Any
from uuid import UUID

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

NONCE_BYTES = 12
DEK_BITS = 256
SECRET_TAIL_LENGTH = 4


class EnvelopeError(RuntimeError):
    """Base error with a stable, non-sensitive public code."""


class EnvelopeConfigurationError(EnvelopeError):
    """Raised when a versioned KEK is missing or malformed."""


class EnvelopeDecryptionError(EnvelopeError):
    """Raised when an envelope cannot be authenticated and decrypted."""


@dataclass(frozen=True, slots=True)
class EncryptedSecret:
    """Database-ready encrypted Provider secret fields."""

    ciphertext: bytes
    ciphertext_nonce: bytes
    wrapped_dek: bytes
    wrapped_dek_nonce: bytes
    kek_version: int
    secret_tail: str

    def __post_init__(self) -> None:
        if len(self.ciphertext_nonce) != NONCE_BYTES:
            raise ValueError("ciphertext_nonce must be 12 bytes")
        if len(self.wrapped_dek_nonce) != NONCE_BYTES:
            raise ValueError("wrapped_dek_nonce must be 12 bytes")
        if self.kek_version < 1:
            raise ValueError("kek_version must be positive")
        if not 2 <= len(self.secret_tail) <= 12:
            raise ValueError("secret_tail must contain between 2 and 12 characters")

    def as_record(self) -> dict[str, bytes | int | str]:
        return {
            "ciphertext": self.ciphertext,
            "ciphertext_nonce": self.ciphertext_nonce,
            "wrapped_dek": self.wrapped_dek,
            "wrapped_dek_nonce": self.wrapped_dek_nonce,
            "kek_version": self.kek_version,
            "secret_tail": self.secret_tail,
        }

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> EncryptedSecret:
        return cls(
            ciphertext=bytes(record["ciphertext"]),
            ciphertext_nonce=bytes(record["ciphertext_nonce"]),
            wrapped_dek=bytes(record["wrapped_dek"]),
            wrapped_dek_nonce=bytes(record["wrapped_dek_nonce"]),
            kek_version=int(record["kek_version"]),
            secret_tail=str(record["secret_tail"]),
        )


def load_kek(kek_version: int, environ: Mapping[str, str] | None = None) -> bytes:
    if kek_version < 1:
        raise EnvelopeConfigurationError("KEK version must be positive")

    variable = f"PROVIDER_KEK_V{kek_version}"
    source = os.environ if environ is None else environ
    value = source.get(variable)
    if not value:
        raise EnvelopeConfigurationError(f"{variable} is not configured")

    try:
        key = bytes.fromhex(value)
    except ValueError as exc:
        raise EnvelopeConfigurationError(f"{variable} must be a 64-character hex key") from exc

    if len(value) != 64 or len(key) != 32:
        raise EnvelopeConfigurationError(f"{variable} must be a 64-character hex key")
    return key


def _connection_aad(connection_id: UUID | str, connection_version: int) -> bytes:
    normalized_id = str(connection_id).strip()
    if not normalized_id or "\x00" in normalized_id:
        raise ValueError("connection_id must be a non-empty identifier")
    if connection_version < 1:
        raise ValueError("connection_version must be positive")
    return f"alea/provider-secret/v1\x00{normalized_id}\x00{connection_version}".encode()


class EnvelopeEncryption:
    """AES-256-GCM envelope encryption bound to a connection and version."""

    def __init__(self, key_resolver: Callable[[int], bytes] = load_kek) -> None:
        self._key_resolver = key_resolver

    def encrypt(
        self,
        secret: str,
        *,
        connection_id: UUID | str,
        connection_version: int,
        kek_version: int = 1,
    ) -> EncryptedSecret:
        if len(secret) < 2:
            raise ValueError("secret must contain at least two characters")

        kek = self._validated_kek(kek_version)
        aad = _connection_aad(connection_id, connection_version)
        wrap_aad = aad + f"\x00kek-v{kek_version}\x00dek-wrap".encode()
        dek = AESGCM.generate_key(bit_length=DEK_BITS)
        ciphertext_nonce = os.urandom(NONCE_BYTES)
        wrapped_dek_nonce = os.urandom(NONCE_BYTES)

        ciphertext = AESGCM(dek).encrypt(ciphertext_nonce, secret.encode(), aad)
        wrapped_dek = AESGCM(kek).encrypt(wrapped_dek_nonce, dek, wrap_aad)

        return EncryptedSecret(
            ciphertext=ciphertext,
            ciphertext_nonce=ciphertext_nonce,
            wrapped_dek=wrapped_dek,
            wrapped_dek_nonce=wrapped_dek_nonce,
            kek_version=kek_version,
            secret_tail=secret[-SECRET_TAIL_LENGTH:],
        )

    def decrypt(
        self,
        envelope: EncryptedSecret | Mapping[str, Any],
        *,
        connection_id: UUID | str,
        connection_version: int,
    ) -> str:
        if isinstance(envelope, EncryptedSecret):
            encrypted = envelope
        else:
            encrypted = EncryptedSecret.from_record(envelope)
        kek = self._validated_kek(encrypted.kek_version)
        aad = _connection_aad(connection_id, connection_version)
        wrap_aad = aad + f"\x00kek-v{encrypted.kek_version}\x00dek-wrap".encode()

        try:
            dek = AESGCM(kek).decrypt(
                encrypted.wrapped_dek_nonce,
                encrypted.wrapped_dek,
                wrap_aad,
            )
            plaintext = AESGCM(dek).decrypt(
                encrypted.ciphertext_nonce,
                encrypted.ciphertext,
                aad,
            )
            return plaintext.decode()
        except (InvalidTag, UnicodeDecodeError, ValueError) as exc:
            raise EnvelopeDecryptionError("secret_authentication_failed") from exc

    def _validated_kek(self, kek_version: int) -> bytes:
        key = self._key_resolver(kek_version)
        if len(key) != 32:
            raise EnvelopeConfigurationError("Provider KEK must be exactly 32 bytes")
        return key


class EnvelopeCipher(EnvelopeEncryption):
    """Version-aware envelope cipher supporting KEK rotation without data re-encryption."""

    def __init__(
        self,
        keys: Mapping[int, bytes] | None = None,
        *,
        active_version: int = 1,
    ) -> None:
        if active_version < 1:
            raise EnvelopeConfigurationError("KEK version must be positive")
        self._keys = dict(keys) if keys is not None else None
        self.active_version = active_version
        super().__init__(self._resolve_key)
        self._validated_kek(active_version)

    def _resolve_key(self, version: int) -> bytes:
        if self._keys is None:
            return load_kek(version)
        try:
            return self._keys[version]
        except KeyError as exc:
            raise EnvelopeConfigurationError(f"PROVIDER_KEK_V{version} is not configured") from exc

    def encrypt(
        self,
        secret: str,
        *,
        connection_id: UUID | str,
        connection_version: int,
        kek_version: int | None = None,
    ) -> EncryptedSecret:
        return super().encrypt(
            secret,
            connection_id=connection_id,
            connection_version=connection_version,
            kek_version=self.active_version if kek_version is None else kek_version,
        )

    def rewrap(
        self,
        envelope: EncryptedSecret | Mapping[str, Any],
        *,
        connection_id: UUID | str,
        connection_version: int,
        target_kek_version: int,
    ) -> EncryptedSecret:
        if isinstance(envelope, EncryptedSecret):
            encrypted = envelope
        else:
            encrypted = EncryptedSecret.from_record(envelope)
        aad = _connection_aad(connection_id, connection_version)
        source_wrap_aad = (
            aad + f"\x00kek-v{encrypted.kek_version}\x00dek-wrap".encode()
        )
        target_wrap_aad = aad + f"\x00kek-v{target_kek_version}\x00dek-wrap".encode()

        try:
            dek = AESGCM(self._validated_kek(encrypted.kek_version)).decrypt(
                encrypted.wrapped_dek_nonce,
                encrypted.wrapped_dek,
                source_wrap_aad,
            )
        except (InvalidTag, ValueError) as exc:
            raise EnvelopeDecryptionError("secret_authentication_failed") from exc

        wrapped_dek_nonce = os.urandom(NONCE_BYTES)
        wrapped_dek = AESGCM(self._validated_kek(target_kek_version)).encrypt(
            wrapped_dek_nonce,
            dek,
            target_wrap_aad,
        )
        return replace(
            encrypted,
            wrapped_dek=wrapped_dek,
            wrapped_dek_nonce=wrapped_dek_nonce,
            kek_version=target_kek_version,
        )


def encrypt_secret(
    secret: str,
    *,
    connection_id: UUID | str,
    connection_version: int,
    kek_version: int = 1,
    key_resolver: Callable[[int], bytes] = load_kek,
) -> EncryptedSecret:
    return EnvelopeEncryption(key_resolver).encrypt(
        secret,
        connection_id=connection_id,
        connection_version=connection_version,
        kek_version=kek_version,
    )


def decrypt_secret(
    envelope: EncryptedSecret | Mapping[str, Any],
    *,
    connection_id: UUID | str,
    connection_version: int,
    key_resolver: Callable[[int], bytes] = load_kek,
) -> str:
    return EnvelopeEncryption(key_resolver).decrypt(
        envelope,
        connection_id=connection_id,
        connection_version=connection_version,
    )

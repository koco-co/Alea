#!/usr/bin/env python3
"""Verify the configured Provider KEK without exposing its value."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).parents[1] / "api"))

from app.secrets.envelope import (  # noqa: E402
    EnvelopeDecryptionError,
    EnvelopeEncryption,
)

from validate_env import parse_env  # noqa: E402


def main() -> int:
    values = parse_env(Path(__file__).parents[1] / ".env")
    os.environ["PROVIDER_KEK_V1"] = values["PROVIDER_KEK_V1"]
    cipher = EnvelopeEncryption()
    connection_id = uuid4()
    envelope = cipher.encrypt(
        "verification-secret",
        connection_id=connection_id,
        connection_version=1,
    )
    assert (
        cipher.decrypt(
            envelope,
            connection_id=connection_id,
            connection_version=1,
        )
        == "verification-secret"
    )
    try:
        cipher.decrypt(
            envelope,
            connection_id=uuid4(),
            connection_version=1,
        )
    except EnvelopeDecryptionError:
        pass
    else:
        raise AssertionError("wrong AAD unexpectedly decrypted the test secret")
    print(
        "Existing PROVIDER_KEK_V1 round-trip and wrong-AAD rejection passed; "
        "no secret value displayed."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

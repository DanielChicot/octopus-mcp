"""Credential resolution: env > .env > keyring > error.

Note: config.toml support is deferred to v0.2 (see plan known limitations).
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import find_dotenv, load_dotenv

from octopus_mcp.octopus.errors import ConfigError

_KEYRING_SERVICE = "octopus-mcp"
_ENV_LOADED = False


def _ensure_dotenv_loaded() -> None:
    global _ENV_LOADED
    if _ENV_LOADED:
        return
    found = find_dotenv(usecwd=True)
    if found:
        load_dotenv(found, override=False)
    _ENV_LOADED = True


def _keyring_get(profile: str, key: str) -> str | None:
    """Indirection so tests can patch."""
    try:
        import keyring
    except ImportError:
        return None
    return keyring.get_password(f"{_KEYRING_SERVICE}:{profile}", key)  # type: ignore[no-any-return]


@dataclass(frozen=True)
class OctopusCredentials:
    """Resolved Octopus credentials.

    The custom __repr__ redacts the secret fields. WARNING: this redaction
    does NOT extend to dataclasses.asdict() or dataclasses.astuple(), which
    walk fields directly and produce plaintext. Never pass an instance of
    this class to those helpers or to a generic serialiser.
    """

    api_key: str
    account_number: str
    profile: str = "default"
    email: str | None = None
    password: str | None = None

    def __repr__(self) -> str:  # never leak secrets in logs
        return f"OctopusCredentials(profile={self.profile!r}, api_key=***, account=***)"


def _read(profile: str, key: str, env_var: str) -> str | None:
    val = os.environ.get(env_var)
    if val:
        return val
    return _keyring_get(profile, key)


def resolve_credentials(profile: str | None = None) -> OctopusCredentials:
    _ensure_dotenv_loaded()
    resolved_profile: str = profile or os.environ.get("OCTOPUS_PROFILE", "default") or "default"

    api_key = _read(resolved_profile, "api_key", "OCTOPUS_API_KEY")
    account_number = _read(resolved_profile, "account_number", "OCTOPUS_ACCOUNT_NUMBER")
    email = _read(resolved_profile, "email", "OCTOPUS_EMAIL")
    password = _read(resolved_profile, "password", "OCTOPUS_PASSWORD")

    missing = [
        name
        for name, val in [
            ("OCTOPUS_API_KEY", api_key),
            ("OCTOPUS_ACCOUNT_NUMBER", account_number),
        ]
        if not val
    ]
    if missing:
        raise ConfigError(
            f"Missing required credentials: {', '.join(missing)}. " "Run: octopus-mcp configure"
        )

    # After the missing guard, both are non-None. Assert to narrow for mypy
    # without the type: ignore lie.
    assert api_key is not None
    assert account_number is not None
    return OctopusCredentials(
        api_key=api_key,
        account_number=account_number,
        profile=resolved_profile,
        email=email,
        password=password,
    )

from unittest.mock import patch

import pytest

from octopus_mcp.octopus.auth import OctopusCredentials, resolve_credentials
from octopus_mcp.octopus.errors import ConfigError


def test_env_vars_take_precedence(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OCTOPUS_API_KEY", "sk_test_env")
    monkeypatch.setenv("OCTOPUS_ACCOUNT_NUMBER", "A-ENV")
    creds = resolve_credentials()
    assert creds.api_key == "sk_test_env"
    assert creds.account_number == "A-ENV"


def test_optional_email_and_password_loaded(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OCTOPUS_API_KEY", "k")
    monkeypatch.setenv("OCTOPUS_ACCOUNT_NUMBER", "A-1")
    monkeypatch.setenv("OCTOPUS_EMAIL", "x@y.z")
    monkeypatch.setenv("OCTOPUS_PASSWORD", "secret")
    creds = resolve_credentials()
    assert creds.email == "x@y.z"
    assert creds.password == "secret"


def test_missing_creds_raises_config_error(monkeypatch: pytest.MonkeyPatch) -> None:
    for v in ("OCTOPUS_API_KEY", "OCTOPUS_ACCOUNT_NUMBER", "OCTOPUS_EMAIL", "OCTOPUS_PASSWORD"):
        monkeypatch.delenv(v, raising=False)
    with patch("octopus_mcp.octopus.auth._keyring_get", return_value=None):
        with pytest.raises(ConfigError) as exc:
            resolve_credentials()
        assert "octopus-mcp configure" in str(exc.value)


def test_keyring_used_when_env_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OCTOPUS_API_KEY", raising=False)
    monkeypatch.delenv("OCTOPUS_ACCOUNT_NUMBER", raising=False)

    def fake_get(profile: str, key: str) -> str | None:
        return {"api_key": "sk_test_kr", "account_number": "A-KR"}.get(key)

    with patch("octopus_mcp.octopus.auth._keyring_get", side_effect=fake_get):
        creds = resolve_credentials()
        assert creds.api_key == "sk_test_kr"
        assert creds.account_number == "A-KR"


def test_repr_redacts_secrets() -> None:
    c = OctopusCredentials(
        api_key="sk_secret",
        account_number="A-1",
        email="x@y.z",
        password="hunter2",
        profile="default",
    )
    rendered = repr(c)
    assert "sk_secret" not in rendered
    assert "hunter2" not in rendered
    assert "A-1" not in rendered
    assert "default" in rendered  # non-secret OK

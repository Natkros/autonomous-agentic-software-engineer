import pytest

from core.config.secrets import EnvSecretsProvider, SecretNotFoundError, get_default_secrets_provider


def test_get_reads_a_real_environment_variable(monkeypatch):
    monkeypatch.setenv("FORGEAI_TEST_SECRET", "value123")
    provider = EnvSecretsProvider()
    assert provider.get("FORGEAI_TEST_SECRET") == "value123"


def test_get_returns_default_when_unset(monkeypatch):
    monkeypatch.delenv("FORGEAI_TEST_SECRET_MISSING", raising=False)
    provider = EnvSecretsProvider()
    assert provider.get("FORGEAI_TEST_SECRET_MISSING", default="fallback") == "fallback"


def test_get_returns_none_when_unset_and_no_default(monkeypatch):
    monkeypatch.delenv("FORGEAI_TEST_SECRET_MISSING", raising=False)
    provider = EnvSecretsProvider()
    assert provider.get("FORGEAI_TEST_SECRET_MISSING") is None


def test_require_raises_when_missing(monkeypatch):
    monkeypatch.delenv("FORGEAI_TEST_SECRET_MISSING", raising=False)
    provider = EnvSecretsProvider()
    with pytest.raises(SecretNotFoundError):
        provider.require("FORGEAI_TEST_SECRET_MISSING")


def test_require_returns_value_when_present(monkeypatch):
    monkeypatch.setenv("FORGEAI_TEST_SECRET", "value123")
    provider = EnvSecretsProvider()
    assert provider.require("FORGEAI_TEST_SECRET") == "value123"


def test_default_provider_is_env_backed():
    assert isinstance(get_default_secrets_provider(), EnvSecretsProvider)

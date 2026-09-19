"""Secrets management (spec section 10's "Secrets management" line item).

Every phase so far has read credentials (`JWT_SECRET`, `ANTHROPIC_API_KEY`,
`GITHUB_TOKEN`, `DATABASE_URL`, ...) directly from environment variables —
real, and the correct approach for a 12-factor app, but scattered ad hoc
across `apps/api/app/config.py` and each provider's own `os.environ.get(...)`
call. `SecretsProvider` gives that pattern one small, explicit interface
so a real secrets backend (Vault, AWS Secrets Manager, etc.) could be
swapped in later by implementing the same three methods — deliberately
NOT attempted here: this project has no credentials or reachable service
for any such backend in this environment, and stubbing one out with no
way to even structurally verify it would be worse than not claiming it at
all. `EnvSecretsProvider` — reading from `os.environ`, exactly what every
earlier phase already did — is the only implementation, and it is real,
not a placeholder.
"""
from __future__ import annotations

import os
from abc import ABC, abstractmethod


class SecretNotFoundError(KeyError):
    pass


class SecretsProvider(ABC):
    @abstractmethod
    def get(self, key: str, default: str | None = None) -> str | None:
        """Return the secret's value, or `default` if it isn't set."""

    def require(self, key: str) -> str:
        """Like `get`, but raises if the secret is missing — for values
        with no safe default (e.g. a signing key), so a missing secret
        fails loudly at the point of use rather than silently as `None`.
        """
        value = self.get(key)
        if value is None:
            raise SecretNotFoundError(f"Required secret '{key}' is not set")
        return value


class EnvSecretsProvider(SecretsProvider):
    """Reads from `os.environ` — the real backend every phase of this
    project has always used, now behind an explicit, swappable interface.
    """

    def get(self, key: str, default: str | None = None) -> str | None:
        return os.environ.get(key, default)


def get_default_secrets_provider() -> SecretsProvider:
    return EnvSecretsProvider()

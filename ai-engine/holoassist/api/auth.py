"""Two local development credentials; not a production identity provider."""

import hashlib
import hmac
from dataclasses import dataclass


@dataclass(frozen=True)
class Principal:
    identity: str
    role: str


class LocalCredentials:
    """Bind opaque bearer credentials to server-owned identities and roles."""

    def __init__(self, operator_token: str, reviewer_token: str):
        tokens = (operator_token, reviewer_token)
        if any(len(t) < 64 or not t.isascii() or any(c.isspace() for c in t) for t in tokens):
            raise ValueError("invalid_local_api_credentials")
        if hmac.compare_digest(*tokens):
            raise ValueError("distinct_local_api_credentials_required")
        self._entries = tuple(
            (hashlib.sha256(token.encode()).digest(), Principal(identity, role))
            for token, identity, role in (
                (operator_token, "local-api-operator", "operator"),
                (reviewer_token, "local-api-reviewer", "reviewer"),
            )
        )

    def authenticate(self, token: str) -> Principal | None:
        digest = hashlib.sha256(token.encode()).digest()
        result = None
        for expected, principal in self._entries:
            if hmac.compare_digest(digest, expected):
                result = principal
        return result

"""Backend configuration and PostgreSQL error redaction, without a running server."""

from unittest.mock import patch

import pytest
from holoassist.safety.approvals import ApprovalError
from holoassist.safety.storage import approval_store


def test_default_backend_is_sqlite(monkeypatch):
    monkeypatch.delenv("HOLOASSIST_APPROVAL_BACKEND", raising=False)
    with patch("holoassist.safety.storage.ApprovalStore") as backend:
        approval_store("ignored.sqlite3", authorized_reviewers=("reviewer",))
    backend.assert_called_once_with("ignored.sqlite3", authorized_reviewers=("reviewer",))


def test_unknown_backend_never_silently_falls_back(monkeypatch):
    monkeypatch.setenv("HOLOASSIST_APPROVAL_BACKEND", "invalid")
    with pytest.raises(ApprovalError, match="unknown_approval_backend"):
        approval_store("unused.sqlite3")


def test_missing_postgres_password_is_rejected(monkeypatch):
    monkeypatch.setenv("HOLOASSIST_APPROVAL_BACKEND", "postgres")
    monkeypatch.delenv("HOLOASSIST_POSTGRES_PASSWORD", raising=False)
    with pytest.raises(ApprovalError, match="postgres_password_required"):
        approval_store("unused.sqlite3")


def test_postgres_driver_error_is_redacted():
    psycopg = pytest.importorskip("psycopg")
    from holoassist.safety.postgres import PostgresApprovalStore

    with patch("psycopg.connect", side_effect=psycopg.OperationalError("private-password-value")):
        with pytest.raises(ApprovalError) as error:
            PostgresApprovalStore("")
    assert str(error.value) == "postgres_storage_unavailable"
    assert "private-password" not in str(error.value)


@pytest.mark.parametrize("port", ["invalid", "0", "65536"])
def test_bad_postgres_port_is_rejected(port):
    from holoassist.safety.postgres import PostgresApprovalStore

    with pytest.raises(ApprovalError, match="postgres_port_invalid"):
        PostgresApprovalStore.from_environment(
            {"HOLOASSIST_POSTGRES_PASSWORD": "test-only", "HOLOASSIST_POSTGRES_PORT": port}
        )

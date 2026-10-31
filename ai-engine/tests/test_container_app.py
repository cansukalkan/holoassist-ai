"""Container configuration accepts only environment-backed PostgreSQL."""

import pytest
from fastapi.testclient import TestClient
from holoassist.api.app import container_app
from holoassist.safety import storage
from holoassist.safety.approvals import ApprovalStore


def test_container_never_falls_back_to_sqlite(monkeypatch):
    monkeypatch.setenv("HOLOASSIST_APPROVAL_BACKEND", "sqlite")
    with pytest.raises(ValueError, match="container_requires_postgres"):
        container_app()


def test_container_uses_no_env_file_and_server_reviewer(tmp_path, monkeypatch):
    monkeypatch.setenv("HOLOASSIST_APPROVAL_BACKEND", "postgres")
    monkeypatch.setenv("HOLOASSIST_API_OPERATOR_TOKEN", "o" * 64)
    monkeypatch.setenv("HOLOASSIST_API_REVIEWER_TOKEN", "r" * 64)
    captured = {}

    def fake_store(path, *, authorized_reviewers, env_file):
        captured.update(env_file=env_file, reviewers=authorized_reviewers)
        return ApprovalStore(tmp_path / "reviews.db", authorized_reviewers=authorized_reviewers)

    monkeypatch.setattr(storage, "approval_store", fake_store)
    with TestClient(container_app()) as client:
        assert client.get("/ready").json()["storage"] == "reachable"
        assert client.get("/demo").status_code == 200
    assert captured == {"env_file": None, "reviewers": ("local-api-reviewer",)}


def test_container_missing_credentials_does_not_initialize_storage(monkeypatch):
    monkeypatch.setenv("HOLOASSIST_APPROVAL_BACKEND", "postgres")
    monkeypatch.delenv("HOLOASSIST_API_OPERATOR_TOKEN", raising=False)
    monkeypatch.delenv("HOLOASSIST_API_REVIEWER_TOKEN", raising=False)

    def forbidden(*args, **kwargs):
        raise AssertionError("storage must not open before credentials are validated")

    monkeypatch.setattr(storage, "approval_store", forbidden)
    with pytest.raises(ValueError, match="invalid_local_api_credentials"):
        container_app()

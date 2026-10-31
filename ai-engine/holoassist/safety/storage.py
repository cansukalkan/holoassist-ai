"""Explicit backend selection; a failed PostgreSQL connection never falls back to SQLite."""

import os
from collections.abc import Collection
from pathlib import Path

from holoassist.safety.approvals import ApprovalError, ApprovalStore


def approval_store(
    path: str | Path,
    *,
    authorized_reviewers: Collection[str] = (),
    env_file: str | Path | None = None,
):
    environment = dict(os.environ)
    if env_file is not None:
        from dotenv import dotenv_values

        if not Path(env_file).is_file():
            raise ApprovalError("environment_file_not_found")
        environment = {**dotenv_values(env_file), **environment}
    backend = environment.get("HOLOASSIST_APPROVAL_BACKEND", "sqlite")
    if backend == "sqlite":
        return ApprovalStore(path, authorized_reviewers=authorized_reviewers)
    if backend == "postgres":
        from holoassist.safety.postgres import PostgresApprovalStore

        return PostgresApprovalStore.from_environment(
            environment, authorized_reviewers=authorized_reviewers
        )
    raise ApprovalError("unknown_approval_backend")

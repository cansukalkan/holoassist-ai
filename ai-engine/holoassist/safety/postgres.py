"""PostgreSQL persistence for the existing synthetic approval lifecycle."""

import os
from collections.abc import Callable, Collection, Mapping
from contextlib import contextmanager
from datetime import UTC, datetime

from holoassist.safety.approvals import ApprovalError, ApprovalStore

LOCK_KEY = 734841210


class _PostgresConnection:
    """Adapt fixed internal qmark SQL to Psycopg parameter placeholders.

    The shared lifecycle only issues static SQL. User values stay in the separate
    parameters tuple; this helper is not a general SQL parser or public query API.
    """

    def __init__(self, connection):
        self.connection = connection

    def execute(self, query, parameters=()):
        return self.connection.execute(query.replace("?", "%s"), parameters)


class PostgresApprovalStore(ApprovalStore):
    """Reuse lifecycle rules, swapping only storage and transaction primitives.

    A transaction advisory lock serializes this small approval store across workers,
    preserving the SQLite prototype's read/modify/write semantics. Not a pool or
    high-throughput design. No automatic import or deletion of SQLite records.
    """

    def __init__(
        self,
        conninfo: str = "",
        *,
        authorized_reviewers: Collection[str] = (),
        clock: Callable[[], datetime] | None = None,
        **connection_parameters,
    ):
        if isinstance(authorized_reviewers, str) or any(
            not isinstance(x, str) or not x.strip() for x in authorized_reviewers
        ):
            raise ValueError("reviewer allowlist must contain nonblank identities")
        self.reviewers = frozenset(authorized_reviewers)
        self.clock = clock or (lambda: datetime.now(UTC))
        self._conninfo = conninfo
        self._connection_parameters = connection_parameters
        with self._transaction() as con:
            con.execute("""CREATE TABLE IF NOT EXISTS approvals (
                approval_id TEXT PRIMARY KEY, review_id TEXT NOT NULL UNIQUE,
                record_json TEXT NOT NULL, snapshot_json TEXT NOT NULL)""")
            con.execute("""CREATE TABLE IF NOT EXISTS approval_events (
                seq BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                approval_id TEXT NOT NULL REFERENCES approvals(approval_id),
                event TEXT NOT NULL, at_utc TEXT NOT NULL, actor TEXT)""")

    @classmethod
    def from_environment(cls, environment: Mapping[str, str] | None = None, **options):
        env = os.environ if environment is None else environment
        password = env.get("HOLOASSIST_POSTGRES_PASSWORD", "")
        if not password:
            raise ApprovalError("postgres_password_required")
        try:
            port = int(env.get("HOLOASSIST_POSTGRES_PORT", "5433"))
            if not 1 <= port <= 65535:
                raise ValueError
        except (TypeError, ValueError):
            raise ApprovalError("postgres_port_invalid") from None
        return cls(
            host=env.get("HOLOASSIST_POSTGRES_HOST", "127.0.0.1"),
            port=port,
            dbname=env.get("HOLOASSIST_POSTGRES_DATABASE", "holoassist"),
            user=env.get("HOLOASSIST_POSTGRES_USER", "holoassist"),
            password=password,
            **options,
        )

    @contextmanager
    def _transaction(self):
        try:
            import psycopg
            from psycopg.rows import dict_row
        except ImportError:
            raise ApprovalError("install_postgres_extra") from None
        try:
            with psycopg.connect(
                self._conninfo,
                **self._connection_parameters,
                connect_timeout=5,
                autocommit=True,
                row_factory=dict_row,
            ) as con:
                with con.transaction():
                    con.execute("SET LOCAL lock_timeout = '5s'")
                    con.execute("SET LOCAL statement_timeout = '10s'")
                    con.execute("SELECT pg_advisory_xact_lock(%s)", (LOCK_KEY,))
                    yield _PostgresConnection(con)
        except psycopg.Error:
            # Driver diagnostics can contain connection details. Keep them out of CLI/log output.
            raise ApprovalError("postgres_storage_unavailable") from None

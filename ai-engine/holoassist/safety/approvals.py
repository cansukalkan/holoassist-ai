"""SQLite-backed synthetic review/checkpoint lifecycle with atomic one-time use."""

import json
import sqlite3
from collections.abc import Callable, Collection
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from holoassist.contracts.approval import ApprovalRecord, DemoResumeReceipt
from holoassist.safety.gate import evaluate_plan


class ApprovalError(ValueError):
    """Sanitized lifecycle failure; never includes snapshot content."""


def canonical(value) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


class ApprovalStore:
    """Local demo backend; authenticated reviewer identities must come from a trusted caller.

    The allowlist is authorization policy, not a production identity provider.
    No method enables physical guidance or resumes a LangGraph execution.
    """

    def __init__(
        self,
        path: str | Path,
        *,
        authorized_reviewers: Collection[str] = (),
        clock: Callable[[], datetime] | None = None,
    ):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(authorized_reviewers, str) or any(
            not isinstance(x, str) or not x.strip() for x in authorized_reviewers
        ):
            raise ValueError("reviewer allowlist must contain nonblank identities")
        self.reviewers = frozenset(authorized_reviewers)
        self.clock = clock or (lambda: datetime.now(UTC))
        with self._transaction() as con:
            con.execute("""CREATE TABLE IF NOT EXISTS approvals (
                approval_id TEXT PRIMARY KEY, review_id TEXT NOT NULL UNIQUE,
                record_json TEXT NOT NULL, snapshot_json TEXT NOT NULL)""")
            con.execute("""CREATE TABLE IF NOT EXISTS approval_events (
                seq INTEGER PRIMARY KEY AUTOINCREMENT, approval_id TEXT NOT NULL,
                event TEXT NOT NULL, at_utc TEXT NOT NULL, actor TEXT,
                FOREIGN KEY(approval_id) REFERENCES approvals(approval_id))""")

    @contextmanager
    def _transaction(self):
        con = sqlite3.connect(self.path, timeout=5, isolation_level=None)
        con.row_factory = sqlite3.Row
        try:
            con.execute("PRAGMA foreign_keys=ON")
            con.execute("BEGIN IMMEDIATE")
            yield con
            con.commit()
        except BaseException:
            con.rollback()
            raise
        finally:
            con.close()

    def _now(self) -> datetime:
        now = self.clock()
        if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
            raise ApprovalError("invalid_server_clock")
        return now.astimezone(UTC)

    @staticmethod
    def _read(con, approval_id):
        row = con.execute("SELECT * FROM approvals WHERE approval_id=?", (approval_id,)).fetchone()
        if row is None:
            raise ApprovalError("approval_not_found")
        return ApprovalRecord.model_validate_json(row["record_json"]), json.loads(
            row["snapshot_json"]
        )

    @staticmethod
    def _event(con, approval_id, event, now, actor=None):
        con.execute(
            "INSERT INTO approval_events(approval_id,event,at_utc,actor) VALUES(?,?,?,?)",
            (approval_id, event, now.isoformat(), actor),
        )

    def _change(self, con, record, now, status, reason, **changes):
        updated = ApprovalRecord.model_validate(
            record.model_dump() | dict(status=status, updated_utc=now, reason_code=reason) | changes
        )
        con.execute(
            "UPDATE approvals SET record_json=? WHERE approval_id=?",
            (updated.model_dump_json(), record.approval_id),
        )
        self._event(con, record.approval_id, reason, now, changes.get("decided_by"))
        return updated

    def _expire(self, con, record, now):
        if now < record.updated_utc:
            raise ApprovalError("server_clock_regressed")
        if record.status in ("pending", "approved") and now >= record.expires_utc:
            return self._change(con, record, now, "expired", "approval_expired")
        return record

    @staticmethod
    def _snapshot(analysis, selection, catalog):
        def plain(item):
            return item.model_dump(mode="json") if hasattr(item, "model_dump") else item

        snapshot = dict(analysis=plain(analysis), request=plain(selection), catalog=plain(catalog))
        report = evaluate_plan(snapshot["analysis"], snapshot["request"], snapshot["catalog"])
        if report.status != "needs_approval":
            raise ApprovalError("plan_not_eligible_for_approval")
        # Validate and normalize before persistence using the same contracts as the gate.
        from holoassist.contracts.analysis import AnalysisState
        from holoassist.contracts.safety import InstructionCatalog, SafetyRequest

        snapshot = dict(
            analysis=AnalysisState.model_validate(snapshot["analysis"]).model_dump(mode="json"),
            request=SafetyRequest.model_validate(snapshot["request"]).model_dump(mode="json"),
            catalog=InstructionCatalog.model_validate(snapshot["catalog"]).model_dump(mode="json"),
        )
        return snapshot, report

    def open_review(
        self, analysis, selection, catalog, *, ttl_seconds: int = 900
    ) -> ApprovalRecord:
        if type(ttl_seconds) is not int or not 1 <= ttl_seconds <= 3600:
            raise ApprovalError("invalid_approval_ttl")
        snapshot, report = self._snapshot(analysis, selection, catalog)
        with self._transaction() as con:
            now = self._now()
            row = con.execute(
                "SELECT approval_id FROM approvals WHERE review_id=?", (report.review_id,)
            ).fetchone()
            if row:
                record, _ = self._read(con, row["approval_id"])
                if record.context_digest != report.context_digest:
                    raise ApprovalError("review_id_context_conflict")
                return self._expire(con, record, now)
            record = ApprovalRecord(
                approval_id=str(uuid4()),
                review_id=report.review_id,
                analysis_request_id=report.analysis_request_id,
                context_digest=report.context_digest,
                status="pending",
                created_utc=now,
                updated_utc=now,
                expires_utc=now + timedelta(seconds=ttl_seconds),
                reason_code="review_created",
            )
            con.execute(
                "INSERT INTO approvals VALUES(?,?,?,?)",
                (
                    record.approval_id,
                    record.review_id,
                    record.model_dump_json(),
                    canonical(snapshot),
                ),
            )
            self._event(con, record.approval_id, "review_created", now)
            return record

    def get(self, approval_id: str) -> ApprovalRecord:
        with self._transaction() as con:
            record, _ = self._read(con, approval_id)
            return self._expire(con, record, self._now())

    def check_ready(self) -> None:
        """Verify access to both persistent tables without changing review state."""
        with self._transaction() as con:
            con.execute("SELECT approval_id FROM approvals LIMIT 1").fetchone()
            con.execute("SELECT approval_id FROM approval_events LIMIT 1").fetchone()

    def decide(
        self,
        approval_id: str,
        *,
        authenticated_reviewer: str,
        decision: str,
        expected_context_digest: str,
    ) -> ApprovalRecord:
        if authenticated_reviewer not in self.reviewers:
            raise ApprovalError("reviewer_not_authorized")
        if decision not in ("approve", "reject"):
            raise ApprovalError("invalid_review_decision")
        error = None
        with self._transaction() as con:
            record, snapshot = self._read(con, approval_id)
            now = self._now()
            record = self._expire(con, record, now)
            if expected_context_digest != record.context_digest:
                error = "review_context_mismatch"
            elif record.status != "pending":
                error = "approval_not_pending"
            else:
                try:
                    _, report = self._snapshot(
                        snapshot["analysis"], snapshot["request"], snapshot["catalog"]
                    )
                    valid = report.context_digest == record.context_digest
                except (ValueError, TypeError, KeyError):
                    valid = False
                if not valid:
                    record = self._change(con, record, now, "invalidated", "checkpoint_invalid")
                    error = "checkpoint_invalid"
                else:
                    record = self._change(
                        con,
                        record,
                        now,
                        "approved" if decision == "approve" else "rejected",
                        "review_approved" if decision == "approve" else "review_rejected",
                        decided_by=authenticated_reviewer,
                        decided_utc=now,
                    )
        if error:
            raise ApprovalError(error)
        return record

    def resume_demo(self, approval_id: str, analysis, selection, catalog) -> DemoResumeReceipt:
        error = None
        receipt = None
        with self._transaction() as con:
            record, snapshot = self._read(con, approval_id)
            now = self._now()
            record = self._expire(con, record, now)
            if record.status != "approved":
                error = "approval_not_approved"
            else:
                try:
                    _, stored_report = self._snapshot(
                        snapshot["analysis"], snapshot["request"], snapshot["catalog"]
                    )
                    _, current_report = self._snapshot(analysis, selection, catalog)
                    valid = (
                        stored_report.context_digest
                        == current_report.context_digest
                        == record.context_digest
                    )
                except (ValueError, TypeError, KeyError):
                    valid = False
                if not valid:
                    self._change(
                        con, record, now, "invalidated", "context_changed_or_gate_rejected"
                    )
                    error = "context_changed_or_gate_rejected"
                elif record.decided_by not in self.reviewers:
                    self._change(con, record, now, "invalidated", "reviewer_authorization_revoked")
                    error = "reviewer_authorization_revoked"
                else:
                    self._change(
                        con, record, now, "consumed", "demo_continuation_recorded", consumed_utc=now
                    )
                    receipt = DemoResumeReceipt(
                        approval_id=record.approval_id,
                        context_digest=record.context_digest,
                        consumed_utc=now,
                    )
        if error:
            raise ApprovalError(error)
        return receipt

    def audit(self, approval_id: str) -> tuple[dict, ...]:
        with self._transaction() as con:
            self._read(con, approval_id)
            rows = con.execute(
                "SELECT seq,event,at_utc,actor FROM approval_events "
                "WHERE approval_id=? ORDER BY seq",
                (approval_id,),
            ).fetchall()
            return tuple(dict(row) for row in rows)

    def review_context(self, approval_id: str, *, authenticated_reviewer: str) -> dict:
        if authenticated_reviewer not in self.reviewers:
            raise ApprovalError("reviewer_not_authorized")
        with self._transaction() as con:
            record, snapshot = self._read(con, approval_id)
            record = self._expire(con, record, self._now())
            return {"record": record.model_dump(mode="json"), "snapshot": snapshot}

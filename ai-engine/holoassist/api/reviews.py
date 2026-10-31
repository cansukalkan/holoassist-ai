"""Authenticated local synthetic reviews; no physical execution or HTTP resume."""

import sqlite3
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import Field

from holoassist.api.auth import LocalCredentials, Principal
from holoassist.contracts.analysis import AnalysisState
from holoassist.contracts.approval import ApprovalRecord
from holoassist.contracts.models import Checksum, Contract
from holoassist.contracts.safety import InstructionCatalog, SafetyRequest
from holoassist.safety.approvals import ApprovalError, ApprovalStore


class OpenReview(Contract):
    selection: SafetyRequest
    ttl_seconds: Annotated[int, Field(strict=True, ge=1, le=3600)] = 900


class ReviewDecision(Contract):
    decision: Literal["approve", "reject"]
    expected_context_digest: Checksum


class Snapshot(Contract):
    analysis: AnalysisState
    request: SafetyRequest
    catalog: InstructionCatalog


class ReviewContext(Contract):
    record: ApprovalRecord
    snapshot: Snapshot


def review_router(store: ApprovalStore, credentials: LocalCredentials, state_json, catalog_json):
    router = APIRouter(prefix="/v1/demo/reviews", tags=["local synthetic reviews"])
    bearer = HTTPBearer(auto_error=False)

    def require(*roles):
        def authenticate(
            auth: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
        ) -> Principal:
            principal = credentials.authenticate(auth.credentials) if auth else None
            if principal is None:
                raise HTTPException(
                    401, "authentication_required", headers={"WWW-Authenticate": "Bearer"}
                )
            if principal.role not in roles:
                raise HTTPException(403, "role_not_authorized")
            return principal

        return authenticate

    operator = require("operator")
    reviewer = require("reviewer")
    reader = require("operator", "reviewer")

    def call(operation):
        try:
            return operation()
        except ApprovalError as error:
            code = str(error)
            if code == "approval_not_found":
                raise HTTPException(404, "review_not_found") from None
            if code == "reviewer_not_authorized":
                raise HTTPException(403, "role_not_authorized") from None
            if code == "postgres_storage_unavailable":
                raise HTTPException(503, "storage_unavailable") from None
            raise HTTPException(409, "review_state_conflict") from None
        except (sqlite3.Error, OSError):
            raise HTTPException(503, "storage_unavailable") from None

    @router.post("", response_model=ApprovalRecord, dependencies=[Depends(operator)])
    def open_review(body: OpenReview):
        return call(
            lambda: store.open_review(
                AnalysisState.model_validate_json(state_json),
                body.selection,
                InstructionCatalog.model_validate_json(catalog_json),
                ttl_seconds=body.ttl_seconds,
            )
        )

    @router.get("/{approval_id}", response_model=ApprovalRecord, dependencies=[Depends(reader)])
    def get_review(approval_id: UUID):
        return call(lambda: store.get(str(approval_id)))

    @router.get("/{approval_id}/context", response_model=ReviewContext)
    def context(approval_id: UUID, principal: Annotated[Principal, Depends(reviewer)]):
        return call(
            lambda: store.review_context(
                str(approval_id),
                authenticated_reviewer=principal.identity,
            )
        )

    @router.post("/{approval_id}/decision", response_model=ApprovalRecord)
    def decide(
        approval_id: UUID,
        body: ReviewDecision,
        principal: Annotated[Principal, Depends(reviewer)],
    ):
        return call(
            lambda: store.decide(
                str(approval_id),
                authenticated_reviewer=principal.identity,
                decision=body.decision,
                expected_context_digest=body.expected_context_digest,
            )
        )

    return router

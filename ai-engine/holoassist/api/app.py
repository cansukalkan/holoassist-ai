"""Local synthetic evaluation and optional authenticated persistent reviews."""

import os
import sqlite3
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException

from holoassist.api.auth import LocalCredentials
from holoassist.api.diagnostic import router as diagnostic_router
from holoassist.api.evaluation import router as evaluation_router
from holoassist.api.export import export_router
from holoassist.api.limits import BodyLimitMiddleware
from holoassist.api.sensors import router as sensor_router
from holoassist.api.spatial import spatial_router
from holoassist.api.vision import router as vision_router
from holoassist.contracts.analysis import AnalysisState
from holoassist.contracts.models import Contract
from holoassist.contracts.safety import InstructionCatalog, SafetyReport, SafetyRequest
from holoassist.safety.approvals import ApprovalError, ApprovalStore
from holoassist.safety.gate import evaluate_plan


class Health(Contract):
    status: Literal["ok"] = "ok"
    scope: Literal["synthetic_demo"] = "synthetic_demo"
    guidance_allowed: Literal[False] = False


class ApiError(Contract):
    code: str


class _NoCacheStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        response = await super().get_response(path, scope)
        if response.status_code == 200:
            response.headers["Cache-Control"] = "no-store"
        return response


class Readiness(Contract):
    status: Literal["ready"] = "ready"
    scope: Literal["synthetic_demo"] = "synthetic_demo"
    storage: Literal["not_configured", "reachable"]
    guidance_allowed: Literal[False] = False


def create_app(
    analysis: AnalysisState,
    catalog: InstructionCatalog,
    *,
    store: ApprovalStore | None = None,
    credentials: LocalCredentials | None = None,
) -> FastAPI:
    if (store is None) != (credentials is None):
        raise ValueError("store_and_credentials_required_together")
    # Copy and validate at the trusted server boundary. No client-supplied evidence.
    state_json = AnalysisState.model_validate(analysis).model_dump_json()
    catalog_json = InstructionCatalog.model_validate(catalog).model_dump_json()
    if analysis.request.mode != "demo" or catalog.scope != "synthetic_demo":
        raise ValueError("synthetic_context_required")
    app = FastAPI(
        title="HoloAssist synthetic demo API",
        version="0.1.0",
        responses={code: {"model": ApiError} for code in (400, 401, 403, 404, 409, 413, 422, 503)},
    )
    app.add_middleware(BodyLimitMiddleware)
    app.include_router(vision_router)
    app.include_router(sensor_router)
    app.include_router(diagnostic_router)
    app.include_router(spatial_router(state_json, catalog_json))
    app.include_router(evaluation_router)
    app.include_router(export_router(state_json, catalog_json))
    static_directory = Path(__file__).parent / "static"
    app.mount("/demo/assets", _NoCacheStaticFiles(directory=static_directory), name="demo-assets")

    def _html_page(filename: str) -> FileResponse:
        return FileResponse(
            static_directory / filename,
            headers={
                "Cache-Control": "no-store",
                "Content-Security-Policy": (
                    "default-src 'self'; script-src 'self'; style-src 'self'; "
                    "img-src 'self'; connect-src 'self'; object-src 'none'; "
                    "base-uri 'none'; frame-ancestors 'none'; form-action 'none'"
                ),
                "X-Content-Type-Options": "nosniff",
                "Referrer-Policy": "no-referrer",
            },
        )

    @app.get("/", include_in_schema=False)
    def site():
        return _html_page("site.html")

    @app.get("/demo", include_in_schema=False)
    def demo():
        return _html_page("index.html")

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, error: HTTPException):
        return JSONResponse(
            status_code=error.status_code,
            content=ApiError(
                code=error.detail if isinstance(error.detail, str) else "http_error"
            ).model_dump(),
            headers=error.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request: Request, error: RequestValidationError):
        # Do not echo supplied values, document text, or validation internals.
        return JSONResponse(status_code=422, content=ApiError(code="invalid_request").model_dump())

    @app.get("/health", response_model=Health)
    def health():
        return Health()

    @app.get("/ready", response_model=Readiness)
    def ready():
        if store is not None:
            try:
                store.check_ready()
            except (ApprovalError, sqlite3.Error, OSError):
                raise HTTPException(503, "storage_unavailable") from None
        return Readiness(storage="reachable" if store is not None else "not_configured")

    @app.post("/v1/demo/safety/evaluate", response_model=SafetyReport)
    def evaluate(selection: SafetyRequest):
        return evaluate_plan(
            AnalysisState.model_validate_json(state_json),
            selection,
            InstructionCatalog.model_validate_json(catalog_json),
        )

    if store is not None:
        from holoassist.api.reviews import review_router

        app.include_router(review_router(store, credentials, state_json, catalog_json))
    return app


def local_app() -> FastAPI:
    """Uvicorn factory; start from repository root with trusted local fixtures."""
    return create_app(
        AnalysisState.model_validate_json(Path("docs/examples/safety-analysis.json").read_bytes()),
        InstructionCatalog.model_validate_json(
            Path("datasets/fixtures/instruction-catalog.json").read_bytes()
        ),
    )


def local_review_app() -> FastAPI:
    """Explicit opt-in local review server; credential failures stop startup."""
    return configured_review_app(".env")


def container_app() -> FastAPI:
    """Environment-only PostgreSQL configuration; never create ephemeral SQLite data."""
    if os.environ.get("HOLOASSIST_APPROVAL_BACKEND") != "postgres":
        raise ValueError("container_requires_postgres")
    return configured_review_app(None)


def configured_review_app(env_file: str | None) -> FastAPI:
    from dotenv import dotenv_values

    from holoassist.safety.storage import approval_store

    environment = {**(dotenv_values(env_file) if env_file is not None else {}), **os.environ}
    credentials = LocalCredentials(
        environment.get("HOLOASSIST_API_OPERATOR_TOKEN", ""),
        environment.get("HOLOASSIST_API_REVIEWER_TOKEN", ""),
    )
    store = approval_store(
        "data/approvals.sqlite3",
        env_file=env_file,
        authorized_reviewers=("local-api-reviewer",),
    )
    return create_app(
        AnalysisState.model_validate_json(Path("docs/examples/safety-analysis.json").read_bytes()),
        InstructionCatalog.model_validate_json(
            Path("datasets/fixtures/instruction-catalog.json").read_bytes()
        ),
        store=store,
        credentials=credentials,
    )

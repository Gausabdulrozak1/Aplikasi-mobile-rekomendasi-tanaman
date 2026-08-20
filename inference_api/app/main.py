from __future__ import annotations

import hmac
import logging
import re
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from inference_api.app.api.routes import create_router
from inference_api.app.core.config import Settings, get_settings
from inference_api.app.core.errors import ApiError
from inference_api.app.services.generation_service import GenerationService

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("taniadaptif.inference")


def _safe_request_id(value: str | None) -> str:
    if value and len(value) <= 64 and re.fullmatch(r"[A-Za-z0-9._-]+", value):
        return value
    return uuid.uuid4().hex[:16]


def _error_body(
    request: Request,
    *,
    code: str,
    message: str,
    retryable: bool,
    details: object = None,
) -> dict[str, object]:
    error: dict[str, object] = {
        "code": code,
        "message": message,
        "retryable": retryable,
    }
    if details is not None:
        error["details"] = details
    return {
        "success": False,
        "request_id": getattr(request.state, "request_id", "unknown"),
        "error": error,
    }


def create_app(
    settings: Settings | None = None,
    service: GenerationService | None = None,
) -> FastAPI:
    active_settings = settings or get_settings()
    active_settings.generated_dir.mkdir(parents=True, exist_ok=True)
    active_service = service or GenerationService(active_settings)
    app = FastAPI(title=active_settings.app_name, version=active_settings.app_version)

    allow_credentials = active_settings.cors_origin_list != ["*"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=active_settings.cors_origin_list,
        allow_credentials=allow_credentials,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "X-Request-ID", "X-Inference-Token"],
    )

    @app.middleware("http")
    async def request_logging(request: Request, call_next):
        request.state.request_id = _safe_request_id(request.headers.get("X-Request-ID"))
        start = time.perf_counter()
        supplied_token = request.headers.get("X-Inference-Token", "")
        token_valid = bool(active_settings.api_token) and hmac.compare_digest(
            supplied_token,
            active_settings.api_token,
        )
        if active_settings.require_api_token and request.url.path != "/health" and not token_valid:
            response = JSONResponse(
                status_code=401,
                content=_error_body(
                    request,
                    code="INFERENCE_AUTH_REQUIRED",
                    message="Kredensial layanan inference tidak valid.",
                    retryable=False,
                ),
            )
        else:
            response = await call_next(request)
        duration = round(time.perf_counter() - start, 3)
        response.headers["X-Request-ID"] = request.state.request_id
        logger.info(
            "%s %s status=%s duration=%s request_id=%s",
            request.method,
            request.url.path,
            response.status_code,
            duration,
            request.state.request_id,
        )
        return response

    @app.exception_handler(ApiError)
    async def api_error_handler(request: Request, error: ApiError) -> JSONResponse:
        return JSONResponse(
            status_code=error.status_code,
            content=_error_body(
                request,
                code=error.code,
                message=error.message,
                retryable=error.retryable,
                details=error.details,
            ),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, error: RequestValidationError
    ) -> JSONResponse:
        details = [
            {
                "location": [str(item) for item in issue["loc"]],
                "message": issue["msg"],
                "type": issue["type"],
            }
            for issue in error.errors()
        ]
        return JSONResponse(
            status_code=422,
            content=_error_body(
                request,
                code="VALIDATION_ERROR",
                message="Payload permintaan tidak valid.",
                retryable=False,
                details=details,
            ),
        )

    app.mount(
        "/static/generated",
        StaticFiles(directory=active_settings.generated_dir),
        name="generated_images",
    )
    app.include_router(create_router(active_settings, active_service))
    return app


app = create_app()

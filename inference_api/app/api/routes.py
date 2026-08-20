from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi import APIRouter, Request, Response

from inference_api.app.core.config import Settings
from inference_api.app.core.errors import ApiError
from inference_api.app.models.schemas import (
    GenerateRequest,
    GenerateResponse,
    HealthResponse,
    ModelInfoResponse,
    PromptGenerateRequest,
    ReadinessResponse,
)
from inference_api.app.services.generation_service import GenerationService
from inference_api.app.services.prompt_builder import PILOT_TRIGGER_TOKENS, TRIGGER_TOKENS

SUPPORTED_DIMENSIONS = list(range(256, 769, 64))


def create_router(settings: Settings, service: GenerationService) -> APIRouter:
    router = APIRouter()

    @router.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        provider_health = service.health()
        return HealthResponse(
            status="ok",
            provider=str(provider_health["provider"]),
            device=str(provider_health["device"]),
            model_loaded=bool(provider_health["model_loaded"]),
            version=settings.app_version,
        )

    @router.get(
        "/ready",
        response_model=ReadinessResponse,
        responses={503: {"model": ReadinessResponse}},
    )
    async def ready(response: Response) -> ReadinessResponse:
        readiness = service.readiness()
        is_ready = bool(readiness["ready"])
        if not is_ready:
            response.status_code = 503
        return ReadinessResponse(
            status="ready" if is_ready else "not_ready",
            provider=str(readiness["provider"]),
            device=str(readiness["device"]),
            model_loaded=bool(readiness["model_loaded"]),
            reason=str(readiness["reason"]) if readiness.get("reason") else None,
        )

    @router.get("/v1/model-info", response_model=ModelInfoResponse)
    async def model_info() -> ModelInfoResponse:
        return ModelInfoResponse(
            base_model=settings.base_model,
            lora_identifier=settings.lora_identifier,
            provider=settings.provider,
            supported_crops=list(TRIGGER_TOKENS),
            trigger_tokens=TRIGGER_TOKENS,
            pilot_trigger_tokens={crop: token for token, crop in PILOT_TRIGGER_TOKENS.items()},
            supported_request_modes=["structured_context", "direct_prompt"],
            supported_width=SUPPORTED_DIMENSIONS,
            supported_height=SUPPORTED_DIMENSIONS,
            default_parameters={
                "seed": settings.default_seed,
                "steps": 25,
                "guidance_scale": 7.5,
                "width": settings.default_width,
                "height": settings.default_height,
                "max_retries": settings.generation_max_retries,
                "timeout_seconds": settings.generation_timeout_seconds,
            },
        )

    @router.post("/v1/generate", response_model=GenerateResponse)
    async def generate(
        payload: GenerateRequest | PromptGenerateRequest,
        request: Request,
    ) -> GenerateResponse:
        request_id = payload.request_id or request.state.request_id
        request.state.request_id = request_id
        try:
            result = await service.generate(payload, request_id)
        except asyncio.TimeoutError as exc:
            raise ApiError(
                status_code=504,
                code="GENERATION_TIMEOUT",
                message="Waktu pembuatan visual melewati batas layanan.",
                retryable=True,
            ) from exc
        except RuntimeError as exc:
            raise ApiError(
                status_code=503,
                code="GENERATION_FAILED",
                message="Visual tidak dapat dibuat oleh provider saat ini.",
                retryable=True,
                details={"provider": service.provider.provider_name},
            ) from exc

        filename = Path(result.image_path).name
        image_url = str(request.url_for("generated_images", path=filename))
        return GenerateResponse(
            success=True,
            request_id=request_id,
            crop=result.metadata.get("crop"),
            image_url=image_url,
            image_id=result.image_id,
            seed=result.seed,
            generation_time_seconds=result.generation_time_seconds,
            model=result.model,
            metadata=result.metadata,
        )

    return router

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from pathlib import Path

from inference_api.app.core.config import Settings
from inference_api.app.models.schemas import GeneratePayload
from inference_api.app.providers.base import GenerationResult, ImageGenerator
from inference_api.app.providers.diffusers_provider import DiffusersImageGenerator
from inference_api.app.providers.mock import MockImageGenerator
from inference_api.app.services.prompt_builder import prepare_generation_request

logger = logging.getLogger("taniadaptif.inference.service")


def build_provider(settings: Settings) -> ImageGenerator:
    provider = settings.provider.lower()
    if provider == "mock":
        return MockImageGenerator(settings)
    if provider == "diffusers":
        return DiffusersImageGenerator(settings)
    raise RuntimeError(f"Unsupported provider: {settings.provider}")


class GenerationService:
    def __init__(self, settings: Settings, provider: ImageGenerator | None = None) -> None:
        self.settings = settings
        self.provider = provider or build_provider(settings)
        self._generation_lock = asyncio.Lock()
        self._blocked_after_timeout = False

    def health(self) -> dict[str, object]:
        return self.provider.health()

    def readiness(self) -> dict[str, object]:
        health = self.provider.health()
        provider_ready = bool(health.get("model_loaded"))
        return {
            **health,
            "ready": provider_ready and not self._blocked_after_timeout,
            "reason": (
                "Provider timed out; restart is required before another generation."
                if self._blocked_after_timeout
                else health.get("reason")
            ),
        }

    async def generate(
        self,
        request: GeneratePayload,
        request_id: str,
    ) -> GenerationResult:
        if self._blocked_after_timeout:
            raise RuntimeError("Provider is blocked after a timeout and requires restart.")
        prepared = prepare_generation_request(request, default_seed=self.settings.default_seed)
        attempts = self.settings.generation_max_retries + 1
        last_error: RuntimeError | None = None

        async with self._generation_lock:
            for attempt in range(1, attempts + 1):
                try:
                    result = await asyncio.wait_for(
                        asyncio.to_thread(self.provider.generate, prepared, request_id),
                        timeout=self.settings.generation_timeout_seconds,
                    )
                    self._validate_output_path(result.image_path)
                    result.metadata.update(
                        {
                            "base_model": self.settings.base_model,
                            "lora_identifier": self.settings.lora_identifier,
                            "seed": result.seed,
                            "generated_at": datetime.now(UTC).isoformat(),
                            "recommendation_source": prepared.recommendation_source,
                            "request_mode": prepared.request_mode,
                        }
                    )
                    return result
                except asyncio.TimeoutError:
                    self._blocked_after_timeout = True
                    logger.error(
                        "generation timeout provider=%s request_id=%s",
                        self.provider.provider_name,
                        request_id,
                    )
                    raise
                except RuntimeError as exc:
                    last_error = exc
                    logger.warning(
                        "generation failed provider=%s request_id=%s attempt=%s/%s",
                        self.provider.provider_name,
                        request_id,
                        attempt,
                        attempts,
                    )
                    if attempt < attempts:
                        await asyncio.sleep(0.1 * attempt)

        raise last_error or RuntimeError("Image generation failed.")

    def _validate_output_path(self, raw_path: str) -> None:
        output_root = self.settings.generated_dir.resolve()
        path = Path(raw_path).resolve()
        if path.parent != output_root or not path.is_file():
            raise RuntimeError("Provider returned an invalid output artifact.")

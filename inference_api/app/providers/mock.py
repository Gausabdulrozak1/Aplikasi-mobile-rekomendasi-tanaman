from __future__ import annotations

import hashlib
import textwrap
import time
from pathlib import Path

from PIL import Image, ImageDraw

from inference_api.app.core.config import Settings
from inference_api.app.providers.base import GenerationResult, ImageGenerator
from inference_api.app.services.prompt_builder import PreparedGenerationRequest


class MockImageGenerator(ImageGenerator):
    provider_name = "mock"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.output_dir = settings.generated_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def health(self) -> dict[str, object]:
        return {
            "provider": self.provider_name,
            "device": "cpu",
            "model_loaded": True,
            "reason": None,
        }

    def generate(self, request: PreparedGenerationRequest, request_id: str) -> GenerationResult:
        start = time.time()
        image_id = self._image_id(request, request_id)
        image_path = self.output_dir / f"{image_id}.png"
        self._write_placeholder(image_path, request, image_id)
        return GenerationResult(
            image_path=str(image_path),
            image_id=image_id,
            seed=request.seed,
            generation_time_seconds=round(time.time() - start, 3),
            model="mock-placeholder",
            metadata={
                "provider": self.provider_name,
                "request_id": request_id,
                "crop": request.crop,
                "trigger_token": request.trigger_token,
                "prompt": request.prompt,
                "negative_prompt": request.negative_prompt,
                "width": request.width,
                "height": request.height,
                "is_mock": True,
                "research_output": False,
            },
        )

    def _image_id(self, request: PreparedGenerationRequest, request_id: str) -> str:
        digest = hashlib.sha256(
            (
                f"{request_id}|{request.prompt}|{request.seed}|{request.width}x{request.height}"
            ).encode("utf-8")
        ).hexdigest()[:16]
        return f"mock_{digest}"

    def _write_placeholder(
        self,
        image_path: Path,
        request: PreparedGenerationRequest,
        image_id: str,
    ) -> None:
        background = (224, 240, 226)
        foreground = (38, 91, 66)
        accent = (61, 130, 91)
        image = Image.new("RGB", (request.width, request.height), background)
        draw = ImageDraw.Draw(image)
        margin = max(24, request.width // 18)
        draw.rectangle(
            [margin, margin, request.width - margin, request.height - margin],
            outline=foreground,
            width=4,
        )
        draw.rectangle(
            [margin + 12, margin + 12, request.width - margin - 12, margin + 72],
            fill=accent,
        )
        draw.text((margin + 24, margin + 30), "TaniAdaptif Mock Visual", fill="white")

        wrapped = textwrap.wrap(request.prompt, width=42)[:8]
        y = margin + 105
        for line in wrapped:
            draw.text((margin + 24, y), line, fill=foreground)
            y += 24
        draw.text(
            (margin + 24, request.height - margin - 60),
            f"seed={request.seed} id={image_id}",
            fill=foreground,
        )
        image.save(image_path)

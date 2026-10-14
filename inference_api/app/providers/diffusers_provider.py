from __future__ import annotations

import time
from pathlib import Path

from inference_api.app.core.config import Settings
from inference_api.app.providers.base import GenerationResult, ImageGenerator
from inference_api.app.providers.lora_validation import LoraArtifactInfo, validate_lora_artifact
from inference_api.app.services.prompt_builder import PreparedGenerationRequest


class DiffusersImageGenerator(ImageGenerator):
    provider_name = "diffusers"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.output_dir = settings.generated_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.pipe = None
        self.device = "not_loaded"
        self.load_error: str | None = None
        self.lora_artifact: LoraArtifactInfo | None = None
        try:
            self._load_model()
        except Exception as exc:
            self.pipe = None
            self.load_error = str(exc)

    def _load_model(self) -> None:
        self.lora_artifact = validate_lora_artifact(
            self.settings.lora_path,
            self.settings.lora_sha256,
        )
        try:
            import torch
            from diffusers import StableDiffusionPipeline
        except ImportError as exc:
            raise RuntimeError("Diffusers runtime dependencies are not installed.") from exc

        if self.settings.require_gpu and not torch.cuda.is_available():
            raise RuntimeError("GPU is required but CUDA is not available.")

        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        dtype = torch.float16 if self.device == "cuda" else torch.float32
        self.pipe = StableDiffusionPipeline.from_pretrained(
            self.settings.base_model,
            torch_dtype=dtype,
        )
        self.pipe = self.pipe.to(self.device)
        self.pipe.enable_attention_slicing()

        lora_path = Path(self.lora_artifact.path)
        self.pipe.load_lora_weights(
            str(lora_path.parent),
            weight_name=lora_path.name,
        )

    def health(self) -> dict[str, object]:
        return {
            "provider": self.provider_name,
            "device": self.device,
            "model_loaded": self.pipe is not None,
            "lora_validated": self.lora_artifact is not None,
            "lora_sha256": self.lora_artifact.sha256 if self.lora_artifact else None,
            "reason": self.load_error,
        }

    def generate(self, request: PreparedGenerationRequest, request_id: str) -> GenerationResult:
        if self.pipe is None:
            raise RuntimeError(self.load_error or "Model is not loaded.")

        import torch

        start = time.time()
        generator = torch.Generator(device=self.device).manual_seed(request.seed)
        image = self.pipe(
            prompt=request.prompt,
            negative_prompt=request.negative_prompt,
            num_inference_steps=request.steps,
            guidance_scale=request.guidance_scale,
            width=request.width,
            height=request.height,
            generator=generator,
        ).images[0]
        crop_identity = request.crop or "direct"
        image_id = f"sd15_{crop_identity}_{request.seed}_{request_id}"
        image_path = self.output_dir / f"{image_id}.png"
        image.save(image_path, format="PNG")

        return GenerationResult(
            image_path=str(image_path),
            image_id=image_id,
            seed=request.seed,
            generation_time_seconds=round(time.time() - start, 3),
            model=self.settings.base_model,
            metadata={
                "provider": self.provider_name,
                "request_id": request_id,
                "device": self.device,
                "crop": request.crop,
                "trigger_token": request.trigger_token,
                "lora_identifier": self.settings.lora_identifier,
                "lora_sha256": self.lora_artifact.sha256 if self.lora_artifact else None,
                "prompt": request.prompt,
                "negative_prompt": request.negative_prompt,
                "width": request.width,
                "height": request.height,
                "is_mock": False,
            },
        )

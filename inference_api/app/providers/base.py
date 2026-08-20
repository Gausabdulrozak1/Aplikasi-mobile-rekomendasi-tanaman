from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from inference_api.app.services.prompt_builder import PreparedGenerationRequest


@dataclass
class GenerationResult:
    image_path: str
    image_id: str
    seed: int
    generation_time_seconds: float
    model: str
    metadata: dict[str, Any] = field(default_factory=dict)


class ImageGenerator(ABC):
    provider_name: str = "base"

    @abstractmethod
    def health(self) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def generate(self, request: PreparedGenerationRequest, request_id: str) -> GenerationResult:
        raise NotImplementedError

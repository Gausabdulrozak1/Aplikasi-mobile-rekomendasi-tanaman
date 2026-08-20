from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

CropId = Literal["padi", "jagung", "cabai", "kacang_tanah"]
LandType = Literal["sawah", "tegalan", "kebun_campur"]
WaterAvailability = Literal["cukup", "terbatas", "kurang"]
PreviousCrop = Literal["padi", "jagung", "cabai", "kacang_tanah", "kosong"]


class ApiModel(BaseModel):
    model_config = ConfigDict(protected_namespaces=())


class GenerationParameters(ApiModel):
    model_config = ConfigDict(protected_namespaces=(), extra="forbid")

    seed: int | None = Field(default=None, ge=0, le=2_147_483_647)
    request_id: str | None = Field(default=None, min_length=1, max_length=64)
    steps: int = Field(default=25, ge=1, le=50)
    guidance_scale: float = Field(default=7.5, ge=1.0, le=15.0)
    width: int = Field(default=512, ge=256, le=768)
    height: int = Field(default=512, ge=256, le=768)

    @field_validator("width", "height")
    @classmethod
    def dimension_must_be_multiple_of_64(cls, value: int) -> int:
        if value % 64 != 0:
            raise ValueError("dimension must be a multiple of 64")
        return value

    @field_validator("request_id")
    @classmethod
    def request_id_must_be_safe(cls, value: str | None) -> str | None:
        if value is not None and not re.fullmatch(r"[A-Za-z0-9._-]+", value):
            raise ValueError("request_id may contain only letters, numbers, dot, dash, underscore")
        return value


class GenerateRequest(GenerationParameters):
    crop: CropId
    land_type: LandType
    water_availability: WaterAvailability
    previous_crop: PreviousCrop
    weather_summary: str = Field(min_length=2, max_length=500)

    @field_validator("weather_summary")
    @classmethod
    def normalize_weather_summary(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("weather_summary must not be blank")
        return normalized


class PromptGenerateRequest(GenerationParameters):
    prompt: str = Field(min_length=2, max_length=1000)
    negative_prompt: str = Field(default="", max_length=1000)

    @field_validator("prompt")
    @classmethod
    def normalize_required_prompt(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("prompt must not be blank")
        return normalized

    @field_validator("negative_prompt")
    @classmethod
    def normalize_negative_prompt(cls, value: str) -> str:
        return " ".join(value.split())


GeneratePayload = GenerateRequest | PromptGenerateRequest


class GenerateResponse(ApiModel):
    success: bool
    request_id: str
    crop: CropId | None
    image_url: str
    image_id: str
    seed: int
    generation_time_seconds: float
    model: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class HealthResponse(ApiModel):
    status: Literal["ok"]
    provider: str
    device: str
    model_loaded: bool
    version: str


class ReadinessResponse(ApiModel):
    status: Literal["ready", "not_ready"]
    provider: str
    device: str
    model_loaded: bool
    reason: str | None = None


class ModelInfoResponse(ApiModel):
    base_model: str
    lora_identifier: str
    provider: str
    supported_crops: list[str]
    trigger_tokens: dict[str, str]
    pilot_trigger_tokens: dict[str, str]
    supported_request_modes: list[str]
    supported_width: list[int]
    supported_height: list[int]
    default_parameters: dict[str, Any]

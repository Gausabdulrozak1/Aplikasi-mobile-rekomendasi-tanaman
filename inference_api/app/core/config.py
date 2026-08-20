from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "TaniAdaptif Inference API"
    app_version: str = "0.1.0"
    provider: str = Field(default="mock", validation_alias="INFERENCE_PROVIDER")
    base_model: str = Field(
        default="stable-diffusion-v1-5/stable-diffusion-v1-5",
        validation_alias="BASE_MODEL",
    )
    lora_path: str = Field(default="", validation_alias="LORA_PATH")
    lora_sha256: str = Field(default="", validation_alias="LORA_SHA256")
    lora_identifier: str = Field(default="none", validation_alias="LORA_IDENTIFIER")
    require_gpu: bool = Field(default=False, validation_alias="REQUIRE_GPU")
    require_api_token: bool = Field(default=False, validation_alias="INFERENCE_REQUIRE_TOKEN")
    api_token: str = Field(default="", validation_alias="INFERENCE_API_TOKEN")
    generated_dir: Path = Field(
        default=Path("inference_api/generated"), validation_alias="GENERATED_DIR"
    )
    cors_origins: str = Field(default="*", validation_alias="CORS_ORIGINS")
    generation_timeout_seconds: float = Field(
        default=90.0, validation_alias="GENERATION_TIMEOUT_SECONDS"
    )
    generation_max_retries: int = Field(
        default=1, ge=0, le=2, validation_alias="GENERATION_MAX_RETRIES"
    )
    default_seed: int = Field(default=42, ge=0, le=2_147_483_647, validation_alias="DEFAULT_SEED")
    default_width: int = 512
    default_height: int = 512

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    @property
    def cors_origin_list(self) -> list[str]:
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @model_validator(mode="after")
    def validate_api_token(self) -> "Settings":
        placeholder = self.api_token.strip().casefold().startswith("replace-with")
        if self.require_api_token and (len(self.api_token) < 32 or placeholder):
            raise ValueError(
                "INFERENCE_API_TOKEN must be a non-placeholder secret with at least 32 "
                "characters when token auth is required"
            )
        return self


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.generated_dir.mkdir(parents=True, exist_ok=True)
    return settings

from __future__ import annotations

import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from inference_api.app.core.config import Settings
from inference_api.app.main import create_app
from inference_api.app.models.schemas import GenerateRequest, PromptGenerateRequest
from inference_api.app.providers.base import GenerationResult, ImageGenerator
from inference_api.app.services.generation_service import GenerationService
from inference_api.app.services.prompt_builder import (
    TRIGGER_TOKENS,
    PreparedGenerationRequest,
    build_direct_prompt,
    build_generation_prompt,
)


def make_settings(tmp_path: Path, **overrides: object) -> Settings:
    values: dict[str, object] = {
        "provider": "mock",
        "generated_dir": tmp_path / "generated",
        "generation_timeout_seconds": 1.0,
        "generation_max_retries": 1,
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def valid_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "crop": "padi",
        "land_type": "sawah",
        "water_availability": "cukup",
        "previous_crop": "jagung",
        "weather_summary": "Cerah berawan, kelembaban 78 persen",
        "seed": 42,
        "steps": 5,
        "width": 512,
        "height": 512,
    }
    payload.update(overrides)
    return payload


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    settings = make_settings(tmp_path)
    with TestClient(create_app(settings)) as test_client:
        yield test_client


def test_health_and_readiness_mock_provider(client: TestClient) -> None:
    health = client.get("/health")
    ready = client.get("/ready")

    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    assert health.json()["provider"] == "mock"
    assert ready.status_code == 200
    assert ready.json()["status"] == "ready"


def test_private_inference_token_protects_non_health_routes(tmp_path: Path) -> None:
    token = "t" * 32
    settings = make_settings(
        tmp_path,
        require_api_token=True,
        api_token=token,
    )
    with TestClient(create_app(settings)) as test_client:
        health = test_client.get("/health")
        unauthorized = test_client.get("/ready")
        authorized = test_client.get(
            "/ready",
            headers={"X-Inference-Token": token},
        )

    assert health.status_code == 200
    assert unauthorized.status_code == 401
    assert unauthorized.json()["error"]["code"] == "INFERENCE_AUTH_REQUIRED"
    assert authorized.status_code == 200
    assert token not in authorized.text


def test_private_inference_token_rejects_example_placeholder(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="non-placeholder"):
        make_settings(
            tmp_path,
            require_api_token=True,
            api_token="replace-with-a-random-secret-at-least-32-characters",
        )


def test_model_info_has_four_final_triggers(client: TestClient) -> None:
    response = client.get("/v1/model-info")

    assert response.status_code == 200
    data = response.json()
    assert data["supported_crops"] == ["padi", "jagung", "cabai", "kacang_tanah"]
    assert data["trigger_tokens"] == TRIGGER_TOKENS
    assert data["pilot_trigger_tokens"] == {"padi": "gaus_padi_public"}
    assert data["supported_request_modes"] == ["structured_context", "direct_prompt"]
    assert 512 in data["supported_width"]
    assert data["default_parameters"]["max_retries"] == 1


@pytest.mark.parametrize("crop", list(TRIGGER_TOKENS))
def test_generate_mock_image_for_each_crop(client: TestClient, crop: str, tmp_path: Path) -> None:
    response = client.post(
        "/v1/generate",
        json=valid_payload(crop=crop, request_id=f"test-{crop}"),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["crop"] == crop
    assert data["request_id"] == f"test-{crop}"
    assert response.headers["x-request-id"] == f"test-{crop}"
    assert data["metadata"]["trigger_token"] == TRIGGER_TOKENS[crop]
    assert data["metadata"]["is_mock"] is True
    assert data["metadata"]["request_mode"] == "structured_context"
    assert data["metadata"]["recommendation_source"] == "rule_engine_input"
    image_name = data["image_url"].split("/")[-1]
    assert (tmp_path / "generated" / image_name).is_file()


def test_prompt_is_generated_from_structured_context() -> None:
    request = GenerateRequest.model_validate(valid_payload(crop="kacang_tanah"))
    prepared = build_generation_prompt(request, default_seed=7)

    assert "taniadaptif_kacang_tanah" in prepared.prompt
    assert "peanut plants" in prepared.prompt
    assert "following maize" in prepared.prompt
    assert "Aikmel" not in prepared.prompt
    assert "market stall" in prepared.negative_prompt


def test_direct_prompt_mode_supports_the_public_padi_pilot(client: TestClient) -> None:
    response = client.post(
        "/v1/generate",
        json={
            "prompt": "a realistic agricultural photograph of gaus_padi_public in a rice field",
            "negative_prompt": "blurry, watermark",
            "seed": 42,
            "request_id": "pilot-direct-001",
            "steps": 5,
            "guidance_scale": 7.5,
            "width": 512,
            "height": 512,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["crop"] == "padi"
    assert data["request_id"] == "pilot-direct-001"
    assert data["metadata"]["trigger_token"] == "gaus_padi_public"
    assert data["metadata"]["request_mode"] == "direct_prompt"
    assert data["metadata"]["recommendation_source"] == "direct_prompt_input"
    assert data["metadata"]["is_mock"] is True


def test_direct_prompt_builder_does_not_invent_a_crop_without_a_known_trigger() -> None:
    request = PromptGenerateRequest.model_validate(
        {
            "prompt": "a realistic agricultural landscape",
            "negative_prompt": "blurry",
        }
    )

    prepared = build_direct_prompt(request, default_seed=42)

    assert prepared.crop is None
    assert prepared.trigger_token == ""
    assert prepared.request_mode == "direct_prompt"
    assert prepared.recommendation_source == "direct_prompt_input"


def test_direct_prompt_validation_rejects_long_or_hybrid_payload(client: TestClient) -> None:
    too_long = client.post(
        "/v1/generate",
        json={"prompt": "x" * 1001, "negative_prompt": "blurry"},
    )
    blank = client.post(
        "/v1/generate",
        json={"prompt": "  ", "negative_prompt": "blurry"},
    )
    hybrid = client.post(
        "/v1/generate",
        json={**valid_payload(), "prompt": "must not be silently ignored"},
    )

    assert too_long.status_code == 422
    assert too_long.json()["error"]["code"] == "VALIDATION_ERROR"
    assert blank.status_code == 422
    assert blank.json()["error"]["code"] == "VALIDATION_ERROR"
    assert hybrid.status_code == 422
    assert hybrid.json()["error"]["code"] == "VALIDATION_ERROR"


def test_validation_and_unsupported_crop_are_structured(client: TestClient) -> None:
    bad_dimension = client.post(
        "/v1/generate",
        json=valid_payload(width=513),
    )
    unsupported_crop = client.post(
        "/v1/generate",
        json=valid_payload(crop="kedelai"),
    )

    assert bad_dimension.status_code == 422
    assert bad_dimension.json()["error"]["code"] == "VALIDATION_ERROR"
    assert unsupported_crop.status_code == 422
    assert unsupported_crop.json()["error"]["code"] == "VALIDATION_ERROR"
    assert unsupported_crop.json()["error"]["retryable"] is False


def test_request_id_header_is_preserved(client: TestClient) -> None:
    response = client.post(
        "/v1/generate",
        headers={"X-Request-ID": "flutter-request-123"},
        json=valid_payload(seed=None),
    )

    assert response.status_code == 200
    assert response.json()["request_id"] == "flutter-request-123"
    assert response.json()["seed"] == 42


class FailingProvider(ImageGenerator):
    provider_name = "failing-test"

    def __init__(self) -> None:
        self.calls = 0

    def health(self) -> dict[str, object]:
        return {"provider": self.provider_name, "device": "cpu", "model_loaded": True}

    def generate(self, request: PreparedGenerationRequest, request_id: str) -> GenerationResult:
        self.calls += 1
        raise RuntimeError("fixture provider failure")


class SlowProvider(FailingProvider):
    provider_name = "slow-test"

    def generate(self, request: PreparedGenerationRequest, request_id: str) -> GenerationResult:
        self.calls += 1
        time.sleep(0.15)
        raise RuntimeError("late fixture failure")


class NotReadyProvider(FailingProvider):
    provider_name = "not-ready-test"

    def health(self) -> dict[str, object]:
        return {
            "provider": self.provider_name,
            "device": "not_loaded",
            "model_loaded": False,
            "reason": "fixture model unavailable",
        }


def test_provider_failure_retries_once_then_returns_structured_503(tmp_path: Path) -> None:
    settings = make_settings(tmp_path, generation_max_retries=1)
    provider = FailingProvider()
    service = GenerationService(settings, provider)

    with TestClient(create_app(settings, service), raise_server_exceptions=False) as test_client:
        response = test_client.post("/v1/generate", json=valid_payload())

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "GENERATION_FAILED"
    assert provider.calls == 2


def test_generation_timeout_is_not_retried(tmp_path: Path) -> None:
    settings = make_settings(
        tmp_path,
        generation_timeout_seconds=0.02,
        generation_max_retries=2,
    )
    provider = SlowProvider()
    service = GenerationService(settings, provider)

    with TestClient(create_app(settings, service), raise_server_exceptions=False) as test_client:
        response = test_client.post("/v1/generate", json=valid_payload())

    assert response.status_code == 504
    assert response.json()["error"]["code"] == "GENERATION_TIMEOUT"
    assert provider.calls == 1
    assert service.readiness()["ready"] is False


def test_not_ready_provider_returns_503(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    service = GenerationService(settings, NotReadyProvider())

    with TestClient(create_app(settings, service)) as test_client:
        response = test_client.get("/ready")

    assert response.status_code == 503
    assert response.json()["status"] == "not_ready"
    assert response.json()["model_loaded"] is False


class OutsidePathProvider(ImageGenerator):
    provider_name = "outside-path-test"

    def __init__(self, outside_path: Path) -> None:
        self.outside_path = outside_path

    def health(self) -> dict[str, object]:
        return {"provider": self.provider_name, "device": "cpu", "model_loaded": True}

    def generate(self, request: PreparedGenerationRequest, request_id: str) -> GenerationResult:
        self.outside_path.write_bytes(b"fixture")
        return GenerationResult(
            image_path=str(self.outside_path),
            image_id="outside",
            seed=request.seed,
            generation_time_seconds=0,
            model="fixture",
        )


def test_provider_output_outside_generated_directory_is_rejected(tmp_path: Path) -> None:
    settings = make_settings(tmp_path, generation_max_retries=0)
    service = GenerationService(settings, OutsidePathProvider(tmp_path / "outside.png"))

    with TestClient(create_app(settings, service), raise_server_exceptions=False) as test_client:
        response = test_client.post("/v1/generate", json=valid_payload())

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "GENERATION_FAILED"

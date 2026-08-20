from __future__ import annotations

import re
from dataclasses import dataclass

from inference_api.app.models.schemas import GeneratePayload, GenerateRequest, PromptGenerateRequest

TRIGGER_TOKENS = {
    "padi": "taniadaptif_padi",
    "jagung": "taniadaptif_jagung",
    "cabai": "taniadaptif_cabai",
    "kacang_tanah": "taniadaptif_kacang_tanah",
}

PILOT_TRIGGER_TOKENS = {
    "gaus_padi_public": "padi",
}

CROP_PHRASES = {
    "padi": "rice plants",
    "jagung": "maize plants",
    "cabai": "chili plants",
    "kacang_tanah": "peanut plants",
}

LAND_PHRASES = {
    "sawah": "in a cultivated rice-field landscape",
    "tegalan": "on cultivated dryland",
    "kebun_campur": "in a cultivated mixed-garden landscape",
}

WATER_PHRASES = {
    "cukup": "with sufficient water availability",
    "terbatas": "with limited water availability",
    "kurang": "with low water availability",
}

PREVIOUS_CROP_PHRASES = {
    "padi": "rice",
    "jagung": "maize",
    "cabai": "chili",
    "kacang_tanah": "peanut",
    "kosong": "no previous crop",
}

DEFAULT_NEGATIVE_PROMPT = (
    "illustration, painting, drawing, CGI, artificial plastic texture, blurry, low resolution, "
    "distorted plants, duplicated plants, harvested produce only, prepared food, market stall, "
    "text, logo, watermark, people as the main subject"
)


@dataclass(frozen=True)
class PreparedGenerationRequest:
    crop: str | None
    trigger_token: str
    prompt: str
    negative_prompt: str
    seed: int
    steps: int
    guidance_scale: float
    width: int
    height: int
    request_mode: str
    recommendation_source: str


def build_generation_prompt(
    request: GenerateRequest,
    *,
    default_seed: int,
) -> PreparedGenerationRequest:
    trigger = TRIGGER_TOKENS[request.crop]
    crop_phrase = CROP_PHRASES[request.crop]
    previous_crop = PREVIOUS_CROP_PHRASES[request.previous_crop]
    weather = request.weather_summary.rstrip(".,; ")
    prompt = (
        f"a realistic agricultural photograph of {trigger}, {crop_phrase} growing in an "
        f"agricultural environment, natural lighting, {LAND_PHRASES[request.land_type]}, "
        f"{WATER_PHRASES[request.water_availability]}, following {previous_crop}, "
        f"weather context: {weather}"
    )
    return PreparedGenerationRequest(
        crop=request.crop,
        trigger_token=trigger,
        prompt=prompt,
        negative_prompt=DEFAULT_NEGATIVE_PROMPT,
        seed=request.seed if request.seed is not None else default_seed,
        steps=request.steps,
        guidance_scale=request.guidance_scale,
        width=request.width,
        height=request.height,
        request_mode="structured_context",
        recommendation_source="rule_engine_input",
    )


def build_direct_prompt(
    request: PromptGenerateRequest,
    *,
    default_seed: int,
) -> PreparedGenerationRequest:
    detected: list[tuple[str, str]] = []
    normalized_prompt = request.prompt.casefold()
    token_to_crop = {
        **{token: crop for crop, token in TRIGGER_TOKENS.items()},
        **PILOT_TRIGGER_TOKENS,
    }
    for token, crop in token_to_crop.items():
        if re.search(rf"(?<![a-z0-9_]){re.escape(token)}(?![a-z0-9_])", normalized_prompt):
            detected.append((token, crop))

    detected_crops = {crop for _, crop in detected}
    crop = next(iter(detected_crops)) if len(detected_crops) == 1 else None
    trigger_token = detected[0][0] if len(detected) == 1 else ""
    return PreparedGenerationRequest(
        crop=crop,
        trigger_token=trigger_token,
        prompt=request.prompt,
        negative_prompt=request.negative_prompt or DEFAULT_NEGATIVE_PROMPT,
        seed=request.seed if request.seed is not None else default_seed,
        steps=request.steps,
        guidance_scale=request.guidance_scale,
        width=request.width,
        height=request.height,
        request_mode="direct_prompt",
        recommendation_source="direct_prompt_input",
    )


def prepare_generation_request(
    request: GeneratePayload,
    *,
    default_seed: int,
) -> PreparedGenerationRequest:
    if isinstance(request, PromptGenerateRequest):
        return build_direct_prompt(request, default_seed=default_seed)
    return build_generation_prompt(request, default_seed=default_seed)

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

CROP_VISUAL_PROMPTS = {
    "padi": (
    "taniadaptif_padi, commercial agricultural photograph of a wooden bowl "
    "overflowing with uncooked white rice grains beside bundles of golden rice "
    "panicles, unmistakable rice harvest, paddy field background, realistic "
    "natural daylight"

    ),
    "jagung": (
        "maize plants in an agricultural environment, natural lighting, clear crop view"
    ),
    "cabai": (
        "chili plants in an agricultural environment, natural lighting, clear crop view"
    ),
    "kacang_tanah": (
        "peanut plants in an agricultural environment, natural lighting, clear crop view"
    ),
}

DEFAULT_NEGATIVE_PROMPT = (
    "illustration, painting, drawing, CGI, blurry, text, logo, watermark"
)

CROP_NEGATIVE_PROMPTS = {
    "padi": (
        "wooden bowl, cup, plate, cooked rice, uncooked rice grains, rice product, "
        "packaged rice, food, kitchen, restaurant, harvested rice only, wheat, barley, "
        "oats, maize, corn, chili, peanut, illustration, painting, drawing, CGI, blurry, "
        "text, logo, watermark"
    ),
}


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
    crop_visual_prompt = CROP_VISUAL_PROMPTS[request.crop]
    # Keep historical crops and land labels out of the visual prompt: terms such
    # as "rice-field" can overpower the explicitly selected non-rice trigger.
    prompt = f"{trigger}, {crop_visual_prompt}"
    return PreparedGenerationRequest(
        crop=request.crop,
        trigger_token=trigger,
        prompt=prompt,
        negative_prompt=CROP_NEGATIVE_PROMPTS.get(request.crop, DEFAULT_NEGATIVE_PROMPT),
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

import '../data/demo_visual_catalog.dart';
import '../models/generate_visual_model.dart';

class DemoVisualFallbackService {
  static final Map<String, int> _nextVariantByCrop = {};

  static GenerateVisualResponse? responseFor(
    GenerateVisualRequest request, {
    required String fallbackReason,
  }) {
    final variants = DemoVisualCatalog.variantsForCrop(
      request.selectedCrop,
    );

    if (variants.isEmpty) return null;

    final currentIndex = _nextVariantByCrop[request.selectedCrop] ?? 0;
    final variantIndex = currentIndex % variants.length;

    _nextVariantByCrop[request.selectedCrop] =
        (variantIndex + 1) % variants.length;

    final artifact = variants[variantIndex];
    final isGeneratedArtifact =
        artifact.sourcePath.startsWith('artifacts/');

    return GenerateVisualResponse(
      success: true,
      requestId: request.requestId,
      crop: artifact.crop,
      imageUrl: '',
      imageId:
          'cached-${artifact.crop}-fallback-v${variantIndex + 1}-s${artifact.seed}',
      seed: artifact.seed,
      generationTimeSeconds: 0,
      model: isGeneratedArtifact
          ? 'stable-diffusion-v1-5 + LoRA'
          : 'local cached photo',
      metadata: {
        'provider': isGeneratedArtifact ? 'diffusers' : 'local_asset',
        'is_mock': false,
        'is_live': false,
        'visual_source': isGeneratedArtifact
            ? 'cached_inference_artifact'
            : 'cached_demo_asset',
        'asset_path': artifact.assetPath,
        'source_artifact': artifact.sourcePath,
        'artifact_sha256': artifact.sha256,
        'trigger_token': artifact.triggerToken,
        'prompt': artifact.prompt,
        'lora_identifier': isGeneratedArtifact
            ? 'multisource_multicrop_lora_sd15_20260820T143551Z'
            : null,
        'fallback_variant': variantIndex + 1,
        'fallback_variant_count': variants.length,
        'fallback_reason': fallbackReason,
      },
    );
  }
}
class GenerateVisualRequest {
  final String selectedCrop;
  final String landType;
  final String waterAvailability;
  final String previousCrop;
  final String weatherSummary;
  final int? seed;
  final String requestId;
  final int steps;
  final double guidanceScale;
  final int width;
  final int height;

  const GenerateVisualRequest({
    required this.selectedCrop,
    required this.landType,
    required this.waterAvailability,
    required this.previousCrop,
    required this.weatherSummary,
    required this.requestId,
    this.seed,
    this.steps = 25,
    this.guidanceScale = 7.5,
    this.width = 512,
    this.height = 512,
  });

  Map<String, dynamic> toJson() {
    return {
      'selected_crop': selectedCrop,
      'land_type': landType,
      'water_availability': waterAvailability,
      'previous_crop': previousCrop,
      'weather_summary': weatherSummary,
      if (seed != null) 'seed': seed,
      'request_id': requestId,
      'steps': steps,
      'guidance_scale': guidanceScale,
      'width': width,
      'height': height,
    };
  }
}

class GenerateVisualResponse {
  final bool success;
  final String requestId;
  final String crop;
  final String imageUrl;
  final String imageId;
  final int seed;
  final double generationTimeSeconds;
  final String model;
  final Map<String, dynamic> metadata;

  const GenerateVisualResponse({
    required this.success,
    required this.requestId,
    required this.crop,
    required this.imageUrl,
    required this.imageId,
    required this.seed,
    required this.generationTimeSeconds,
    required this.model,
    required this.metadata,
  });

  factory GenerateVisualResponse.fromJson(Map<String, dynamic> json) {
    return GenerateVisualResponse(
      success: json['success'] == true,
      requestId: json['request_id']?.toString() ?? '',
      crop: json['selected_crop']?.toString() ?? json['crop']?.toString() ?? '',
      imageUrl: json['image_url']?.toString() ?? '',
      imageId: json['image_id']?.toString() ?? '',
      seed: _toInt(json['seed']),
      generationTimeSeconds: _toDouble(json['generation_time_seconds']),
      model: json['model']?.toString() ?? '',
      metadata: _asMap(json['metadata']),
    );
  }
}

class InferenceModelInfo {
  final String baseModel;
  final String loraIdentifier;
  final String provider;
  final List<String> supportedCrops;

  const InferenceModelInfo({
    required this.baseModel,
    required this.loraIdentifier,
    required this.provider,
    required this.supportedCrops,
  });

  factory InferenceModelInfo.fromJson(Map<String, dynamic> json) {
    return InferenceModelInfo(
      baseModel: json['base_model']?.toString() ?? '',
      loraIdentifier: json['lora_identifier']?.toString() ?? '',
      provider: json['provider']?.toString() ?? '',
      supportedCrops: (json['supported_crops'] as List<dynamic>? ?? const [])
          .map((item) => item.toString())
          .toList(),
    );
  }
}

Map<String, dynamic> _asMap(dynamic value) {
  if (value is Map<String, dynamic>) return value;
  if (value is Map) {
    return value.map((key, item) => MapEntry(key.toString(), item));
  }
  return <String, dynamic>{};
}

int _toInt(dynamic value) {
  if (value is int) return value;
  if (value is double) return value.toInt();
  return int.tryParse(value?.toString() ?? '') ?? 0;
}

double _toDouble(dynamic value) {
  if (value is double) return value;
  if (value is int) return value.toDouble();
  return double.tryParse(value?.toString() ?? '') ?? 0;
}

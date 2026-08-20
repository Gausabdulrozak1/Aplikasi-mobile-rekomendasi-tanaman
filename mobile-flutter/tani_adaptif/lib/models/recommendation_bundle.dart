import 'cuaca_model.dart';
import 'rekomendasi_model.dart';

class RecommendationBundle {
  final CuacaModel cuaca;
  final RekomendasiModel rekomendasi;
  final Map<String, dynamic> rawResponse;

  const RecommendationBundle({
    required this.cuaca,
    required this.rekomendasi,
    required this.rawResponse,
  });

  factory RecommendationBundle.fromJson(Map<String, dynamic> json) {
    return RecommendationBundle(
      cuaca: CuacaModel.fromJson({'data': json['cuaca']}),
      rekomendasi: RekomendasiModel.fromJson(json),
      rawResponse: Map<String, dynamic>.from(json),
    );
  }

  RecommendationBundle asLocalCache() {
    return RecommendationBundle(
      cuaca: cuaca.asLocalCache(),
      rekomendasi: rekomendasi,
      rawResponse: rawResponse,
    );
  }

  Map<String, dynamic> toJson() => rawResponse;
}

import '../config/app_config.dart';
import '../models/cuaca_model.dart';
import '../models/recommendation_bundle.dart';
import '../services/api_service.dart';
import '../services/local_storage_service.dart';

class RepositoryResult<T> {
  final T data;
  final bool fromCache;
  final String? notice;

  const RepositoryResult({
    required this.data,
    required this.fromCache,
    this.notice,
  });
}

class TaniAdaptifRepository {
  final ApiService apiService;
  final LocalStorageService localStorage;

  TaniAdaptifRepository({
    ApiService? apiService,
    LocalStorageService? localStorage,
  }) : apiService = apiService ?? ApiService(),
       localStorage = localStorage ?? const LocalStorageService();

  Future<RepositoryResult<CuacaModel>> getWeather({String? kodeWilayah}) async {
    try {
      final weather = await apiService.ambilCuaca(kodeWilayah: kodeWilayah);
      await localStorage.saveWeather(weather);
      return RepositoryResult(data: weather, fromCache: false);
    } catch (error) {
      final cached = await localStorage.loadWeather();
      if (cached == null) rethrow;
      return RepositoryResult(
        data: cached,
        fromCache: true,
        notice: 'Server tidak terjangkau. Menampilkan data terakhir tersimpan.',
      );
    }
  }

  Future<RepositoryResult<RecommendationBundle>> getRecommendation({
    required String ketersediaanAir,
    required String tanamanSebelumnya,
    required String jenisLahan,
    String? kodeWilayah,
  }) async {
    final signature = [
      kodeWilayah ?? AppConfig.kodeWilayahAikmel,
      ketersediaanAir,
      tanamanSebelumnya,
      jenisLahan,
    ].join('|');
    try {
      final bundle = await apiService.dapatkanRekomendasiOtomatis(
        ketersediaanAir: ketersediaanAir,
        tanamanSebelumnya: tanamanSebelumnya,
        jenisLahan: jenisLahan,
        kodeWilayah: kodeWilayah,
      );
      await localStorage.saveRecommendation(signature, bundle);
      return RepositoryResult(data: bundle, fromCache: false);
    } catch (error) {
      final cached = await localStorage.loadRecommendation(signature);
      if (cached == null) rethrow;
      return RepositoryResult(
        data: cached,
        fromCache: true,
        notice:
            'Server tidak terjangkau. Menampilkan rekomendasi terakhir untuk input ini.',
      );
    }
  }
}

import 'dart:async';

import 'package:dio/dio.dart';

import '../config/app_config.dart';
import '../models/cuaca_model.dart';
import '../models/recommendation_bundle.dart';

class ApiService {
  final Dio _dio;
  final bool mockMode;

  ApiService({Dio? dio, bool? mockMode})
    : mockMode = mockMode ?? AppConfig.mockMode,
      _dio =
          dio ??
          Dio(
            BaseOptions(
              baseUrl: AppConfig.baseUrl,
              connectTimeout: const Duration(seconds: 15),
              receiveTimeout: const Duration(seconds: 25),
              sendTimeout: const Duration(seconds: 15),
              headers: {'Accept': 'application/json'},
            ),
          );

  Future<bool> cekKesehatan() async {
    if (mockMode) return true;
    try {
      final response = await _request(() => _dio.get('/kesehatan'));
      return response.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  Future<CuacaModel> ambilCuaca({String? kodeWilayah}) async {
    if (mockMode) return CuacaModel.fromJson(_mockWeatherResponse);
    try {
      final kode = kodeWilayah ?? AppConfig.kodeWilayahAikmel;
      final response = await _request(() => _dio.get('/cuaca/$kode'));
      return CuacaModel.fromJson(_asMap(response.data));
    } on DioException catch (error) {
      throw ApiException.fromDio(error, operation: 'mengambil cuaca');
    }
  }

  Future<RecommendationBundle> dapatkanRekomendasiOtomatis({
    required String ketersediaanAir,
    required String tanamanSebelumnya,
    required String jenisLahan,
    String? kodeWilayah,
  }) async {
    if (mockMode) {
      return RecommendationBundle.fromJson(
        _mockRecommendationResponse(
          ketersediaanAir: ketersediaanAir,
          tanamanSebelumnya: tanamanSebelumnya,
          jenisLahan: jenisLahan,
        ),
      );
    }

    try {
      final kode = kodeWilayah ?? AppConfig.kodeWilayahAikmel;
      final response = await _request(
        () => _dio.post(
          '/rekomendasi/kalender',
          data: {
            'kodeWilayah': kode,
            'ketersediaanAir': ketersediaanAir,
            'tanamanSebelumnya': tanamanSebelumnya,
            'jenisLahan': jenisLahan,
          },
        ),
      );
      return RecommendationBundle.fromJson(_asMap(response.data));
    } on DioException catch (error) {
      throw ApiException.fromDio(error, operation: 'mendapatkan rekomendasi');
    }
  }

  Future<Response<dynamic>> _request(
    Future<Response<dynamic>> Function() action,
  ) async {
    const maxRetries = 1;
    for (var attempt = 0; ; attempt++) {
      try {
        return await action();
      } on DioException catch (error) {
        if (attempt >= maxRetries || !_isRetryable(error)) rethrow;
        await Future<void>.delayed(const Duration(milliseconds: 250));
      }
    }
  }

  bool _isRetryable(DioException error) {
    if (error.type == DioExceptionType.connectionError ||
        error.type == DioExceptionType.connectionTimeout) {
      return true;
    }
    final status = error.response?.statusCode ?? 0;
    return status >= 500;
  }
}

class ApiException implements Exception {
  final String message;
  final int? statusCode;
  final bool offline;
  final String? code;

  const ApiException(
    this.message, {
    this.statusCode,
    this.offline = false,
    this.code,
  });

  factory ApiException.fromDio(
    DioException error, {
    required String operation,
  }) {
    final data = _asMap(error.response?.data);
    final structuredError = _asMap(data['error']);
    final serverMessage =
        structuredError['message']?.toString() ?? data['pesan']?.toString();
    final offline =
        error.type == DioExceptionType.connectionError ||
        error.type == DioExceptionType.connectionTimeout;
    final fallback = offline
        ? 'Tidak dapat terhubung ke server saat $operation.'
        : 'Server gagal $operation.';
    return ApiException(
      serverMessage ?? fallback,
      statusCode: error.response?.statusCode,
      offline: offline,
      code: structuredError['code']?.toString() ?? data['kode']?.toString(),
    );
  }

  @override
  String toString() => message;
}

Map<String, dynamic> _asMap(dynamic value) {
  if (value is Map<String, dynamic>) return value;
  if (value is Map) {
    return value.map((key, item) => MapEntry(key.toString(), item));
  }
  return <String, dynamic>{};
}

final Map<String, dynamic> _mockWeatherPayload = {
  'lokasi': {'desa': 'Aikmel', 'kecamatan': 'Aikmel', 'kotkab': 'Lombok Timur'},
  'cuacaSaatIni': {
    'waktu': 'fixture',
    'suhu': 28,
    'kelembaban': 78,
    'kondisi': 'Cerah Berawan',
    'kecepatanAngin': 5,
    'curahHujan': 1,
  },
  'kategoriCurahHujan': 'sedang',
  'estimasiCurahHujanBulanan': 150,
  'sumberData': 'Mock fixture - bukan data penelitian',
  'waktuAmbil': 'fixture',
  'cache': {'status': 'mock', 'isStale': false},
  'cakupanCurahHujan': {'lengkap': true},
  'metodologiEstimasi': 'Fixture pengembangan aplikasi.',
};

final Map<String, dynamic> _mockWeatherResponse = {'data': _mockWeatherPayload};

Map<String, dynamic> _mockRecommendationResponse({
  required String ketersediaanAir,
  required String tanamanSebelumnya,
  required String jenisLahan,
}) {
  final inputSummary = {
    'kondisiCuaca': 'sedang',
    'jenisLahan': jenisLahan,
    'ketersediaanAir': ketersediaanAir,
    'tanamanSebelumnya': tanamanSebelumnya,
  };
  final tanaman = {
    'prioritas': 1,
    'kode': 'jagung',
    'nama': 'Jagung',
    'namaIlmiah': 'Zea mays',
    'keluarga': 'Sereal',
    'hariTumbuh': 90,
    'kebutuhanAir': 'sedang',
    'deskripsi': 'Fixture rekomendasi untuk pengujian UI.',
  };
  return {
    'status': 'berhasil',
    'cuaca': _mockWeatherPayload,
    'rekomendasi': {
      'status': 'berhasil',
      'input': {
        'tanamanSebelumnya': tanamanSebelumnya,
        'jenisLahan': jenisLahan,
      },
      'inputSummary': inputSummary,
      'recommendedCrop': 'jagung',
      'ruleId': 'MOCK-FIXTURE-NOT-RESEARCH',
      'rekomendasi': [tanaman],
      'alasan': 'Fixture otomatis untuk pengembangan; bukan hasil penelitian.',
    },
    'kalender': {
      'inputSummary': inputSummary,
      'recommendedCrop': 'jagung',
      'ruleId': 'MOCK-FIXTURE-NOT-RESEARCH',
      'rekomendasiTanaman': [tanaman],
      'rencanaMingguan': [],
      'jadwalTanam': [],
      'alasan': 'Fixture otomatis untuk pengembangan; bukan hasil penelitian.',
      'periode': {'mulai': '', 'selesai': '', 'durasi': ''},
      'prakiraanCuaca': {'catatan': 'Mock mode aktif.'},
    },
  };
}

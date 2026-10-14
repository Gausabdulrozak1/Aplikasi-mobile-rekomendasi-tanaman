import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';

import '../config/app_config.dart';
import '../models/cuaca_model.dart';
import '../models/generate_visual_model.dart';
import '../models/rekomendasi_model.dart';

class StableDiffusionService {
  final Dio _dio;
  final String _clientToken;
  int _requestSequence = 0;

  StableDiffusionService({Dio? dio, String? clientToken})
    : _clientToken = clientToken ?? AppConfig.backendVisualApiToken,
      _dio =
          dio ??
          Dio(
            BaseOptions(
              baseUrl: '${AppConfig.baseUrl}/',
              connectTimeout: const Duration(seconds: 15),
              receiveTimeout: const Duration(seconds: 120),
              sendTimeout: const Duration(seconds: 15),
              headers: {'Accept': 'application/json'},
            ),
          );

  Future<GenerateVisualResponse> generate(GenerateVisualRequest request) async {
    try {
      debugPrint('FLUTTER_REQUEST_CROP=${request.selectedCrop}');
      final response = await _dio.post(
        'visual/generate',
        data: request.toJson(),
        options: Options(
          headers: {
            'X-Request-ID': request.requestId,
            if (_clientToken.isNotEmpty) 'X-Client-Token': _clientToken,
          },
        ),
      );
      final result = GenerateVisualResponse.fromJson(_asMap(response.data));
      if (result.crop != request.selectedCrop) {
        throw const StableDiffusionException(
          'Komoditas gambar tidak sesuai dengan tanaman yang dipilih.',
          technicalMessage: 'INFERENCE_CROP_MISMATCH',
        );
      }
      return result;
    } on StableDiffusionException {
      rethrow;
    } on DioException catch (error) {
      throw StableDiffusionException.fromDio(error);
    } catch (error) {
      throw StableDiffusionException(
        'Gagal membuat simulasi visual.',
        technicalMessage: error.toString(),
      );
    }
  }

  Future<InferenceModelInfo> getModelInfo() async {
    for (var attempt = 0; ; attempt++) {
      try {
        final response = await _dio.get(
          'visual/model-info',
          options: Options(
            headers: {
              if (_clientToken.isNotEmpty) 'X-Client-Token': _clientToken,
            },
          ),
        );
        return InferenceModelInfo.fromJson(_asMap(response.data));
      } on DioException catch (error) {
        if (attempt >= 1 || !_isRetryable(error)) {
          throw StableDiffusionException.fromDio(error);
        }
      }
    }
  }

  String describeError(DioException error) {
    return StableDiffusionException.fromDio(error).message;
  }

  GenerateVisualRequest buildRequest({
    required TanamanRekomendasi tanaman,
    required CuacaModel cuaca,
    required String jenisLahan,
    required String ketersediaanAir,
    required String tanamanSebelumnya,
    int? seed,
    String? requestId,
  }) {
    final resolvedRequestId = requestId ?? _nextRequestId(tanaman.kode);
    return GenerateVisualRequest(
      selectedCrop: tanaman.kode,
      landType: jenisLahan,
      waterAvailability: ketersediaanAir,
      previousCrop: tanamanSebelumnya,
      weatherSummary: _weatherSummary(cuaca),
      requestId: resolvedRequestId,
      seed: seed,
    );
  }

  String _nextRequestId(String crop) {
    _requestSequence += 1;
    return 'flutter-$crop-${DateTime.now().microsecondsSinceEpoch}-$_requestSequence';
  }

  String _weatherSummary(CuacaModel cuaca) {
    final details = <String>[cuaca.kondisi];
    if (cuaca.suhu != null) {
      details.add('suhu ${cuaca.suhu!.toStringAsFixed(0)} C');
    }
    if (cuaca.kelembaban != null) {
      details.add('kelembaban ${cuaca.kelembaban!.toStringAsFixed(0)} persen');
    }
    if (cuaca.kategoriCurahHujan != null) {
      details.add('kategori hujan ${cuaca.kategoriCurahHujan}');
    }
    return details.join('; ');
  }

  bool _isRetryable(DioException error) {
    if (error.type == DioExceptionType.connectionError ||
        error.type == DioExceptionType.connectionTimeout) {
      return true;
    }
    return (error.response?.statusCode ?? 0) >= 500;
  }
}

class StableDiffusionException implements Exception {
  final String message;
  final int? statusCode;
  final String? requestId;
  final bool retryable;
  final String? technicalMessage;

  const StableDiffusionException(
    this.message, {
    this.statusCode,
    this.requestId,
    this.retryable = false,
    this.technicalMessage,
  });

  factory StableDiffusionException.fromDio(DioException error) {
    final data = _asMap(error.response?.data);
    final details = _asMap(data['error']);
    if (error.type == DioExceptionType.connectionTimeout ||
        error.type == DioExceptionType.receiveTimeout) {
      return StableDiffusionException(
        'Server simulasi visual terlalu lama merespons.',
        statusCode: error.response?.statusCode,
        requestId: data['request_id']?.toString(),
        retryable: true,
      );
    }
    if (error.type == DioExceptionType.connectionError) {
      return const StableDiffusionException(
        'Server simulasi visual belum aktif atau tidak dapat dijangkau.',
        retryable: true,
      );
    }
    return StableDiffusionException(
      details['message']?.toString() ?? 'Gagal membuat simulasi visual.',
      statusCode: error.response?.statusCode,
      requestId: data['request_id']?.toString(),
      retryable: details['retryable'] == true,
      technicalMessage: details['code']?.toString(),
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

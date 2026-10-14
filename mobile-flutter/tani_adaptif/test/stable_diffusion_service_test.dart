import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:tani_adaptif/models/cuaca_model.dart';
import 'package:tani_adaptif/models/generate_visual_model.dart';
import 'package:tani_adaptif/models/rekomendasi_model.dart';
import 'package:tani_adaptif/services/demo_visual_fallback_service.dart';
import 'package:tani_adaptif/services/stable_diffusion_service.dart';

void main() {
  test('GenerateVisualRequest serializes structured API payload', () {
    const request = GenerateVisualRequest(
      selectedCrop: 'padi',
      landType: 'sawah',
      waterAvailability: 'cukup',
      previousCrop: 'jagung',
      weatherSummary: 'Cerah berawan',
      requestId: 'flutter-test-1',
    );

    expect(request.toJson()['selected_crop'], 'padi');
    expect(request.toJson(), isNot(contains('crop')));
    expect(request.toJson()['land_type'], 'sawah');
    expect(request.toJson()['previous_crop'], 'jagung');
    expect(request.toJson()['request_id'], 'flutter-test-1');
    expect(request.toJson(), isNot(contains('seed')));
    expect(request.toJson(), isNot(contains('prompt')));
  });

  test('GenerateVisualRequest preserves an explicit reproducible seed', () {
    const request = GenerateVisualRequest(
      selectedCrop: 'cabai',
      landType: 'tegalan',
      waterAvailability: 'cukup',
      previousCrop: 'padi',
      weatherSummary: 'Cerah',
      requestId: 'flutter-seed-42',
      seed: 42,
    );

    expect(request.toJson()['seed'], 42);
  });

  test('GenerateVisualResponse parses request and model provenance', () {
    final response = GenerateVisualResponse.fromJson({
      'success': true,
      'request_id': 'req-42',
      'crop': 'padi',
      'image_url': 'http://localhost:3000/api/visual/images/mock.png',
      'image_id': 'mock',
      'seed': 42,
      'generation_time_seconds': 0.1,
      'model': 'mock-placeholder',
      'metadata': {'provider': 'mock', 'trigger_token': 'taniadaptif_padi'},
    });

    expect(response.success, isTrue);
    expect(response.requestId, 'req-42');
    expect(response.crop, 'padi');
    expect(response.metadata['trigger_token'], 'taniadaptif_padi');
  });

  test('demo visual fallback preserves the four crop trigger mappings', () {
    const crops = {
      'padi': 'taniadaptif_padi',
      'jagung': 'taniadaptif_jagung',
      'cabai': 'taniadaptif_cabai',
      'kacang_tanah': 'taniadaptif_kacang_tanah',
    };

    for (final entry in crops.entries) {
      final response = DemoVisualFallbackService.responseFor(
        GenerateVisualRequest(
          selectedCrop: entry.key,
          landType: 'sawah',
          waterAvailability: 'cukup',
          previousCrop: 'padi',
          weatherSummary: 'Cerah',
          requestId: 'fallback-${entry.key}',
        ),
        fallbackReason: 'offline',
      );

      expect(response, isNotNull);
      expect(response!.crop, entry.key);
      expect(response.metadata['trigger_token'], entry.value);
      expect(response.metadata['visual_source'], 'cached_inference_artifact');
      expect(response.metadata['asset_path'], startsWith('assets/demo_visual/'));
    }
  });

  test('StableDiffusionService builds request from recommendation context', () {
    final service = StableDiffusionService();
    final request = service.buildRequest(
      tanaman: _tanamanPadi,
      cuaca: _cuaca,
      jenisLahan: 'sawah',
      ketersediaanAir: 'cukup',
      tanamanSebelumnya: 'jagung',
      requestId: 'fixed-request',
    );

    expect(request.selectedCrop, 'padi');
    expect(request.previousCrop, 'jagung');
    expect(request.weatherSummary, contains('Berawan'));
    expect(request.weatherSummary, contains('kelembaban 80 persen'));
    expect(request.weatherSummary, isNot(contains('Aikmel')));
    expect(request.seed, isNull);
  });

  test(
    'StableDiffusionService creates a new request ID for every simulation',
    () {
      final service = StableDiffusionService();
      final first = service.buildRequest(
        tanaman: _tanamanPadi,
        cuaca: _cuaca,
        jenisLahan: 'sawah',
        ketersediaanAir: 'cukup',
        tanamanSebelumnya: 'jagung',
      );
      final second = service.buildRequest(
        tanaman: _tanamanPadi,
        cuaca: _cuaca,
        jenisLahan: 'sawah',
        ketersediaanAir: 'cukup',
        tanamanSebelumnya: 'jagung',
      );

      expect(first.selectedCrop, 'padi');
      expect(second.selectedCrop, 'padi');
      expect(first.seed, isNull);
      expect(second.seed, isNull);
      expect(first.requestId, isNot(second.requestId));
    },
  );

  test('StableDiffusionService parses structured connection error clearly', () {
    final service = StableDiffusionService();
    final message = service.describeError(
      DioException(
        requestOptions: RequestOptions(path: 'visual/generate'),
        type: DioExceptionType.connectionError,
      ),
    );

    expect(message, contains('belum aktif'));
  });

  test(
    'StableDiffusionService generate sends request ID and parses response',
    () async {
      final dio = Dio(BaseOptions(baseUrl: 'http://mock.test/api/'));
      final adapter = _FakeInferenceAdapter();
      dio.httpClientAdapter = adapter;
      final service = StableDiffusionService(
        dio: dio,
        clientToken: 'temporary-client-token',
      );
      final request = service.buildRequest(
        tanaman: _tanamanPadi,
        cuaca: _cuaca,
        jenisLahan: 'sawah',
        ketersediaanAir: 'cukup',
        tanamanSebelumnya: 'jagung',
        requestId: 'flutter-fixed-42',
      );

      final response = await service.generate(request);

      expect(response.success, isTrue);
      expect(response.requestId, 'flutter-fixed-42');
      expect(response.imageUrl, endsWith('/api/visual/images/mock.png'));
      expect(adapter.lastRequestId, 'flutter-fixed-42');
      expect(adapter.lastClientToken, 'temporary-client-token');
      expect(adapter.lastPayload?['selected_crop'], 'padi');
      expect(adapter.lastPayload, isNot(contains('seed')));
    },
  );

  test('StableDiffusionService rejects a mismatched response crop', () async {
    final dio = Dio(BaseOptions(baseUrl: 'http://mock.test/api/'));
    dio.httpClientAdapter = _FakeInferenceAdapter(responseCrop: 'cabai');
    final service = StableDiffusionService(
      dio: dio,
      clientToken: 'temporary-client-token',
    );
    final request = service.buildRequest(
      tanaman: _tanamanPadi,
      cuaca: _cuaca,
      jenisLahan: 'sawah',
      ketersediaanAir: 'cukup',
      tanamanSebelumnya: 'jagung',
      requestId: 'flutter-mismatch-42',
    );

    await expectLater(
      service.generate(request),
      throwsA(
        isA<StableDiffusionException>().having(
          (error) => error.technicalMessage,
          'technicalMessage',
          'INFERENCE_CROP_MISMATCH',
        ),
      ),
    );
  });
}

final _tanamanPadi = TanamanRekomendasi(
  prioritas: 1,
  kode: 'padi',
  nama: 'Padi',
  namaIlmiah: 'Oryza sativa',
  keluarga: 'Sereal',
  hariTumbuh: 120,
  kebutuhanAir: 'tinggi',
  deskripsi: 'Tanaman pangan utama.',
);

const _cuaca = CuacaModel(
  desa: 'Aikmel',
  kecamatan: 'Aikmel',
  kabupaten: 'Lombok Timur',
  suhu: 28,
  kelembaban: 80,
  kondisi: 'Berawan',
  kecepatanAngin: 4,
  curahHujan: 2,
  kategoriCurahHujan: 'sedang',
  estimasiCurahHujanBulanan: 120,
  sumberData: 'BMKG',
);

class _FakeInferenceAdapter implements HttpClientAdapter {
  final String responseCrop;
  String? lastRequestId;
  String? lastClientToken;
  Map<String, dynamic>? lastPayload;

  _FakeInferenceAdapter({this.responseCrop = 'padi'});

  @override
  void close({bool force = false}) {}

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    expect(options.path, 'visual/generate');
    expect(options.uri.path, '/api/visual/generate');
    lastRequestId = options.headers['X-Request-ID']?.toString();
    lastClientToken = options.headers['X-Client-Token']?.toString();
    lastPayload = Map<String, dynamic>.from(options.data as Map);
    return ResponseBody.fromString(
      jsonEncode({
        'success': true,
        'request_id': lastRequestId,
        'selected_crop': responseCrop,
        'crop': responseCrop,
        'image_url': 'http://mock.test/api/visual/images/mock.png',
        'image_id': 'mock',
        'seed': 42,
        'generation_time_seconds': 0.01,
        'model': 'mock-placeholder',
        'metadata': {'provider': 'mock', 'prompt': 'server generated prompt'},
      }),
      200,
      headers: {
        Headers.contentTypeHeader: [Headers.jsonContentType],
      },
    );
  }
}

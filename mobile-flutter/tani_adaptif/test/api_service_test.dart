import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:tani_adaptif/services/api_service.dart';

void main() {
  test('weather parser preserves unavailable rain as null', () async {
    final dio = Dio(BaseOptions(baseUrl: 'http://backend.test/api'));
    dio.httpClientAdapter = _QueueAdapter([
      _jsonResponse({
        'status': 'berhasil',
        'data': {
          'lokasi': {'desa': 'Aikmel'},
          'cuacaSaatIni': {
            'waktu': '2026-08-04 08:00:00',
            'suhu': 28,
            'kelembaban': 78,
            'kondisi': 'Cerah',
            'curahHujan': null,
          },
          'kategoriCurahHujan': null,
          'estimasiCurahHujanBulanan': null,
          'sumberData': 'BMKG',
          'cakupanCurahHujan': {'lengkap': false},
        },
      }),
    ]);

    final weather = await ApiService(dio: dio).ambilCuaca();

    expect(weather.curahHujan, isNull);
    expect(weather.kategoriCurahHujan, isNull);
    expect(weather.estimasiCurahHujanBulanan, isNull);
    expect(weather.curahHujanLengkap, isFalse);
  });

  test('weather request retries one transient connection failure', () async {
    final dio = Dio(BaseOptions(baseUrl: 'http://backend.test/api'));
    final adapter = _QueueAdapter([
      DioException(
        requestOptions: RequestOptions(path: '/cuaca/test'),
        type: DioExceptionType.connectionError,
      ),
      _jsonResponse({
        'data': {
          'lokasi': {'desa': 'Aikmel'},
          'cuacaSaatIni': {'kondisi': 'Cerah'},
          'sumberData': 'BMKG',
        },
      }),
    ]);
    dio.httpClientAdapter = adapter;

    final weather = await ApiService(dio: dio).ambilCuaca(kodeWilayah: 'test');

    expect(weather.desa, 'Aikmel');
    expect(adapter.calls, 2);
  });

  test(
    'recommendation contract parses rule ID and previous crop code',
    () async {
      final dio = Dio(BaseOptions(baseUrl: 'http://backend.test/api'));
      dio.httpClientAdapter = _QueueAdapter([
        _jsonResponse(_recommendationJson),
      ]);

      final bundle = await ApiService(dio: dio).dapatkanRekomendasiOtomatis(
        ketersediaanAir: 'cukup',
        tanamanSebelumnya: 'padi',
        jenisLahan: 'sawah',
      );

      expect(bundle.rekomendasi.ruleId, 'ROT-TEST');
      expect(bundle.rekomendasi.tanamanSebelumnyaKode, 'padi');
      expect(bundle.rekomendasi.rekomendasi.single.kode, 'jagung');
    },
  );
}

ResponseBody _jsonResponse(Map<String, dynamic> value) {
  return ResponseBody.fromString(
    jsonEncode(value),
    200,
    headers: {
      Headers.contentTypeHeader: [Headers.jsonContentType],
    },
  );
}

class _QueueAdapter implements HttpClientAdapter {
  final List<Object> results;
  int calls = 0;

  _QueueAdapter(this.results);

  @override
  void close({bool force = false}) {}

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    final result = results[calls++];
    if (result is DioException) throw result;
    return result as ResponseBody;
  }
}

final Map<String, dynamic> _recommendationJson = {
  'status': 'berhasil',
  'cuaca': {
    'lokasi': {'desa': 'Aikmel'},
    'cuacaSaatIni': {'kondisi': 'Cerah'},
    'sumberData': 'BMKG',
  },
  'rekomendasi': {
    'input': {'tanamanSebelumnya': 'Padi'},
    'inputSummary': {'tanamanSebelumnya': 'padi'},
    'ruleId': 'ROT-TEST',
    'recommendedCrop': 'jagung',
    'alasan': 'Fixture',
    'rekomendasi': [
      {'prioritas': 1, 'kode': 'jagung', 'nama': 'Jagung', 'hariTumbuh': 90},
    ],
  },
  'kalender': {
    'rencanaMingguan': [],
    'jadwalTanam': [],
    'periode': {},
    'prakiraanCuaca': {},
  },
};

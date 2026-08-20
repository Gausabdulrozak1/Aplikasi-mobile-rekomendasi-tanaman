import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:tani_adaptif/models/cuaca_model.dart';
import 'package:tani_adaptif/models/recommendation_bundle.dart';
import 'package:tani_adaptif/repositories/tani_adaptif_repository.dart';
import 'package:tani_adaptif/services/api_service.dart';
import 'package:tani_adaptif/services/local_storage_service.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  test(
    'weather repository saves network result and loads last-known cache',
    () async {
      final api = _StubApiService();
      final repository = TaniAdaptifRepository(apiService: api);

      final network = await repository.getWeather();
      api.fail = true;
      final cached = await repository.getWeather();

      expect(network.fromCache, isFalse);
      expect(cached.fromCache, isTrue);
      expect(cached.data.desa, 'Aikmel');
      expect(cached.data.isStale, isTrue);
    },
  );

  test('recommendation cache is scoped to the same land inputs', () async {
    final api = _StubApiService();
    final repository = TaniAdaptifRepository(apiService: api);

    await repository.getRecommendation(
      ketersediaanAir: 'cukup',
      tanamanSebelumnya: 'padi',
      jenisLahan: 'sawah',
    );
    api.fail = true;
    final cached = await repository.getRecommendation(
      ketersediaanAir: 'cukup',
      tanamanSebelumnya: 'padi',
      jenisLahan: 'sawah',
    );

    expect(cached.fromCache, isTrue);
    expect(cached.data.rekomendasi.ruleId, 'ROT-FIXTURE');

    expect(
      () => repository.getRecommendation(
        ketersediaanAir: 'terbatas',
        tanamanSebelumnya: 'padi',
        jenisLahan: 'sawah',
      ),
      throwsA(isA<ApiException>()),
    );
  });

  test('visual history saves, loads, and remains bounded', () async {
    final preferences = await SharedPreferences.getInstance();
    final storage = LocalStorageService(preferences: preferences);
    for (var index = 0; index < 25; index++) {
      await storage.saveVisualHistory({
        'request_id': 'request-$index',
        'crop': 'padi',
      });
    }

    final history = await storage.loadVisualHistory();

    expect(history, hasLength(20));
    expect(history.first['request_id'], 'request-24');
    expect(history.last['request_id'], 'request-5');
  });
}

class _StubApiService extends ApiService {
  bool fail = false;

  _StubApiService() : super(mockMode: true);

  @override
  Future<CuacaModel> ambilCuaca({String? kodeWilayah}) async {
    if (fail) throw const ApiException('offline', offline: true);
    return _weather;
  }

  @override
  Future<RecommendationBundle> dapatkanRekomendasiOtomatis({
    required String ketersediaanAir,
    required String tanamanSebelumnya,
    required String jenisLahan,
    String? kodeWilayah,
  }) async {
    if (fail) throw const ApiException('offline', offline: true);
    return RecommendationBundle.fromJson(_bundleJson);
  }
}

const _weather = CuacaModel(
  desa: 'Aikmel',
  kecamatan: 'Aikmel',
  kabupaten: 'Lombok Timur',
  suhu: 28,
  kelembaban: 78,
  kondisi: 'Cerah',
  kecepatanAngin: 5,
  curahHujan: 1,
  kategoriCurahHujan: 'sedang',
  estimasiCurahHujanBulanan: 150,
  sumberData: 'BMKG',
);

final Map<String, dynamic> _bundleJson = {
  'cuaca': _weather.toJson(),
  'rekomendasi': {
    'input': {'tanamanSebelumnya': 'Padi'},
    'inputSummary': {'tanamanSebelumnya': 'padi'},
    'ruleId': 'ROT-FIXTURE',
    'recommendedCrop': 'jagung',
    'alasan': 'Fixture',
    'rekomendasi': [
      {'prioritas': 1, 'kode': 'jagung', 'nama': 'Jagung'},
    ],
  },
  'kalender': {
    'rencanaMingguan': [],
    'jadwalTanam': [],
    'periode': {},
    'prakiraanCuaca': {},
  },
};

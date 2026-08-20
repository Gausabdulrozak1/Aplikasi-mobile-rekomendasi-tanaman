import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:tani_adaptif/models/cuaca_model.dart';
import 'package:tani_adaptif/models/generate_visual_model.dart';
import 'package:tani_adaptif/models/recommendation_bundle.dart';
import 'package:tani_adaptif/screens/form_lahan_screen.dart';
import 'package:tani_adaptif/screens/hasil_screen.dart';
import 'package:tani_adaptif/screens/riwayat_screen.dart';
import 'package:tani_adaptif/services/local_storage_service.dart';
import 'package:tani_adaptif/services/stable_diffusion_service.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets('land form renders the complete recommendation inputs', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      const MaterialApp(home: FormLahanScreen(cuaca: _weatherFixture)),
    );

    expect(find.text('Input Kondisi Lahan'), findsOneWidget);
    expect(find.text('Tanaman Sebelumnya'), findsOneWidget);
    expect(find.text('Ketersediaan Air'), findsOneWidget);
    expect(find.text('Jenis Lahan'), findsOneWidget);
    expect(find.text('Ringkasan Cuaca BMKG'), findsOneWidget);
    expect(find.text('Proses Rekomendasi'), findsOneWidget);
    expect(find.byType(DropdownButtonFormField<String>), findsNWidgets(3));
  });

  testWidgets('recommendation remains visible when visual generation fails', (
    WidgetTester tester,
  ) async {
    final bundle = RecommendationBundle.fromJson(_resultJson);
    await tester.pumpWidget(
      MaterialApp(
        home: HasilScreen(
          cuaca: bundle.cuaca,
          rekomendasi: bundle.rekomendasi,
          stableDiffusionService: _FailingVisualService(),
        ),
      ),
    );

    expect(find.text('Jagung'), findsWidgets);
    await tester.ensureVisible(find.text('Simulasi Visual'));
    await tester.tap(find.text('Simulasi Visual'));
    await tester.pumpAndSettle();

    expect(find.text('Simulasi Visual'), findsWidgets);
    await tester.ensureVisible(find.text('Buat Simulasi Visual'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Buat Simulasi Visual'));
    await tester.pumpAndSettle();

    expect(
      find.textContaining('Rekomendasi tanaman tetap dapat digunakan'),
      findsOneWidget,
    );
    await tester.pageBack();
    await tester.pumpAndSettle();
    expect(find.text('Jagung'), findsWidgets);
  });

  testWidgets('history page shows saved recommendation details', (
    WidgetTester tester,
  ) async {
    SharedPreferences.setMockInitialValues({
      'visual_generation_history_v1': [
        jsonEncode({
          'id': 'history-1',
          'timestamp': '2026-08-21T10:00:00.000Z',
          'nama_tanaman': 'Jagung',
          'land_type': 'sawah',
          'water_availability': 'cukup',
          'previous_crop': 'padi',
          'rekomendasi_alasan': 'Fixture riwayat.',
        }),
      ],
    });
    final preferences = await SharedPreferences.getInstance();

    await tester.pumpWidget(
      MaterialApp(
        home: RiwayatScreen(
          localStorageService: LocalStorageService(preferences: preferences),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Riwayat Rekomendasi'), findsOneWidget);
    expect(find.text('Jagung'), findsOneWidget);
    expect(find.textContaining('Sawah'), findsOneWidget);
  });
}

class _FailingVisualService extends StableDiffusionService {
  @override
  Future<InferenceModelInfo> getModelInfo() async {
    return const InferenceModelInfo(
      baseModel: 'fixture',
      loraIdentifier: 'none',
      provider: 'fixture',
      supportedCrops: ['jagung'],
    );
  }

  @override
  Future<GenerateVisualResponse> generate(GenerateVisualRequest request) {
    throw const StableDiffusionException('Fixture provider gagal.');
  }
}

final Map<String, dynamic> _resultJson = {
  'cuaca': {
    'lokasi': {'desa': 'Aikmel'},
    'cuacaSaatIni': {'kondisi': 'Cerah', 'suhu': 28},
    'kategoriCurahHujan': 'sedang',
    'sumberData': 'BMKG',
  },
  'rekomendasi': {
    'input': {'tanamanSebelumnya': 'Padi'},
    'inputSummary': {'tanamanSebelumnya': 'padi'},
    'ruleId': 'ROT-FIXTURE',
    'recommendedCrop': 'jagung',
    'alasan': 'Fixture widget test.',
    'rekomendasi': [
      {
        'prioritas': 1,
        'kode': 'jagung',
        'nama': 'Jagung',
        'namaIlmiah': 'Zea mays',
        'keluarga': 'Sereal',
        'hariTumbuh': 90,
        'kebutuhanAir': 'sedang',
        'deskripsi': 'Tanaman fixture.',
      },
    ],
  },
  'kalender': {
    'rencanaMingguan': [],
    'jadwalTanam': [],
    'periode': {},
    'prakiraanCuaca': {},
  },
};

const _weatherFixture = CuacaModel(
  desa: 'Aikmel',
  kecamatan: 'Aikmel',
  kabupaten: 'Lombok Timur',
  suhu: 28,
  kelembaban: 78,
  kondisi: 'Cerah Berawan',
  kecepatanAngin: 5,
  curahHujan: 1,
  kategoriCurahHujan: 'sedang',
  estimasiCurahHujanBulanan: 150,
  sumberData: 'BMKG',
);

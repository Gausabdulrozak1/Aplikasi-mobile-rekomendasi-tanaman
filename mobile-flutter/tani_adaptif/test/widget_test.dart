import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:tani_adaptif/models/generate_visual_model.dart';
import 'package:tani_adaptif/models/recommendation_bundle.dart';
import 'package:tani_adaptif/screens/hasil_screen.dart';
import 'package:tani_adaptif/screens/form_lahan_screen.dart';
import 'package:tani_adaptif/services/stable_diffusion_service.dart';

void main() {
  testWidgets('land form renders the complete recommendation inputs', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(const MaterialApp(home: FormLahanScreen()));

    expect(find.text('Informasi Lahan'), findsOneWidget);
    expect(find.text('Tanaman Sebelumnya'), findsOneWidget);
    expect(find.text('Ketersediaan Air'), findsOneWidget);
    expect(find.text('Jenis Lahan'), findsOneWidget);
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
    await tester.ensureVisible(find.text('Generate Visual'));
    await tester.tap(find.text('Generate Visual'));
    await tester.pumpAndSettle();

    expect(find.text('Jagung'), findsWidgets);
    expect(
      find.textContaining('Rekomendasi tanaman tetap dapat digunakan'),
      findsOneWidget,
    );
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

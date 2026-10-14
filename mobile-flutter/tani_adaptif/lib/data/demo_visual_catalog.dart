class DemoVisualArtifact {
  final String crop;
  final String triggerToken;
  final int seed;
  final String assetPath;
  final String sourcePath;
  final String sha256;
  final String prompt;

  const DemoVisualArtifact({
    required this.crop,
    required this.triggerToken,
    required this.seed,
    required this.assetPath,
    required this.sourcePath,
    required this.sha256,
    required this.prompt,
  });
}

class DemoVisualCatalog {
  static const Map<String, List<DemoVisualArtifact>> byCrop = {
    'padi': [
      DemoVisualArtifact(
        crop: 'padi',
        triggerToken: 'taniadaptif_padi',
        seed: 42,
        assetPath: 'assets/demo_visual/jj.png',
        sourcePath:
            'artifacts/model_evaluation/kaggle_run_20260820T143551Z/generated/evaluation/lora/padi_p1_s42_lora.png',
        sha256:
            'c032c661be9b060fca00e5f5a0dcd562de8b3073261f0cf0e380b5a14f4d0699',
        prompt:
            'a realistic agricultural photograph of taniadaptif_padi, rice plants across a cultivated field, natural daylight',
      ),
      DemoVisualArtifact(
        crop: 'padi',
        triggerToken: 'taniadaptif_padi',
        seed: 0,
        assetPath: 'assets/demo_visual/padi_p1_s42_lora.jpg',
        sourcePath: 'assets/demo_visual/padi_p1_s42_lora.jpg',
        sha256:
            '06d34a708608f6511bbf34899c6cb4805dd9059b6a8102f5fe9a1c236c4fda8b',
        prompt:
            'Foto padi tersimpan sebagai aset demo lokal; bukan hasil inference live.',
      ),
    ],
    'jagung': [
      DemoVisualArtifact(
        crop: 'jagung',
        triggerToken: 'taniadaptif_jagung',
        seed: 42,
        assetPath: 'assets/demo_visual/jagung_p1_s42_lora.png',
        sourcePath:
            'artifacts/model_evaluation/kaggle_run_20260820T143551Z/generated/evaluation/lora/jagung_p1_s42_lora.png',
        sha256:
            '57fa8bcdde32872bf2984ecbc8491aa424bf67b37bdd10bb89b5fda2f066d386',
        prompt:
            'a realistic agricultural photograph of taniadaptif_jagung, maize plants across a cultivated field, natural daylight',
      ),
    ],
    'cabai': [
      DemoVisualArtifact(
        crop: 'cabai',
        triggerToken: 'taniadaptif_cabai',
        seed: 42,
        assetPath: 'assets/demo_visual/cabai_p1_s42_lora.png',
        sourcePath:
            'artifacts/model_evaluation/kaggle_run_20260820T143551Z/generated/evaluation/lora/cabai_p1_s42_lora.png',
        sha256:
            '70f929c8898860a8a5f41044dd8c88728c057c2d0ee77e38aa3599b86ee28616',
        prompt:
            'a realistic agricultural photograph of taniadaptif_cabai, chili plants across a cultivated field, natural daylight',
      ),
    ],
    'kacang_tanah': [
      DemoVisualArtifact(
        crop: 'kacang_tanah',
        triggerToken: 'taniadaptif_kacang_tanah',
        seed: 42,
        assetPath: 'assets/demo_visual/kacang_tanah_p1_s42_lora.png',
        sourcePath:
            'artifacts/model_evaluation/kaggle_run_20260820T143551Z/generated/evaluation/lora/kacang_tanah_p1_s42_lora.png',
        sha256:
            '81237b0bd9d9c6d6e940de68991102baada15ed45e826304474613c87264a2d4',
        prompt:
            'a realistic agricultural photograph of taniadaptif_kacang_tanah, peanut plants across a cultivated field, natural daylight',
      ),
    ],
  };

  static List<DemoVisualArtifact> variantsForCrop(String crop) {
    return byCrop[crop] ?? const <DemoVisualArtifact>[];
  }

  static DemoVisualArtifact? forCrop(String crop) {
    final variants = variantsForCrop(crop);
    return variants.isEmpty ? null : variants.first;
  }
}
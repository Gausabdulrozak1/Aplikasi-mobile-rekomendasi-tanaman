# LAMPIRAN 9
# POTONGAN SOURCE CODE UTAMA

## Lampiran 9.1 Integrasi dan Normalisasi Data BMKG

**Nama file sumber:**  
`backend-nodejs/src/services/bmkgService.js`

```javascript
function prosesDataCuaca(dataBmkg, waktuAmbil = new Date()) {
  const lokasi = dataBmkg.lokasi || {};
  const rawCuaca = dataBmkg.data?.[0]?.cuaca;
  const titikPrakiraan = Array.isArray(rawCuaca)
    ? rawCuaca.flat(Infinity).filter((item) => item && typeof item === 'object')
    : [];

  const semuaPrakiraan = titikPrakiraan.map((point) => ({
    waktu: point.local_datetime || null,
    suhu: angkaAtauNull(point.t),
    kelembaban: angkaAtauNull(point.hu),
    kondisi: point.weather_desc || 'Tidak diketahui',
    kecepatanAngin: angkaAtauNull(point.ws),
    arahAngin: point.wd || '',
    tutupanAwan: angkaAtauNull(point.tcc),
    curahHujan: angkaAtauNull(point.tp),
    jarakPandang: point.vs_text || '',
  }));

  const cuacaSaatIni = semuaPrakiraan[0] || {};
  const dataCurahHujan = semuaPrakiraan
    .map((point) => point.curahHujan)
    .filter((value) => Number.isFinite(value));
  const tanggalPrakiraan = new Set(
    semuaPrakiraan.map((point) => tanggalLokal(point.waktu)).filter(Boolean)
  );
  const jumlahHariPrakiraan = tanggalPrakiraan.size;
  const cakupanLengkap =
    semuaPrakiraan.length > 0 && dataCurahHujan.length === semuaPrakiraan.length;
  const totalCurahHujanPrakiraan = cakupanLengkap
    ? bulatkan(dataCurahHujan.reduce((total, value) => total + value, 0))
    : null;
  const estimasiCurahHujanBulanan =
    cakupanLengkap && jumlahHariPrakiraan > 0
      ? Math.round((totalCurahHujanPrakiraan / jumlahHariPrakiraan) * 30)
      : null;
```

**Keterangan:** Potongan ini meratakan struktur prakiraan BMKG, menormalisasi setiap field cuaca, dan mempertahankan nilai numerik yang tidak tersedia sebagai `null`. Estimasi setara 30 hari hanya dihitung apabila seluruh titik prakiraan memiliki data curah hujan sehingga sistem tidak membuat nilai hujan fiktif.

**Sumber:** Source Code Aplikasi TaniAdaptif, 2026.

## Lampiran 9.2 Rule-Based Engine Rekomendasi Tanaman

**Nama file sumber:**  
`backend-nodejs/src/services/rekomendasiService.js`

```javascript
function dapatkanRekomendasi(input) {
  try {
    const {
      curahHujan,
      ketersediaanAir,
      tanamanSebelumnya,
      jenisLahan,
    } = input;

    logger.info(
      `Memproses rekomendasi: hujan=${curahHujan}, air=${ketersediaanAir}, sebelumnya=${tanamanSebelumnya}`
    );

    // Validasi
    const errors = validasiInput(curahHujan, ketersediaanAir, tanamanSebelumnya, jenisLahan);
    if (errors.length > 0) {
      return { status: 'gagal', errors };
    }

    // Perlakuan khusus: jika air "kurang", anggap seperti "terbatas" untuk pencarian aturan
    const airUntukAturan = ketersediaanAir === 'kurang' ? 'terbatas' : ketersediaanAir;

    // Bentuk kunci untuk cari di decision table
    const kunci = `${curahHujan}_${airUntukAturan}_${tanamanSebelumnya}`;
    logger.info(`Mencari aturan dengan kunci: ${kunci}`);

    const hasilPencarian = cariAturan(kunci);
    const aturan = hasilPencarian.aturan;
    const penyesuaianLahan = sesuaikanUrutanDenganLahan(
      aturan.rekomendasi,
      jenisLahan
    );
    const ruleId = buatRuleId(kunci, jenisLahan, hasilPencarian.menggunakanDefault);
    const tanamanTidakValid = penyesuaianLahan.rekomendasi.filter(
      (kode) => !KODE_TANAMAN_VALID.has(kode)
    );
    if (tanamanTidakValid.length > 0) {
      throw new Error(`Konfigurasi aturan memuat tanaman tidak valid: ${tanamanTidakValid.join(', ')}`);
    }
```

**Keterangan:** Fungsi ini memvalidasi masukan, membentuk kunci decision table dari kategori hujan, ketersediaan air, dan tanaman sebelumnya, lalu menyesuaikan urutan rekomendasi terhadap jenis lahan. Setiap keputusan memperoleh rule ID sehingga keluaran dapat ditelusuri dan diaudit.

**Sumber:** Source Code Aplikasi TaniAdaptif, 2026.

## Lampiran 9.3 Endpoint dan Proxy Inference pada Express

**Nama file sumber:**  
`backend-nodejs/src/routes/visualRoutes.js`

```javascript
router.post('/generate', limitVisualRequests, async (req, res) => {
  const requestId = req.visualRequestId;
  try {
    const selectedCrop = selectedCropFor(req.body);
    const payload = { ...req.body, crop: selectedCrop, request_id: requestId };
    delete payload.selected_crop;
    logger.info(`EXPRESS_SELECTED_CROP=${selectedCrop} request_id=${requestId}`);
    const result = await inferenceService.generate(payload, requestId);
    assertUpstreamCrop(result, selectedCrop);
    const fileName = generatedFileName(result.image_url);
    return res.json({
      ...result,
      request_id: requestId,
      crop: selectedCrop,
      selected_crop: selectedCrop,
      image_url: `${publicBaseUrl(req)}/api/visual/images/${encodeURIComponent(fileName)}`,
      metadata: {
        ...(result.metadata || {}),
        crop: selectedCrop,
        selected_crop: selectedCrop,
        delivery_path: 'backend_proxy',
        upstream_image_url_exposed: false,
      },
    });
  } catch (error) {
    return handleError(res, error, requestId);
  }
});
```

**Keterangan:** Route ini menormalisasi komoditas terpilih, meneruskan request ke layanan inference, memverifikasi bahwa komoditas respons sesuai dengan pilihan pengguna, dan mengganti alamat gambar upstream dengan endpoint proxy Express. Dengan demikian, aplikasi Flutter tidak menerima URL internal layanan GPU.

**Sumber:** Source Code Aplikasi TaniAdaptif, 2026.

## Lampiran 9.4 Mapping Komoditas ke Trigger LoRA dan Prompt FastAPI

**Nama file sumber:**  
`inference_api/app/services/prompt_builder.py`

```python
TRIGGER_TOKENS = {
    "padi": "taniadaptif_padi",
    "jagung": "taniadaptif_jagung",
    "cabai": "taniadaptif_cabai",
    "kacang_tanah": "taniadaptif_kacang_tanah",
}

CROP_VISUAL_PROMPTS = {
    "padi": (
        "commercial agricultural photograph of a wooden bowl overflowing with uncooked "
        "white rice grains beside bundles of golden rice panicles, unmistakable rice "
        "harvest, paddy field background, realistic natural daylight"
    ),
    "jagung": (
        "maize plants in an agricultural environment, natural lighting, clear crop view"
    ),
    "cabai": (
        "chili plants in an agricultural environment, natural lighting, clear crop view"
    ),
    "kacang_tanah": (
        "peanut plants in an agricultural environment, natural lighting, clear crop view"
    ),
}

DEFAULT_NEGATIVE_PROMPT = (
    "illustration, painting, drawing, CGI, blurry, text, logo, watermark"
)

# Bagian lain pada file tidak ditampilkan.

def build_generation_prompt(
    request: GenerateRequest,
    *,
    default_seed: int,
) -> PreparedGenerationRequest:
    trigger = TRIGGER_TOKENS[request.crop]
    crop_visual_prompt = CROP_VISUAL_PROMPTS[request.crop]
    # Keep historical crops and land labels out of the visual prompt: terms such
    # as "rice-field" can overpower the explicitly selected non-rice trigger.
    prompt = f"{trigger}, {crop_visual_prompt}"
    return PreparedGenerationRequest(
        crop=request.crop,
        trigger_token=trigger,
        prompt=prompt,
        negative_prompt=CROP_NEGATIVE_PROMPTS.get(request.crop, DEFAULT_NEGATIVE_PROMPT),
        seed=request.seed if request.seed is not None else default_seed,
```

**Keterangan:** Mapping mempertahankan hubungan tetap antara empat komoditas dan trigger LoRA. Fungsi pembentuk prompt mengambil trigger sesuai komoditas yang dipilih, menambahkan deskripsi visual spesifik, serta mempertahankan seed eksplisit untuk reproduktibilitas atau memakai seed default ketika tidak diberikan.

**Sumber:** Source Code Aplikasi TaniAdaptif, 2026.

## Lampiran 9.5 Request Flutter ke Backend Express

**Nama file sumber:**  
`mobile-flutter/tani_adaptif/lib/services/stable_diffusion_service.dart`

```dart
Future<GenerateVisualResponse> generate(GenerateVisualRequest request) async {
  try {
    debugPrint('FLUTTER_REQUEST_CROP=${request.selectedCrop}');
    final response = await _dio.post(
      'visual/generate',
      data: request.toJson(),
      options: Options(
        headers: {
          'X-Request-ID': request.requestId,
          // Header autentikasi tidak ditampilkan dalam lampiran.
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
  }
}

// Bagian lain pada file tidak ditampilkan.

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
```

**Keterangan:** Service Flutter menyusun payload dari tanaman rekomendasi, kondisi lahan, ringkasan cuaca, seed, dan request ID, lalu mengirimkannya ke endpoint proxy Express. Respons diperiksa kembali agar komoditas gambar sama dengan tanaman yang dipilih sebelum ditampilkan kepada pengguna.

**Sumber:** Source Code Aplikasi TaniAdaptif, 2026.

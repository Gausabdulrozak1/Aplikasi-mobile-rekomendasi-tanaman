import 'package:flutter/material.dart';

import '../config/app_config.dart';
import '../models/cuaca_model.dart';
import '../models/generate_visual_model.dart';
import '../models/rekomendasi_model.dart';
import '../services/local_storage_service.dart';
import '../services/stable_diffusion_service.dart';

class HasilScreen extends StatefulWidget {
  final CuacaModel cuaca;
  final RekomendasiModel rekomendasi;
  final String jenisLahan;
  final String ketersediaanAir;
  final StableDiffusionService? stableDiffusionService;
  final LocalStorageService? localStorageService;

  const HasilScreen({
    super.key,
    required this.cuaca,
    required this.rekomendasi,
    this.jenisLahan = 'sawah',
    this.ketersediaanAir = 'cukup',
    this.stableDiffusionService,
    this.localStorageService,
  });

  @override
  State<HasilScreen> createState() => _HasilScreenState();
}

class _HasilScreenState extends State<HasilScreen> {
  late final StableDiffusionService _stableDiffusionService;
  late final LocalStorageService _localStorageService;

  bool _isLoadingAI = false;
  String? _aiPrompt;
  String? _aiImageUrl;
  String? _aiModel;
  int _aiSeed = 42;
  String? _aiError;
  String? _aiRequestId;
  String? _inferenceProvider;
  String? _loraIdentifier;

  @override
  void initState() {
    super.initState();
    _stableDiffusionService =
        widget.stableDiffusionService ?? StableDiffusionService();
    _localStorageService =
        widget.localStorageService ?? const LocalStorageService();
    _loadModelInfo();
  }

  Future<void> _loadModelInfo() async {
    try {
      final info = await _stableDiffusionService.getModelInfo();
      if (!mounted) return;
      setState(() {
        _inferenceProvider = info.provider;
        _loraIdentifier = info.loraIdentifier;
      });
    } catch (_) {
      // Model info is supplementary; recommendation and generation stay usable.
    }
  }

  Future<void> _generateSimulasiAI() async {
    if (widget.rekomendasi.rekomendasi.isEmpty) return;

    setState(() {
      _isLoadingAI = true;
      _aiError = null;
      _aiImageUrl = null;
      _aiModel = null;
    });

    final tanamanUtama = widget.rekomendasi.rekomendasi.first;
    final request = _stableDiffusionService.buildRequest(
      tanaman: tanamanUtama,
      cuaca: widget.cuaca,
      jenisLahan: widget.jenisLahan,
      ketersediaanAir: widget.ketersediaanAir,
      tanamanSebelumnya: widget.rekomendasi.tanamanSebelumnyaKode,
      seed: _aiSeed,
    );

    try {
      final response = await _stableDiffusionService.generate(request);
      await _simpanRiwayatVisual(request, response, tanamanUtama);
      if (!mounted) return;
      setState(() {
        _aiPrompt = response.metadata['prompt']?.toString();
        _aiImageUrl = response.imageUrl;
        _aiModel = response.model;
        _aiSeed = response.seed;
        _aiRequestId = response.requestId;
        _inferenceProvider = response.metadata['provider']?.toString();
        _loraIdentifier = response.metadata['lora_identifier']?.toString();
        _isLoadingAI = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _aiError = e is StableDiffusionException
            ? '${e.message} Rekomendasi tanaman tetap dapat digunakan.'
            : 'Simulasi visual belum tersedia. Rekomendasi tanaman tetap dapat digunakan.';
        _isLoadingAI = false;
      });
    }
  }

  Future<void> _simpanRiwayatVisual(
    GenerateVisualRequest request,
    GenerateVisualResponse response,
    TanamanRekomendasi tanaman,
  ) async {
    await _localStorageService.saveVisualHistory({
      'timestamp': DateTime.now().toIso8601String(),
      'tanaman': tanaman.kode,
      'nama_tanaman': tanaman.nama,
      'land_type': request.landType,
      'water_availability': request.waterAvailability,
      'previous_crop': request.previousCrop,
      'weather_summary': request.weatherSummary,
      'prompt': response.metadata['prompt'],
      'negative_prompt': response.metadata['negative_prompt'],
      'seed': response.seed,
      'request_id': response.requestId,
      'image_url': response.imageUrl,
      'image_id': response.imageId,
      'model': response.model,
      'rekomendasi_alasan': widget.rekomendasi.alasan,
      'rule_id': widget.rekomendasi.ruleId,
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Hasil Rekomendasi')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _buildRingkasanCuaca(),
            const SizedBox(height: 24),
            const Text(
              'Rekomendasi Tanaman',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 4),
            Text(
              'Setelah ${widget.rekomendasi.tanamanSebelumnya}',
              style: TextStyle(fontSize: 13, color: AppColors.grey),
            ),
            const SizedBox(height: 16),
            if (widget.rekomendasi.rekomendasi.isEmpty)
              _buildRekomendasiKosong()
            else
              ...widget.rekomendasi.rekomendasi.map(_buildKartuTanaman),
            if (widget.rekomendasi.memilikiKalender) ...[
              const SizedBox(height: 12),
              _buildKalenderBulanan(),
              const SizedBox(height: 16),
              _buildJadwalTanam(),
            ],
            const SizedBox(height: 16),
            _buildAlasan(),
            const SizedBox(height: 16),
            _buildSimulasiAI(),
          ],
        ),
      ),
    );
  }

  Widget _buildRingkasanCuaca() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.primaryLightest,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        children: [
          const Icon(Icons.cloud, color: AppColors.primary, size: 32),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Cuaca ${widget.cuaca.desa}: ${widget.cuaca.kondisi}',
                  style: const TextStyle(fontWeight: FontWeight.w600),
                ),
                Text(
                  'Suhu ${widget.cuaca.suhu?.toStringAsFixed(0) ?? 'tidak tersedia'} C - Curah hujan ${widget.cuaca.kategoriCurahHujan ?? 'tidak tersedia'}',
                  style: TextStyle(fontSize: 12, color: AppColors.grey),
                ),
                const SizedBox(height: 4),
                Text(
                  [
                    'Sumber: ${widget.cuaca.sumberData}',
                    if (widget.cuaca.waktuData != null)
                      'Data: ${widget.cuaca.waktuData}',
                    if (widget.cuaca.isStale) 'cache terakhir',
                  ].join(' - '),
                  style: TextStyle(fontSize: 10, color: AppColors.grey),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildRekomendasiKosong() {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.warning.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(8),
      ),
      child: const Row(
        children: [
          Icon(Icons.info_outline, color: AppColors.warning),
          SizedBox(width: 8),
          Expanded(child: Text('Belum ada tanaman yang dapat ditampilkan.')),
        ],
      ),
    );
  }

  Widget _buildAlasan() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.info.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.lightbulb, color: AppColors.info, size: 20),
              const SizedBox(width: 8),
              const Text(
                'Alasan Rekomendasi',
                style: TextStyle(fontWeight: FontWeight.bold),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            widget.rekomendasi.alasan,
            style: const TextStyle(fontSize: 13, height: 1.5),
          ),
          if (widget.rekomendasi.ruleId.isNotEmpty) ...[
            const SizedBox(height: 8),
            Text(
              'Rule ID: ${widget.rekomendasi.ruleId}',
              style: const TextStyle(fontSize: 11, color: AppColors.grey),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildKalenderBulanan() {
    final periode = widget.rekomendasi.periode;
    final periodeText = periode.mulai.isNotEmpty && periode.selesai.isNotEmpty
        ? '${_formatTanggal(periode.mulai)} - ${_formatTanggal(periode.selesai)}'
        : periode.durasi;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            const Icon(
              Icons.calendar_month,
              color: AppColors.primary,
              size: 22,
            ),
            const SizedBox(width: 8),
            const Expanded(
              child: Text(
                'Kalender Rekomendasi 1 Bulan',
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
              ),
            ),
          ],
        ),
        if (periodeText.isNotEmpty) ...[
          const SizedBox(height: 4),
          Text(
            periodeText,
            style: TextStyle(fontSize: 12, color: AppColors.grey),
          ),
        ],
        if (widget.rekomendasi.catatanPrakiraan.isNotEmpty) ...[
          const SizedBox(height: 12),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: AppColors.warning.withValues(alpha: 0.12),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Icon(
                  Icons.info_outline,
                  size: 18,
                  color: AppColors.warning,
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    widget.rekomendasi.catatanPrakiraan,
                    style: const TextStyle(fontSize: 12, height: 1.4),
                  ),
                ),
              ],
            ),
          ),
        ],
        const SizedBox(height: 12),
        ...widget.rekomendasi.rencanaMingguan.map(_buildKartuMingguan),
      ],
    );
  }

  Widget _buildKartuMingguan(RencanaMingguan rencana) {
    final warnaHujan = _warnaKategoriHujan(
      rencana.profilCuaca.kategoriCurahHujan,
    );

    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.greyLight),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                width: 44,
                height: 44,
                decoration: BoxDecoration(
                  color: AppColors.primaryLightest,
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Center(
                  child: Text(
                    'M${rencana.minggu}',
                    style: const TextStyle(
                      color: AppColors.primary,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      rencana.judulTahap,
                      style: const TextStyle(
                        fontWeight: FontWeight.bold,
                        fontSize: 15,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      '${_formatTanggal(rencana.tanggalMulai)} - ${_formatTanggal(rencana.tanggalSelesai)}',
                      style: TextStyle(fontSize: 12, color: AppColors.grey),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              _buildInfoChip(
                Icons.water_drop_outlined,
                'Hujan ${rencana.profilCuaca.kategoriCurahHujan}',
                warnaHujan,
              ),
              _buildInfoChip(
                Icons.cloud_outlined,
                rencana.profilCuaca.kondisiDominan,
                AppColors.info,
              ),
              if (rencana.profilCuaca.tingkatKeyakinan.isNotEmpty)
                _buildInfoChip(
                  Icons.analytics_outlined,
                  'Keyakinan ${rencana.profilCuaca.tingkatKeyakinan}',
                  AppColors.grey,
                ),
            ],
          ),
          const SizedBox(height: 12),
          Text(
            'Tanaman utama: ${rencana.tanamanPrioritas.nama}',
            style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13),
          ),
          if (rencana.profilCuaca.estimasiCurahHujanMingguan > 0) ...[
            const SizedBox(height: 6),
            Text(
              'Estimasi hujan minggu ini ${rencana.profilCuaca.estimasiCurahHujanMingguan.toStringAsFixed(1)} mm, suhu rata-rata ${rencana.profilCuaca.suhuRataRata.toStringAsFixed(1)} C.',
              style: TextStyle(fontSize: 12, color: AppColors.grey),
            ),
          ],
          if (rencana.catatanCuaca.isNotEmpty) ...[
            const SizedBox(height: 8),
            Text(
              rencana.catatanCuaca,
              style: const TextStyle(fontSize: 12, height: 1.4),
            ),
          ],
          const SizedBox(height: 10),
          ...rencana.kegiatan.daftar.map(
            (item) => Padding(
              padding: const EdgeInsets.only(bottom: 6),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Icon(
                    Icons.check_circle_outline,
                    size: 16,
                    color: AppColors.primary,
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      item,
                      style: const TextStyle(fontSize: 12, height: 1.35),
                    ),
                  ),
                ],
              ),
            ),
          ),
          if (rencana.kegiatan.catatan.isNotEmpty) ...[
            const SizedBox(height: 4),
            Text(
              rencana.kegiatan.catatan,
              style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600),
            ),
          ],
          if (rencana.profilCuaca.sumber.isNotEmpty) ...[
            const SizedBox(height: 8),
            Text(
              rencana.profilCuaca.sumber,
              style: TextStyle(fontSize: 11, color: AppColors.grey),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildJadwalTanam() {
    if (widget.rekomendasi.jadwalTanam.isEmpty) {
      return const SizedBox.shrink();
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            const Icon(
              Icons.event_available,
              color: AppColors.primary,
              size: 22,
            ),
            const SizedBox(width: 8),
            const Expanded(
              child: Text(
                'Jadwal Tanam dan Panen',
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
              ),
            ),
          ],
        ),
        const SizedBox(height: 12),
        ...widget.rekomendasi.jadwalTanam.map(_buildKartuJadwalTanam),
      ],
    );
  }

  Widget _buildKartuJadwalTanam(JadwalTanam jadwal) {
    final isUtama = jadwal.tipe == 'utama';

    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: isUtama ? AppColors.primaryLightest : Colors.white,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: isUtama ? AppColors.primaryLight : AppColors.greyLight,
        ),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 36,
            height: 36,
            decoration: BoxDecoration(
              color: isUtama ? AppColors.primary : AppColors.greyLight,
              borderRadius: BorderRadius.circular(8),
            ),
            child: Center(
              child: Text(
                '${jadwal.prioritas}',
                style: TextStyle(
                  color: isUtama ? Colors.white : AppColors.black,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Wrap(
                  spacing: 8,
                  runSpacing: 4,
                  crossAxisAlignment: WrapCrossAlignment.center,
                  children: [
                    Text(
                      jadwal.tanaman,
                      style: const TextStyle(
                        fontWeight: FontWeight.bold,
                        fontSize: 15,
                      ),
                    ),
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 8,
                        vertical: 2,
                      ),
                      decoration: BoxDecoration(
                        color: isUtama
                            ? Colors.white.withValues(alpha: 0.8)
                            : AppColors.primaryLightest,
                        borderRadius: BorderRadius.circular(6),
                      ),
                      child: Text(
                        isUtama ? 'Utama' : 'Alternatif',
                        style: const TextStyle(
                          fontSize: 10,
                          color: AppColors.primary,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 6),
                Text(
                  'Tanam ${_formatTanggal(jadwal.tanggalTanam)} - Panen ${_formatTanggal(jadwal.estimasiPanen)}',
                  style: const TextStyle(fontSize: 12),
                ),
                const SizedBox(height: 4),
                Text(
                  '${jadwal.hariTumbuh} hari tumbuh - Air ${jadwal.kebutuhanAir}',
                  style: TextStyle(fontSize: 11, color: AppColors.grey),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildInfoChip(IconData icon, String text, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 5),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 14, color: color),
          const SizedBox(width: 4),
          ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 220),
            child: Text(
              text,
              style: TextStyle(
                color: color,
                fontSize: 11,
                fontWeight: FontWeight.w600,
              ),
              softWrap: true,
            ),
          ),
        ],
      ),
    );
  }

  Color _warnaKategoriHujan(String kategori) {
    switch (kategori) {
      case 'tinggi':
        return AppColors.info;
      case 'rendah':
        return AppColors.warning;
      default:
        return AppColors.success;
    }
  }

  String _formatTanggal(String value) {
    final tanggal = DateTime.tryParse(value);
    if (tanggal == null) return value;

    final hari = tanggal.day.toString().padLeft(2, '0');
    final bulan = tanggal.month.toString().padLeft(2, '0');
    return '$hari/$bulan/${tanggal.year}';
  }

  Widget _buildSimulasiAI() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'Simulasi Visual',
          style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 12),
        Container(
          width: double.infinity,
          padding: const EdgeInsets.all(20),
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: AppColors.greyLight),
          ),
          child: _buildKontenSimulasi(),
        ),
      ],
    );
  }

  Widget _buildKontenSimulasi() {
    if (_isLoadingAI) {
      return const SizedBox(
        height: 100,
        child: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              CircularProgressIndicator(),
              SizedBox(height: 8),
              Text(
                'Menunggu provider simulasi visual...',
                style: TextStyle(fontSize: 12, color: AppColors.grey),
              ),
            ],
          ),
        ),
      );
    }

    if (_aiError != null) {
      return Column(
        children: [
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: AppColors.danger.withValues(alpha: 0.1),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Column(
              children: [
                const Icon(
                  Icons.info_outline,
                  size: 40,
                  color: AppColors.warning,
                ),
                const SizedBox(height: 8),
                Text(
                  _aiError!,
                  textAlign: TextAlign.center,
                  style: TextStyle(fontSize: 12, color: AppColors.grey),
                ),
                const SizedBox(height: 12),
                OutlinedButton.icon(
                  onPressed: _generateSimulasiAI,
                  icon: const Icon(Icons.refresh),
                  label: const Text('Coba Lagi'),
                ),
              ],
            ),
          ),
          if (widget.rekomendasi.rekomendasi.isNotEmpty) ...[
            const SizedBox(height: 12),
            Container(
              height: 120,
              decoration: BoxDecoration(
                color: AppColors.primaryLightest,
                borderRadius: BorderRadius.circular(8),
              ),
              child: Center(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    const Icon(Icons.eco, size: 40, color: AppColors.primary),
                    Text(
                      widget.rekomendasi.rekomendasi.first.nama,
                      style: const TextStyle(
                        fontWeight: FontWeight.bold,
                        fontSize: 14,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ],
      );
    }

    if (_aiImageUrl != null && _aiImageUrl!.isNotEmpty) {
      return Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: AppColors.primaryLightest,
          borderRadius: BorderRadius.circular(12),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(
                  Icons.auto_awesome,
                  color: AppColors.primary,
                  size: 24,
                ),
                const SizedBox(width: 8),
                const Expanded(
                  child: Text(
                    'Simulasi Tanaman',
                    style: TextStyle(
                      color: AppColors.primary,
                      fontWeight: FontWeight.bold,
                      fontSize: 14,
                    ),
                  ),
                ),
                IconButton(
                  onPressed: _generateSimulasiAI,
                  icon: const Icon(Icons.refresh, color: AppColors.primary),
                  tooltip: 'Generate ulang',
                ),
              ],
            ),
            const SizedBox(height: 12),
            ClipRRect(
              borderRadius: BorderRadius.circular(10),
              child: AspectRatio(
                aspectRatio: 1,
                child: Image.network(
                  _aiImageUrl!,
                  headers: AppConfig.visualImageHeaders,
                  fit: BoxFit.cover,
                  errorBuilder: (context, error, stackTrace) {
                    return Container(
                      color: Colors.white.withValues(alpha: 0.7),
                      child: const Center(
                        child: Icon(
                          Icons.broken_image,
                          color: AppColors.grey,
                          size: 48,
                        ),
                      ),
                    );
                  },
                ),
              ),
            ),
            const SizedBox(height: 12),
            if (_aiModel != null && _aiModel!.isNotEmpty)
              Text(
                'Model: $_aiModel - Seed: $_aiSeed',
                style: TextStyle(fontSize: 11, color: AppColors.grey),
              ),
            if (_inferenceProvider != null || _aiRequestId != null) ...[
              const SizedBox(height: 4),
              Text(
                [
                  if (_inferenceProvider != null)
                    'Provider: $_inferenceProvider',
                  if (_loraIdentifier != null && _loraIdentifier!.isNotEmpty)
                    'LoRA: $_loraIdentifier',
                  if (_aiRequestId != null) 'Request: $_aiRequestId',
                ].join(' - '),
                style: TextStyle(fontSize: 10, color: AppColors.grey),
              ),
            ],
            const SizedBox(height: 8),
            if (_aiPrompt != null && _aiPrompt!.isNotEmpty)
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: Colors.white.withValues(alpha: 0.7),
                  borderRadius: BorderRadius.circular(6),
                ),
                child: Text(
                  'Prompt: $_aiPrompt',
                  style: TextStyle(fontSize: 10, color: AppColors.grey),
                ),
              ),
          ],
        ),
      );
    }

    return Column(
      children: [
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: AppColors.primaryLightest,
            borderRadius: BorderRadius.circular(12),
          ),
          child: Column(
            children: [
              const Icon(Icons.eco, size: 44, color: AppColors.primary),
              const SizedBox(height: 8),
              const Text(
                'Buat simulasi visual dari rekomendasi tanaman utama.',
                textAlign: TextAlign.center,
                style: TextStyle(fontSize: 13),
              ),
              const SizedBox(height: 12),
              if (_inferenceProvider != null)
                Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: Text(
                    'Provider: $_inferenceProvider',
                    style: const TextStyle(fontSize: 11, color: AppColors.grey),
                  ),
                ),
              ElevatedButton.icon(
                onPressed: _generateSimulasiAI,
                icon: const Icon(Icons.auto_awesome),
                label: const Text('Generate Visual'),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildKartuTanaman(TanamanRekomendasi t) {
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.greyLight),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.05),
            blurRadius: 8,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Row(
        children: [
          Container(
            width: 44,
            height: 44,
            decoration: BoxDecoration(
              color: AppColors.primary,
              borderRadius: BorderRadius.circular(10),
            ),
            child: Center(
              child: Text(
                '${t.prioritas}',
                style: const TextStyle(
                  color: Colors.white,
                  fontWeight: FontWeight.bold,
                  fontSize: 18,
                ),
              ),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Wrap(
                  spacing: 8,
                  runSpacing: 4,
                  crossAxisAlignment: WrapCrossAlignment.center,
                  children: [
                    Text(
                      t.nama,
                      style: const TextStyle(
                        fontWeight: FontWeight.bold,
                        fontSize: 16,
                      ),
                    ),
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 8,
                        vertical: 2,
                      ),
                      decoration: BoxDecoration(
                        color: AppColors.primaryLightest,
                        borderRadius: BorderRadius.circular(6),
                      ),
                      child: Text(
                        t.keluarga,
                        style: const TextStyle(
                          fontSize: 10,
                          color: AppColors.primary,
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 4),
                Text(
                  t.deskripsi,
                  style: TextStyle(fontSize: 12, color: AppColors.grey),
                ),
                const SizedBox(height: 6),
                Row(
                  children: [
                    Icon(Icons.schedule, size: 12, color: AppColors.grey),
                    const SizedBox(width: 4),
                    Text(
                      '${t.hariTumbuh} hari',
                      style: TextStyle(fontSize: 11, color: AppColors.grey),
                    ),
                    const SizedBox(width: 12),
                    Icon(Icons.water_drop, size: 12, color: AppColors.grey),
                    const SizedBox(width: 4),
                    Text(
                      'Air ${t.kebutuhanAir}',
                      style: TextStyle(fontSize: 11, color: AppColors.grey),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

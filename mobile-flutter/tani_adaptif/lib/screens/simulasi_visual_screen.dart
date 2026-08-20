import 'package:flutter/material.dart';

import '../config/app_config.dart';
import '../models/cuaca_model.dart';
import '../models/generate_visual_model.dart';
import '../models/rekomendasi_model.dart';
import '../services/local_storage_service.dart';
import '../services/stable_diffusion_service.dart';

class SimulasiVisualScreen extends StatefulWidget {
  final CuacaModel cuaca;
  final RekomendasiModel rekomendasi;
  final String jenisLahan;
  final String ketersediaanAir;
  final String historyId;
  final StableDiffusionService? stableDiffusionService;
  final LocalStorageService? localStorageService;

  const SimulasiVisualScreen({
    super.key,
    required this.cuaca,
    required this.rekomendasi,
    required this.jenisLahan,
    required this.ketersediaanAir,
    required this.historyId,
    this.stableDiffusionService,
    this.localStorageService,
  });

  @override
  State<SimulasiVisualScreen> createState() => _SimulasiVisualScreenState();
}

class _SimulasiVisualScreenState extends State<SimulasiVisualScreen> {
  late final StableDiffusionService _stableDiffusionService;
  late final LocalStorageService _localStorageService;

  bool _isLoading = false;
  bool _isSaved = false;
  String? _error;
  GenerateVisualResponse? _response;
  String? _provider;
  String? _loraIdentifier;

  TanamanRekomendasi? get _tanaman => widget.rekomendasi.rekomendasi.isEmpty
      ? null
      : widget.rekomendasi.rekomendasi.first;

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
        _provider = info.provider;
        _loraIdentifier = info.loraIdentifier;
      });
    } catch (_) {
      // Informasi model bersifat pelengkap dan tidak mengubah rekomendasi.
    }
  }

  Future<void> _generate() async {
    final tanaman = _tanaman;
    if (tanaman == null) return;

    setState(() {
      _isLoading = true;
      _isSaved = false;
      _error = null;
      _response = null;
    });

    final request = _stableDiffusionService.buildRequest(
      tanaman: tanaman,
      cuaca: widget.cuaca,
      jenisLahan: widget.jenisLahan,
      ketersediaanAir: widget.ketersediaanAir,
      tanamanSebelumnya: widget.rekomendasi.tanamanSebelumnyaKode,
      seed: 42,
    );

    try {
      final response = await _stableDiffusionService.generate(request);
      if (!mounted) return;
      setState(() {
        _response = response;
        _provider = response.metadata['provider']?.toString() ?? _provider;
        _loraIdentifier =
            response.metadata['lora_identifier']?.toString() ?? _loraIdentifier;
        _isLoading = false;
      });
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _error = error is StableDiffusionException
            ? error.message
            : 'Simulasi visual belum dapat dibuat.';
        _isLoading = false;
      });
    }
  }

  Future<void> _saveToHistory() async {
    final tanaman = _tanaman;
    final response = _response;
    if (tanaman == null || response == null) return;

    await _localStorageService.saveVisualHistory({
      'id': widget.historyId,
      'timestamp': DateTime.now().toIso8601String(),
      'tanaman': tanaman.kode,
      'nama_tanaman': tanaman.nama,
      'land_type': widget.jenisLahan,
      'water_availability': widget.ketersediaanAir,
      'previous_crop': widget.rekomendasi.tanamanSebelumnyaKode,
      'weather_summary': _weatherSummary(),
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
    if (!mounted) return;
    setState(() => _isSaved = true);
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Visual tersimpan di riwayat.')),
    );
  }

  @override
  Widget build(BuildContext context) {
    final tanaman = _tanaman;
    return Scaffold(
      appBar: AppBar(title: const Text('Simulasi Visual')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          const Text(
            'Tanaman Rekomendasi',
            style: TextStyle(fontSize: 13, color: AppColors.grey),
          ),
          const SizedBox(height: 6),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: AppColors.primaryLightest,
              borderRadius: BorderRadius.circular(8),
            ),
            child: Row(
              children: [
                const Icon(Icons.eco, color: AppColors.primary, size: 34),
                const SizedBox(width: 12),
                Expanded(
                  child: Text(
                    tanaman?.nama ?? 'Belum tersedia',
                    style: const TextStyle(
                      fontSize: 20,
                      fontWeight: FontWeight.bold,
                      color: AppColors.primary,
                    ),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 20),
          Text(
            'Gambar Simulasi',
            style: Theme.of(
              context,
            ).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 10),
          _buildVisualArea(),
          const SizedBox(height: 16),
          Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: AppColors.info.withValues(alpha: 0.08),
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: AppColors.info.withValues(alpha: 0.2)),
            ),
            child: const Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Icon(Icons.info_outline, size: 20, color: AppColors.info),
                SizedBox(width: 10),
                Expanded(
                  child: Text(
                    'Stable Diffusion 1.5 dan LoRA hanya membuat simulasi visual. Rekomendasi tanaman tetap berasal dari rule-based engine.',
                    style: TextStyle(fontSize: 12, height: 1.45),
                  ),
                ),
              ],
            ),
          ),
          if (_response != null) ...[
            const SizedBox(height: 16),
            FilledButton.icon(
              onPressed: _isSaved ? null : _saveToHistory,
              icon: Icon(_isSaved ? Icons.check : Icons.bookmark_add_outlined),
              label: Text(
                _isSaved ? 'Tersimpan di Riwayat' : 'Simpan ke Riwayat',
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildVisualArea() {
    return AspectRatio(
      aspectRatio: 1,
      child: Container(
        width: double.infinity,
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: AppColors.greyLight),
        ),
        clipBehavior: Clip.antiAlias,
        child: _buildVisualContent(),
      ),
    );
  }

  Widget _buildVisualContent() {
    if (_isLoading) {
      return const Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            CircularProgressIndicator(),
            SizedBox(height: 14),
            Text('Membuat simulasi visual...'),
            SizedBox(height: 4),
            Text(
              'Proses GPU dapat memerlukan beberapa saat.',
              style: TextStyle(fontSize: 11, color: AppColors.grey),
            ),
          ],
        ),
      );
    }

    if (_error != null) {
      return Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(
              Icons.cloud_off_outlined,
              size: 48,
              color: AppColors.danger,
            ),
            const SizedBox(height: 12),
            Text(
              _error!,
              textAlign: TextAlign.center,
              style: const TextStyle(fontSize: 13),
            ),
            const SizedBox(height: 6),
            const Text(
              'Rekomendasi tanaman tetap dapat digunakan.',
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 11, color: AppColors.grey),
            ),
            const SizedBox(height: 16),
            OutlinedButton.icon(
              onPressed: _generate,
              icon: const Icon(Icons.refresh),
              label: const Text('Coba Lagi'),
            ),
          ],
        ),
      );
    }

    final response = _response;
    if (response != null && response.imageUrl.isNotEmpty) {
      return Stack(
        fit: StackFit.expand,
        children: [
          Image.network(
            response.imageUrl,
            headers: AppConfig.visualImageHeaders,
            fit: BoxFit.cover,
            errorBuilder: (_, _, _) => const Center(
              child: Icon(
                Icons.broken_image_outlined,
                size: 52,
                color: AppColors.grey,
              ),
            ),
          ),
          Positioned(
            top: 8,
            right: 8,
            child: IconButton.filledTonal(
              onPressed: _generate,
              icon: const Icon(Icons.refresh),
              tooltip: 'Buat ulang',
            ),
          ),
          Positioned(
            left: 8,
            right: 56,
            bottom: 8,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
              decoration: BoxDecoration(
                color: Colors.black.withValues(alpha: 0.68),
                borderRadius: BorderRadius.circular(6),
              ),
              child: Text(
                [
                  ?_provider,
                  ?_loraIdentifier,
                  'Seed ${response.seed}',
                ].join(' | '),
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(color: Colors.white, fontSize: 10),
              ),
            ),
          ),
        ],
      );
    }

    return Column(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        const Icon(Icons.image_outlined, size: 58, color: AppColors.primary),
        const SizedBox(height: 12),
        const Padding(
          padding: EdgeInsets.symmetric(horizontal: 24),
          child: Text(
            'Buat gambaran visual untuk tanaman rekomendasi utama.',
            textAlign: TextAlign.center,
            style: TextStyle(fontSize: 13),
          ),
        ),
        const SizedBox(height: 16),
        FilledButton.icon(
          onPressed: _tanaman == null ? null : _generate,
          icon: const Icon(Icons.auto_awesome),
          label: const Text('Buat Simulasi Visual'),
        ),
        if (_provider != null) ...[
          const SizedBox(height: 10),
          Text(
            'Provider: $_provider',
            style: const TextStyle(fontSize: 10, color: AppColors.grey),
          ),
        ],
      ],
    );
  }

  String _weatherSummary() {
    final details = <String>[widget.cuaca.kondisi];
    if (widget.cuaca.suhu != null) {
      details.add('${widget.cuaca.suhu!.toStringAsFixed(0)} C');
    }
    if (widget.cuaca.kategoriCurahHujan != null) {
      details.add('hujan ${widget.cuaca.kategoriCurahHujan}');
    }
    return details.join(', ');
  }
}

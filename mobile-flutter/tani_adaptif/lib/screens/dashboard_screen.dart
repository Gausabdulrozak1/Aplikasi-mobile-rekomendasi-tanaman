import 'package:flutter/material.dart';

import '../config/app_config.dart';
import '../models/cuaca_model.dart';
import '../repositories/tani_adaptif_repository.dart';
import 'form_lahan_screen.dart';

class DashboardScreen extends StatefulWidget {
  final TaniAdaptifRepository? repository;

  const DashboardScreen({super.key, this.repository});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  late final TaniAdaptifRepository _repository;
  CuacaModel? _cuaca;
  bool _isLoading = true;
  String? _error;
  String? _notice;

  @override
  void initState() {
    super.initState();
    _repository = widget.repository ?? TaniAdaptifRepository();
    _muatCuaca();
  }

  Future<void> _muatCuaca() async {
    setState(() {
      _isLoading = true;
      _error = null;
      _notice = null;
    });

    try {
      final result = await _repository.getWeather();
      if (!mounted) return;
      setState(() {
        _cuaca = result.data;
        _notice = result.notice;
        _isLoading = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _error =
            'Cuaca belum dapat dimuat. Periksa koneksi dan layanan backend.';
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('TaniAdaptif'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _isLoading ? null : _muatCuaca,
            tooltip: 'Muat ulang cuaca',
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _muatCuaca,
        child: SingleChildScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _buildSapaan(),
              const SizedBox(height: 20),
              if (_notice != null) ...[
                _buildNotice(_notice!),
                const SizedBox(height: 12),
              ],
              _buildKontenCuaca(),
              const SizedBox(height: 24),
              _buildTombolRekomendasi(),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildSapaan() {
    final jam = DateTime.now().hour;
    final sapaan = jam < 11
        ? 'Selamat Pagi'
        : jam < 15
        ? 'Selamat Siang'
        : jam < 18
        ? 'Selamat Sore'
        : 'Selamat Malam';

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          '$sapaan, Petani',
          style: const TextStyle(fontSize: 22, fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 4),
        const Text(
          'Informasi cuaca dan rekomendasi tanam untuk Anda',
          style: TextStyle(fontSize: 13, color: AppColors.grey),
        ),
      ],
    );
  }

  Widget _buildNotice(String message) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppColors.warning.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        children: [
          const Icon(Icons.offline_bolt, color: AppColors.warning, size: 20),
          const SizedBox(width: 8),
          Expanded(child: Text(message, style: const TextStyle(fontSize: 12))),
        ],
      ),
    );
  }

  Widget _buildKontenCuaca() {
    if (_isLoading) {
      return const SizedBox(
        height: 220,
        child: Center(child: CircularProgressIndicator()),
      );
    }

    if (_error != null || _cuaca == null) {
      return Container(
        width: double.infinity,
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          color: AppColors.danger.withValues(alpha: 0.1),
          borderRadius: BorderRadius.circular(8),
        ),
        child: Column(
          children: [
            const Icon(Icons.cloud_off, size: 48, color: AppColors.danger),
            const SizedBox(height: 12),
            Text(_error ?? 'Data cuaca kosong.', textAlign: TextAlign.center),
            const SizedBox(height: 12),
            ElevatedButton.icon(
              onPressed: _muatCuaca,
              icon: const Icon(Icons.refresh),
              label: const Text('Coba Lagi'),
            ),
          ],
        ),
      );
    }

    return _buildKartuCuaca(_cuaca!);
  }

  Widget _buildKartuCuaca(CuacaModel cuaca) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: AppColors.primary,
        borderRadius: BorderRadius.circular(8),
        boxShadow: [
          BoxShadow(
            color: AppColors.primary.withValues(alpha: 0.25),
            blurRadius: 10,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.location_on, color: Colors.white, size: 18),
              const SizedBox(width: 4),
              Expanded(
                child: Text(
                  '${cuaca.desa}, ${cuaca.kecamatan}',
                  style: const TextStyle(
                    color: Colors.white,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
              const Icon(Icons.cloud_outlined, color: Colors.white, size: 42),
            ],
          ),
          Text(
            cuaca.kondisi,
            style: const TextStyle(color: Colors.white70, fontSize: 13),
          ),
          const SizedBox(height: 14),
          Text(
            cuaca.suhu == null
                ? 'Suhu tidak tersedia'
                : '${cuaca.suhu!.toStringAsFixed(0)} C',
            style: const TextStyle(
              color: Colors.white,
              fontSize: 42,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 14),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceAround,
            children: [
              _infoCuaca(
                Icons.water_drop,
                'Kelembaban',
                _number(cuaca.kelembaban, suffix: '%'),
              ),
              _infoCuaca(
                Icons.air,
                'Angin',
                _number(cuaca.kecepatanAngin, suffix: ' km/j'),
              ),
              _infoCuaca(
                Icons.umbrella,
                'Hujan',
                cuaca.kategoriCurahHujan ?? 'Tidak tersedia',
              ),
            ],
          ),
          const SizedBox(height: 16),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
            decoration: BoxDecoration(
              color: Colors.white.withValues(alpha: 0.18),
              borderRadius: BorderRadius.circular(6),
            ),
            child: Text(
              [
                'Sumber: ${cuaca.sumberData}',
                if (cuaca.waktuData != null) 'Data: ${cuaca.waktuData}',
                if (cuaca.isStale) 'cache terakhir',
              ].join(' - '),
              style: const TextStyle(color: Colors.white, fontSize: 10),
            ),
          ),
        ],
      ),
    );
  }

  Widget _infoCuaca(IconData icon, String label, String value) {
    return Flexible(
      child: Column(
        children: [
          Icon(icon, color: Colors.white, size: 24),
          const SizedBox(height: 4),
          Text(
            label,
            style: const TextStyle(color: Colors.white70, fontSize: 10),
          ),
          const SizedBox(height: 2),
          Text(
            value,
            textAlign: TextAlign.center,
            style: const TextStyle(
              color: Colors.white,
              fontSize: 11,
              fontWeight: FontWeight.bold,
            ),
          ),
        ],
      ),
    );
  }

  String _number(double? value, {required String suffix}) {
    return value == null
        ? 'Tidak tersedia'
        : '${value.toStringAsFixed(0)}$suffix';
  }

  Widget _buildTombolRekomendasi() {
    return SizedBox(
      width: double.infinity,
      child: ElevatedButton.icon(
        onPressed: () {
          Navigator.push(
            context,
            MaterialPageRoute(
              builder: (_) => FormLahanScreen(repository: _repository),
            ),
          );
        },
        icon: const Icon(Icons.eco),
        label: const Text('Dapatkan Rekomendasi Rotasi Tanam'),
      ),
    );
  }
}

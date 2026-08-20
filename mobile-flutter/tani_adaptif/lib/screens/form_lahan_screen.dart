import 'package:flutter/material.dart';

import '../config/app_config.dart';
import '../models/cuaca_model.dart';
import '../repositories/tani_adaptif_repository.dart';
import 'hasil_screen.dart';

class FormLahanScreen extends StatefulWidget {
  final TaniAdaptifRepository? repository;
  final CuacaModel? cuaca;

  const FormLahanScreen({super.key, this.repository, this.cuaca});

  @override
  State<FormLahanScreen> createState() => _FormLahanScreenState();
}

class _FormLahanScreenState extends State<FormLahanScreen> {
  late final TaniAdaptifRepository _repository;

  String _tanamanSebelumnya = 'padi';
  String _ketersediaanAir = 'cukup';
  String _jenisLahan = 'sawah';
  bool _isLoading = false;
  bool _isWeatherLoading = false;
  CuacaModel? _cuaca;

  @override
  void initState() {
    super.initState();
    _repository = widget.repository ?? TaniAdaptifRepository();
    _cuaca = widget.cuaca;
    if (_cuaca == null) _muatCuaca();
  }

  Future<void> _muatCuaca() async {
    setState(() => _isWeatherLoading = true);
    try {
      final result = await _repository.getWeather();
      if (!mounted) return;
      setState(() => _cuaca = result.data);
    } catch (_) {
      // Form tetap dapat digunakan; backend rekomendasi mengambil cuaca terbaru.
    } finally {
      if (mounted) setState(() => _isWeatherLoading = false);
    }
  }

  Future<void> _prosesRekomendasi() async {
    setState(() => _isLoading = true);

    try {
      final result = await _repository.getRecommendation(
        ketersediaanAir: _ketersediaanAir,
        tanamanSebelumnya: _tanamanSebelumnya,
        jenisLahan: _jenisLahan,
      );

      if (mounted) {
        if (result.notice != null) {
          ScaffoldMessenger.of(
            context,
          ).showSnackBar(SnackBar(content: Text(result.notice!)));
        }
        Navigator.push(
          context,
          MaterialPageRoute(
            builder: (_) => HasilScreen(
              cuaca: result.data.cuaca,
              rekomendasi: result.data.rekomendasi,
              jenisLahan: _jenisLahan,
              ketersediaanAir: _ketersediaanAir,
            ),
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Gagal: $e'),
            backgroundColor: AppColors.danger,
          ),
        );
      }
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Input Kondisi Lahan')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Isi informasi lahan Anda untuk mendapatkan rekomendasi rotasi tanam yang sesuai.',
              style: TextStyle(fontSize: 14, color: AppColors.grey),
            ),
            const SizedBox(height: 24),
            _buildLabel('Jenis Lahan'),
            _buildDropdown(
              value: _jenisLahan,
              items: const {
                'sawah': 'Sawah',
                'tegalan': 'Tegalan / Ladang',
                'kebun_campur': 'Kebun Campur',
              },
              onChanged: (val) => setState(() => _jenisLahan = val!),
            ),
            const SizedBox(height: 20),
            _buildLabel('Ketersediaan Air'),
            _buildDropdown(
              value: _ketersediaanAir,
              items: const {
                'cukup': 'Cukup (irigasi lancar)',
                'terbatas': 'Terbatas',
                'kurang': 'Kurang (sangat minim)',
              },
              onChanged: (val) => setState(() => _ketersediaanAir = val!),
            ),
            const SizedBox(height: 20),
            _buildLabel('Tanaman Sebelumnya'),
            _buildDropdown(
              value: _tanamanSebelumnya,
              items: const {
                'padi': 'Padi',
                'jagung': 'Jagung',
                'cabai': 'Cabai',
                'kacang_tanah': 'Kacang Tanah',
                'kosong': 'Belum ada / Lahan kosong',
              },
              onChanged: (val) => setState(() => _tanamanSebelumnya = val!),
            ),
            const SizedBox(height: 24),
            _buildRingkasanCuaca(),
            const SizedBox(height: 24),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: _isLoading ? null : _prosesRekomendasi,
                child: _isLoading
                    ? const SizedBox(
                        height: 20,
                        width: 20,
                        child: CircularProgressIndicator(
                          color: Colors.white,
                          strokeWidth: 2,
                        ),
                      )
                    : const Padding(
                        padding: EdgeInsets.symmetric(vertical: 4),
                        child: Text(
                          'Proses Rekomendasi',
                          style: TextStyle(fontSize: 15),
                        ),
                      ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildRingkasanCuaca() {
    final cuaca = _cuaca;
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppColors.primaryLightest,
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Row(
            children: [
              Icon(Icons.cloud_outlined, size: 20, color: AppColors.primary),
              SizedBox(width: 8),
              Text(
                'Ringkasan Cuaca BMKG',
                style: TextStyle(fontWeight: FontWeight.bold),
              ),
            ],
          ),
          const SizedBox(height: 12),
          if (_isWeatherLoading)
            const LinearProgressIndicator()
          else if (cuaca == null)
            const Text(
              'Ringkasan belum tersedia. Cuaca akan diambil saat rekomendasi diproses.',
              style: TextStyle(fontSize: 12, color: AppColors.grey),
            )
          else
            Row(
              children: [
                _weatherValue(
                  'Suhu',
                  cuaca.suhu == null
                      ? 'Tidak tersedia'
                      : '${cuaca.suhu!.toStringAsFixed(0)} C',
                ),
                _weatherValue(
                  'Curah hujan',
                  cuaca.kategoriCurahHujan ?? 'Tidak tersedia',
                ),
                _weatherValue('Kondisi', cuaca.kondisi),
              ],
            ),
        ],
      ),
    );
  }

  Widget _weatherValue(String label, String value) {
    return Expanded(
      child: Column(
        children: [
          Text(
            label,
            textAlign: TextAlign.center,
            style: const TextStyle(fontSize: 10, color: AppColors.grey),
          ),
          const SizedBox(height: 4),
          Text(
            value,
            textAlign: TextAlign.center,
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w600),
          ),
        ],
      ),
    );
  }

  Widget _buildLabel(String text) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Text(
        text,
        style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14),
      ),
    );
  }

  Widget _buildDropdown({
    required String value,
    required Map<String, String> items,
    required void Function(String?) onChanged,
  }) {
    return DropdownButtonFormField<String>(
      initialValue: value,
      isExpanded: true,
      items: items.entries
          .map((e) => DropdownMenuItem(value: e.key, child: Text(e.value)))
          .toList(),
      onChanged: onChanged,
    );
  }
}

import 'package:flutter/material.dart';

import '../config/app_config.dart';
import '../services/local_storage_service.dart';

class RiwayatScreen extends StatefulWidget {
  final LocalStorageService? localStorageService;

  const RiwayatScreen({super.key, this.localStorageService});

  @override
  State<RiwayatScreen> createState() => _RiwayatScreenState();
}

class _RiwayatScreenState extends State<RiwayatScreen> {
  late final LocalStorageService _storage;
  final _searchController = TextEditingController();
  List<Map<String, dynamic>> _entries = const [];
  bool _isLoading = true;
  String _query = '';

  @override
  void initState() {
    super.initState();
    _storage = widget.localStorageService ?? const LocalStorageService();
    _loadHistory();
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  Future<void> _loadHistory() async {
    setState(() => _isLoading = true);
    final entries = await _storage.loadVisualHistory();
    if (!mounted) return;
    setState(() {
      _entries = entries;
      _isLoading = false;
    });
  }

  List<Map<String, dynamic>> get _filteredEntries {
    final query = _query.trim().toLowerCase();
    if (query.isEmpty) return _entries;
    return _entries.where((entry) {
      return [
        _name(entry),
        _value(entry, 'land_type'),
        _value(entry, 'water_availability'),
        _value(entry, 'previous_crop'),
      ].any((value) => value.toLowerCase().contains(query));
    }).toList();
  }

  Future<void> _deleteEntry(Map<String, dynamic> entry) async {
    final id = _value(entry, 'id').isNotEmpty
        ? _value(entry, 'id')
        : _value(entry, 'request_id');
    if (id.isEmpty) return;

    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Hapus riwayat?'),
        content: Text('Riwayat ${_name(entry)} akan dihapus dari perangkat.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Batal'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Hapus'),
          ),
        ],
      ),
    );
    if (confirmed != true) return;

    await _storage.deleteVisualHistory(id);
    await _loadHistory();
  }

  void _showDetail(Map<String, dynamic> entry) {
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      showDragHandle: true,
      builder: (context) => DraggableScrollableSheet(
        expand: false,
        initialChildSize: 0.72,
        maxChildSize: 0.92,
        minChildSize: 0.45,
        builder: (context, controller) => ListView(
          controller: controller,
          padding: const EdgeInsets.fromLTRB(20, 0, 20, 24),
          children: [
            Text(
              _name(entry),
              style: Theme.of(context).textTheme.titleLarge?.copyWith(
                fontWeight: FontWeight.bold,
                color: AppColors.primary,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              _formatTimestamp(_value(entry, 'timestamp')),
              style: const TextStyle(color: AppColors.grey, fontSize: 12),
            ),
            if (_value(entry, 'image_url').isNotEmpty) ...[
              const SizedBox(height: 16),
              ClipRRect(
                borderRadius: BorderRadius.circular(8),
                child: AspectRatio(
                  aspectRatio: 1,
                  child: Image.network(
                    _value(entry, 'image_url'),
                    headers: AppConfig.visualImageHeaders,
                    fit: BoxFit.cover,
                    errorBuilder: (_, _, _) => const ColoredBox(
                      color: AppColors.greyLight,
                      child: Center(child: Icon(Icons.broken_image_outlined)),
                    ),
                  ),
                ),
              ),
            ],
            const SizedBox(height: 20),
            _detailRow('Jenis lahan', _label(_value(entry, 'land_type'))),
            _detailRow(
              'Ketersediaan air',
              _label(_value(entry, 'water_availability')),
            ),
            _detailRow(
              'Tanaman sebelumnya',
              _label(_value(entry, 'previous_crop')),
            ),
            _detailRow('Cuaca', _value(entry, 'weather_summary')),
            _detailRow('Alasan', _value(entry, 'rekomendasi_alasan')),
            _detailRow('Rule ID', _value(entry, 'rule_id')),
            _detailRow('Model', _value(entry, 'model')),
            _detailRow('Request ID', _value(entry, 'request_id')),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Riwayat Rekomendasi'),
        actions: [
          IconButton(
            onPressed: _loadHistory,
            icon: const Icon(Icons.refresh),
            tooltip: 'Muat ulang riwayat',
          ),
        ],
      ),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
            child: TextField(
              controller: _searchController,
              onChanged: (value) => setState(() => _query = value),
              decoration: const InputDecoration(
                hintText: 'Cari tanaman atau kondisi lahan',
                prefixIcon: Icon(Icons.search),
              ),
            ),
          ),
          Expanded(child: _buildContent()),
        ],
      ),
    );
  }

  Widget _buildContent() {
    if (_isLoading) {
      return const Center(child: CircularProgressIndicator());
    }

    final entries = _filteredEntries;
    if (entries.isEmpty) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(
                Icons.history_toggle_off,
                size: 56,
                color: AppColors.grey,
              ),
              const SizedBox(height: 12),
              Text(
                _query.isEmpty
                    ? 'Belum ada rekomendasi tersimpan.'
                    : 'Riwayat tidak ditemukan.',
                textAlign: TextAlign.center,
                style: const TextStyle(color: AppColors.grey),
              ),
            ],
          ),
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: _loadHistory,
      child: ListView.separated(
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
        itemCount: entries.length,
        separatorBuilder: (_, _) => const SizedBox(height: 10),
        itemBuilder: (context, index) => _historyCard(entries[index]),
      ),
    );
  }

  Widget _historyCard(Map<String, dynamic> entry) {
    final imageUrl = _value(entry, 'image_url');
    return Card(
      margin: EdgeInsets.zero,
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: () => _showDetail(entry),
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Row(
            children: [
              Container(
                width: 64,
                height: 64,
                decoration: BoxDecoration(
                  color: AppColors.primaryLightest,
                  borderRadius: BorderRadius.circular(8),
                ),
                clipBehavior: Clip.antiAlias,
                child: imageUrl.isEmpty
                    ? const Icon(Icons.eco, color: AppColors.primary, size: 32)
                    : Image.network(
                        imageUrl,
                        headers: AppConfig.visualImageHeaders,
                        fit: BoxFit.cover,
                        errorBuilder: (_, _, _) => const Icon(
                          Icons.eco,
                          color: AppColors.primary,
                          size: 32,
                        ),
                      ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      _name(entry),
                      style: const TextStyle(
                        fontWeight: FontWeight.bold,
                        fontSize: 16,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      '${_label(_value(entry, 'land_type'))} | Air ${_label(_value(entry, 'water_availability'))}',
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontSize: 12),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      _formatTimestamp(_value(entry, 'timestamp')),
                      style: const TextStyle(
                        color: AppColors.grey,
                        fontSize: 11,
                      ),
                    ),
                  ],
                ),
              ),
              IconButton(
                onPressed: () => _deleteEntry(entry),
                icon: const Icon(Icons.delete_outline),
                color: AppColors.danger,
                tooltip: 'Hapus riwayat',
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _detailRow(String label, String value) {
    if (value.trim().isEmpty) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: const TextStyle(
              color: AppColors.grey,
              fontSize: 11,
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: 2),
          Text(value),
        ],
      ),
    );
  }

  String _name(Map<String, dynamic> entry) {
    return _value(entry, 'nama_tanaman').isNotEmpty
        ? _value(entry, 'nama_tanaman')
        : _label(
            _value(entry, 'tanaman').isNotEmpty
                ? _value(entry, 'tanaman')
                : _value(entry, 'crop'),
          );
  }

  String _value(Map<String, dynamic> entry, String key) {
    return entry[key]?.toString() ?? '';
  }

  String _label(String value) {
    if (value.isEmpty) return 'Tidak tersedia';
    return value
        .split('_')
        .map(
          (word) => word.isEmpty
              ? word
              : '${word.substring(0, 1).toUpperCase()}${word.substring(1)}',
        )
        .join(' ');
  }

  String _formatTimestamp(String value) {
    final timestamp = DateTime.tryParse(value)?.toLocal();
    if (timestamp == null) return 'Waktu tidak tersedia';
    final day = timestamp.day.toString().padLeft(2, '0');
    final month = timestamp.month.toString().padLeft(2, '0');
    final hour = timestamp.hour.toString().padLeft(2, '0');
    final minute = timestamp.minute.toString().padLeft(2, '0');
    return '$day/$month/${timestamp.year} $hour:$minute';
  }
}

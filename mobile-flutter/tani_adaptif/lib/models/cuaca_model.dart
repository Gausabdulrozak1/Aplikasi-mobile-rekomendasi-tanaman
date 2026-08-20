class CuacaModel {
  final String desa;
  final String kecamatan;
  final String kabupaten;
  final double? suhu;
  final double? kelembaban;
  final String kondisi;
  final double? kecepatanAngin;
  final double? curahHujan;
  final String? kategoriCurahHujan;
  final int? estimasiCurahHujanBulanan;
  final String sumberData;
  final String? waktuData;
  final String? waktuAmbil;
  final String cacheStatus;
  final bool isStale;
  final bool fromLocalCache;
  final bool curahHujanLengkap;
  final String metodologiEstimasi;

  const CuacaModel({
    required this.desa,
    required this.kecamatan,
    required this.kabupaten,
    required this.suhu,
    required this.kelembaban,
    required this.kondisi,
    required this.kecepatanAngin,
    required this.curahHujan,
    required this.kategoriCurahHujan,
    required this.estimasiCurahHujanBulanan,
    required this.sumberData,
    this.waktuData,
    this.waktuAmbil,
    this.cacheStatus = 'network',
    this.isStale = false,
    this.fromLocalCache = false,
    this.curahHujanLengkap = false,
    this.metodologiEstimasi = '',
  });

  factory CuacaModel.fromJson(Map<String, dynamic> json) {
    final data = _asMap(json['data']).isNotEmpty ? _asMap(json['data']) : json;
    final lokasi = _asMap(data['lokasi']);
    final cuaca = _asMap(data['cuacaSaatIni']);
    final cache = _asMap(data['cache']);
    final cakupan = _asMap(data['cakupanCurahHujan']);

    return CuacaModel(
      desa: lokasi['desa']?.toString() ?? 'Tidak diketahui',
      kecamatan: lokasi['kecamatan']?.toString() ?? '',
      kabupaten: lokasi['kotkab']?.toString() ?? '',
      suhu: _toNullableDouble(cuaca['suhu']),
      kelembaban: _toNullableDouble(cuaca['kelembaban']),
      kondisi: cuaca['kondisi']?.toString() ?? 'Tidak diketahui',
      kecepatanAngin: _toNullableDouble(cuaca['kecepatanAngin']),
      curahHujan: _toNullableDouble(cuaca['curahHujan']),
      kategoriCurahHujan: data['kategoriCurahHujan']?.toString(),
      estimasiCurahHujanBulanan: _toNullableInt(
        data['estimasiCurahHujanBulanan'],
      ),
      sumberData: data['sumberData']?.toString() ?? 'BMKG',
      waktuData: cuaca['waktu']?.toString(),
      waktuAmbil: data['waktuAmbil']?.toString(),
      cacheStatus: cache['status']?.toString() ?? 'network',
      isStale: cache['isStale'] == true,
      fromLocalCache: data['fromLocalCache'] == true,
      curahHujanLengkap: cakupan['lengkap'] == true,
      metodologiEstimasi: data['metodologiEstimasi']?.toString() ?? '',
    );
  }

  CuacaModel asLocalCache() {
    return CuacaModel(
      desa: desa,
      kecamatan: kecamatan,
      kabupaten: kabupaten,
      suhu: suhu,
      kelembaban: kelembaban,
      kondisi: kondisi,
      kecepatanAngin: kecepatanAngin,
      curahHujan: curahHujan,
      kategoriCurahHujan: kategoriCurahHujan,
      estimasiCurahHujanBulanan: estimasiCurahHujanBulanan,
      sumberData: sumberData,
      waktuData: waktuData,
      waktuAmbil: waktuAmbil,
      cacheStatus: 'local-cache',
      isStale: true,
      fromLocalCache: true,
      curahHujanLengkap: curahHujanLengkap,
      metodologiEstimasi: metodologiEstimasi,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'lokasi': {'desa': desa, 'kecamatan': kecamatan, 'kotkab': kabupaten},
      'cuacaSaatIni': {
        'waktu': waktuData,
        'suhu': suhu,
        'kelembaban': kelembaban,
        'kondisi': kondisi,
        'kecepatanAngin': kecepatanAngin,
        'curahHujan': curahHujan,
      },
      'kategoriCurahHujan': kategoriCurahHujan,
      'estimasiCurahHujanBulanan': estimasiCurahHujanBulanan,
      'sumberData': sumberData,
      'waktuAmbil': waktuAmbil,
      'cache': {'status': cacheStatus, 'isStale': isStale},
      'cakupanCurahHujan': {'lengkap': curahHujanLengkap},
      'metodologiEstimasi': metodologiEstimasi,
      'fromLocalCache': fromLocalCache,
    };
  }
}

Map<String, dynamic> _asMap(dynamic value) {
  if (value is Map<String, dynamic>) return value;
  if (value is Map) {
    return value.map((key, item) => MapEntry(key.toString(), item));
  }
  return <String, dynamic>{};
}

double? _toNullableDouble(dynamic value) {
  if (value == null) return null;
  if (value is int) return value.toDouble();
  if (value is double) return value;
  return double.tryParse(value.toString());
}

int? _toNullableInt(dynamic value) {
  if (value == null) return null;
  if (value is int) return value;
  if (value is double) return value.toInt();
  return int.tryParse(value.toString());
}

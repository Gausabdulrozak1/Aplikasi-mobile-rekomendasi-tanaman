Map<String, dynamic> _asMap(dynamic value) {
  if (value is Map<String, dynamic>) return value;
  if (value is Map) {
    return value.map((key, item) => MapEntry(key.toString(), item));
  }
  return <String, dynamic>{};
}

List<dynamic> _asList(dynamic value) {
  return value is List ? value : <dynamic>[];
}

int _toInt(dynamic value) {
  if (value == null) return 0;
  if (value is int) return value;
  if (value is double) return value.toInt();
  return int.tryParse(value.toString()) ?? 0;
}

double _toDouble(dynamic value) {
  if (value == null) return 0;
  if (value is int) return value.toDouble();
  if (value is double) return value;
  return double.tryParse(value.toString()) ?? 0;
}

class TanamanRekomendasi {
  final int prioritas;
  final String kode;
  final String nama;
  final String namaIlmiah;
  final String keluarga;
  final int hariTumbuh;
  final String kebutuhanAir;
  final String deskripsi;

  TanamanRekomendasi({
    required this.prioritas,
    required this.kode,
    required this.nama,
    required this.namaIlmiah,
    required this.keluarga,
    required this.hariTumbuh,
    required this.kebutuhanAir,
    required this.deskripsi,
  });

  factory TanamanRekomendasi.fromJson(Map<String, dynamic> json) {
    return TanamanRekomendasi(
      prioritas: _toInt(json['prioritas']),
      kode: json['kode']?.toString() ?? '',
      nama: json['nama']?.toString() ?? json['tanaman']?.toString() ?? '',
      namaIlmiah: json['namaIlmiah']?.toString() ?? '',
      keluarga: json['keluarga']?.toString() ?? '',
      hariTumbuh: _toInt(json['hariTumbuh']),
      kebutuhanAir: json['kebutuhanAir']?.toString() ?? '',
      deskripsi: json['deskripsi']?.toString() ?? '',
    );
  }
}

class ProfilCuacaMingguan {
  final String kategoriCurahHujan;
  final double estimasiCurahHujanMingguan;
  final double estimasiCurahHujanBulananSetara;
  final double suhuRataRata;
  final double kelembabanRataRata;
  final String kondisiDominan;
  final String sumber;
  final String tingkatKeyakinan;

  ProfilCuacaMingguan({
    required this.kategoriCurahHujan,
    required this.estimasiCurahHujanMingguan,
    required this.estimasiCurahHujanBulananSetara,
    required this.suhuRataRata,
    required this.kelembabanRataRata,
    required this.kondisiDominan,
    required this.sumber,
    required this.tingkatKeyakinan,
  });

  factory ProfilCuacaMingguan.fromJson(Map<String, dynamic> json) {
    return ProfilCuacaMingguan(
      kategoriCurahHujan: json['kategoriCurahHujan']?.toString() ?? 'sedang',
      estimasiCurahHujanMingguan: _toDouble(json['estimasiCurahHujanMingguan']),
      estimasiCurahHujanBulananSetara: _toDouble(
        json['estimasiCurahHujanBulananSetara'],
      ),
      suhuRataRata: _toDouble(json['suhuRataRata']),
      kelembabanRataRata: _toDouble(json['kelembabanRataRata']),
      kondisiDominan: json['kondisiDominan']?.toString() ?? 'Tidak diketahui',
      sumber: json['sumber']?.toString() ?? '',
      tingkatKeyakinan: json['tingkatKeyakinan']?.toString() ?? '',
    );
  }
}

class KegiatanMingguan {
  final List<String> daftar;
  final String catatan;

  KegiatanMingguan({required this.daftar, required this.catatan});

  factory KegiatanMingguan.fromJson(Map<String, dynamic> json) {
    return KegiatanMingguan(
      daftar: _asList(json['daftar']).map((item) => item.toString()).toList(),
      catatan: json['catatan']?.toString() ?? '',
    );
  }
}

class RencanaMingguan {
  final int minggu;
  final String tanggalMulai;
  final String tanggalSelesai;
  final TanamanRekomendasi tanamanPrioritas;
  final List<TanamanRekomendasi> opsiAlternatif;
  final String tahap;
  final String judulTahap;
  final KegiatanMingguan kegiatan;
  final String catatanCuaca;
  final ProfilCuacaMingguan profilCuaca;

  RencanaMingguan({
    required this.minggu,
    required this.tanggalMulai,
    required this.tanggalSelesai,
    required this.tanamanPrioritas,
    required this.opsiAlternatif,
    required this.tahap,
    required this.judulTahap,
    required this.kegiatan,
    required this.catatanCuaca,
    required this.profilCuaca,
  });

  factory RencanaMingguan.fromJson(Map<String, dynamic> json) {
    return RencanaMingguan(
      minggu: _toInt(json['minggu']),
      tanggalMulai: json['tanggalMulai']?.toString() ?? '',
      tanggalSelesai: json['tanggalSelesai']?.toString() ?? '',
      tanamanPrioritas: TanamanRekomendasi.fromJson(
        _asMap(json['tanamanPrioritas']),
      ),
      opsiAlternatif: _asList(
        json['opsiAlternatif'],
      ).map((item) => TanamanRekomendasi.fromJson(_asMap(item))).toList(),
      tahap: json['tahap']?.toString() ?? '',
      judulTahap: json['judulTahap']?.toString() ?? '',
      kegiatan: KegiatanMingguan.fromJson(_asMap(json['kegiatan'])),
      catatanCuaca: json['catatanCuaca']?.toString() ?? '',
      profilCuaca: ProfilCuacaMingguan.fromJson(_asMap(json['profilCuaca'])),
    );
  }
}

class JadwalTanam {
  final int urutan;
  final int prioritas;
  final String tipe;
  final String kode;
  final String tanaman;
  final String keluarga;
  final int mingguTanam;
  final String tanggalTanam;
  final String estimasiPanen;
  final int hariTumbuh;
  final String kebutuhanAir;
  final String catatan;

  JadwalTanam({
    required this.urutan,
    required this.prioritas,
    required this.tipe,
    required this.kode,
    required this.tanaman,
    required this.keluarga,
    required this.mingguTanam,
    required this.tanggalTanam,
    required this.estimasiPanen,
    required this.hariTumbuh,
    required this.kebutuhanAir,
    required this.catatan,
  });

  factory JadwalTanam.fromJson(Map<String, dynamic> json) {
    return JadwalTanam(
      urutan: _toInt(json['urutan']),
      prioritas: _toInt(json['prioritas']),
      tipe: json['tipe']?.toString() ?? '',
      kode: json['kode']?.toString() ?? '',
      tanaman: json['tanaman']?.toString() ?? '',
      keluarga: json['keluarga']?.toString() ?? '',
      mingguTanam: _toInt(json['mingguTanam']),
      tanggalTanam: json['tanggalTanam']?.toString() ?? '',
      estimasiPanen: json['estimasiPanen']?.toString() ?? '',
      hariTumbuh: _toInt(json['hariTumbuh']),
      kebutuhanAir: json['kebutuhanAir']?.toString() ?? '',
      catatan: json['catatan']?.toString() ?? '',
    );
  }
}

class PeriodeRekomendasi {
  final String mulai;
  final String selesai;
  final String durasi;

  PeriodeRekomendasi({
    required this.mulai,
    required this.selesai,
    required this.durasi,
  });

  factory PeriodeRekomendasi.fromJson(Map<String, dynamic> json) {
    if (json.isEmpty) {
      return PeriodeRekomendasi(mulai: '', selesai: '', durasi: '');
    }

    return PeriodeRekomendasi(
      mulai: json['mulai']?.toString() ?? '',
      selesai: json['selesai']?.toString() ?? '',
      durasi: json['durasi']?.toString() ?? '',
    );
  }
}

class RekomendasiModel {
  final List<TanamanRekomendasi> rekomendasi;
  final String alasan;
  final String tanamanSebelumnya;
  final String tanamanSebelumnyaKode;
  final String ruleId;
  final String recommendedCrop;
  final List<RencanaMingguan> rencanaMingguan;
  final List<JadwalTanam> jadwalTanam;
  final PeriodeRekomendasi periode;
  final String catatanPrakiraan;

  RekomendasiModel({
    required this.rekomendasi,
    required this.alasan,
    required this.tanamanSebelumnya,
    required this.tanamanSebelumnyaKode,
    required this.ruleId,
    required this.recommendedCrop,
    required this.rencanaMingguan,
    required this.jadwalTanam,
    required this.periode,
    required this.catatanPrakiraan,
  });

  bool get memilikiKalender => rencanaMingguan.isNotEmpty;

  factory RekomendasiModel.fromJson(Map<String, dynamic> json) {
    final rekomData = _asMap(json['rekomendasi']).isNotEmpty
        ? _asMap(json['rekomendasi'])
        : _asMap(json);
    final kalenderData = _asMap(json['kalender']).isNotEmpty
        ? _asMap(json['kalender'])
        : _asMap(json);
    final input = _asMap(rekomData['input']).isNotEmpty
        ? _asMap(rekomData['input'])
        : _asMap(kalenderData['kondisi']);
    final inputSummary = _asMap(rekomData['inputSummary']).isNotEmpty
        ? _asMap(rekomData['inputSummary'])
        : _asMap(kalenderData['inputSummary']);
    final listRekom = _asList(rekomData['rekomendasi']).isNotEmpty
        ? _asList(rekomData['rekomendasi'])
        : _asList(kalenderData['rekomendasiTanaman']);
    final prakiraanCuaca = _asMap(kalenderData['prakiraanCuaca']);

    return RekomendasiModel(
      rekomendasi: listRekom
          .map((item) => TanamanRekomendasi.fromJson(_asMap(item)))
          .toList(),
      alasan:
          kalenderData['alasan']?.toString() ??
          rekomData['alasan']?.toString() ??
          '',
      tanamanSebelumnya: input['tanamanSebelumnya']?.toString() ?? '',
      tanamanSebelumnyaKode:
          inputSummary['tanamanSebelumnya']?.toString() ?? 'kosong',
      ruleId:
          rekomData['ruleId']?.toString() ??
          kalenderData['ruleId']?.toString() ??
          '',
      recommendedCrop:
          rekomData['recommendedCrop']?.toString() ??
          kalenderData['recommendedCrop']?.toString() ??
          '',
      rencanaMingguan: _asList(
        kalenderData['rencanaMingguan'],
      ).map((item) => RencanaMingguan.fromJson(_asMap(item))).toList(),
      jadwalTanam: _asList(
        kalenderData['jadwalTanam'],
      ).map((item) => JadwalTanam.fromJson(_asMap(item))).toList(),
      periode: PeriodeRekomendasi.fromJson(_asMap(kalenderData['periode'])),
      catatanPrakiraan: prakiraanCuaca['catatan']?.toString() ?? '',
    );
  }
}

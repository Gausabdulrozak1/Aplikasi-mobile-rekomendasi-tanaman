// Kode wilayah untuk Kecamatan Aikmel, Lombok Timur, NTB
// Sumber: Kepmendagri No. 100.1.1-6117 Tahun 2022 (TERVERIFIKASI dengan BMKG)
// Provinsi NTB = 52, Lombok Timur = 52.03, Aikmel = 52.03.09

const WILAYAH_AIKMEL = {
  provinsi: 'Nusa Tenggara Barat',
  kabupaten: 'Lombok Timur',
  kecamatan: 'Aikmel',
  kode_kecamatan: '52.03.09', // ADM3 - untuk lihat semua desa

  // Koordinat pusat Kelurahan Aikmel (terverifikasi)
  koordinat: {
    latitude: -8.56667,  // 8°34'0"S
    longitude: 116.52583, // 116°31'33"E
  },

  // Daftar desa/kelurahan di Kecamatan Aikmel beserta kode ADM4
  // CATATAN: Kelurahan Aikmel = 52.03.09.2002 (TERVERIFIKASI dengan BMKG)
  // Kode desa lain perlu diverifikasi satu per satu via API BMKG
  desa: [
    { nama: 'Aikmel', kode: '52.03.09.2002' }, // TERVERIFIKASI ✓
    // Desa lain di kecamatan Aikmel (kode akan diverifikasi via API)
    // Gunakan endpoint /api/cuaca/cari-desa untuk verifikasi otomatis
  ],

  // Desa default untuk testing (TERVERIFIKASI)
  desa_default: { nama: 'Aikmel', kode: '52.03.09.2002' },
};

module.exports = WILAYAH_AIKMEL;
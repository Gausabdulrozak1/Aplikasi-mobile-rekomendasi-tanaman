const logger = require('../utils/logger');
const DATA_TANAMAN = require('../config/tanaman');
const { ATURAN_ROTASI, ATURAN_DEFAULT } = require('../config/aturanRotasi');

/**
 * Validasi input rekomendasi
 */
function validasiInput(curahHujan, ketersediaanAir, tanamanSebelumnya, jenisLahan) {
  const errors = [];

  const kategoriHujanValid = ['tinggi', 'sedang', 'rendah'];
  const ketersediaanAirValid = ['cukup', 'terbatas', 'kurang'];
  const tanamanValid = ['padi', 'jagung', 'cabai', 'kacang_tanah', 'kosong'];
  const lahanValid = ['sawah', 'tegalan', 'kebun_campur'];

  if (!kategoriHujanValid.includes(curahHujan)) {
    errors.push('Kategori curah hujan harus: tinggi, sedang, atau rendah');
  }
  if (!ketersediaanAirValid.includes(ketersediaanAir)) {
    errors.push('Ketersediaan air harus: cukup, terbatas, atau kurang');
  }
  if (!tanamanValid.includes(tanamanSebelumnya)) {
    errors.push('Tanaman sebelumnya harus: padi, jagung, cabai, kacang_tanah, atau kosong');
  }
  if (!jenisLahan || !lahanValid.includes(jenisLahan)) {
    errors.push('Jenis lahan harus: sawah, tegalan, atau kebun_campur');
  }

  return errors;
}

const JUMLAH_MINGGU_RENCANA = 4;
const MILIDETIK_PER_HARI = 24 * 60 * 60 * 1000;
const KODE_TANAMAN_VALID = new Set(['padi', 'jagung', 'cabai', 'kacang_tanah']);

const TAHAP_MINGGUAN = [
  { kode: 'persiapan_lahan', judul: 'Persiapan lahan dan benih' },
  { kode: 'penanaman', judul: 'Penanaman' },
  { kode: 'perawatan_awal', judul: 'Perawatan awal' },
  { kode: 'pemupukan', judul: 'Pemupukan dan monitoring' },
];

function awalHari(tanggal = new Date()) {
  const d = new Date(tanggal);
  return new Date(d.getFullYear(), d.getMonth(), d.getDate());
}

function tambahHari(tanggal, jumlahHari) {
  return new Date(tanggal.getTime() + (jumlahHari * MILIDETIK_PER_HARI));
}

function formatTanggal(tanggal) {
  const tahun = tanggal.getFullYear();
  const bulan = `${tanggal.getMonth() + 1}`.padStart(2, '0');
  const hari = `${tanggal.getDate()}`.padStart(2, '0');
  return `${tahun}-${bulan}-${hari}`;
}

function bulatkan(nilai, digit = 1) {
  if (!Number.isFinite(nilai)) return null;
  const faktor = 10 ** digit;
  return Math.round(nilai * faktor) / faktor;
}

function angkaAman(nilai, fallback = null) {
  if (nilai === null || nilai === undefined || nilai === '') return fallback;
  const angka = Number(nilai);
  return Number.isFinite(angka) ? angka : fallback;
}

function ambilTanggalPrakiraan(prakiraan) {
  if (!prakiraan || !prakiraan.waktu) return null;

  const mentah = prakiraan.waktu.toString();
  const tanggal = mentah.includes(' ')
    ? mentah.split(' ')[0]
    : mentah.split('T')[0];

  if (/^\d{4}-\d{2}-\d{2}$/.test(tanggal)) {
    return tanggal;
  }

  const hasilParse = new Date(mentah);
  if (Number.isNaN(hasilParse.getTime())) return null;
  return formatTanggal(hasilParse);
}

function rataRata(items, ambilNilai) {
  const nilai = items
    .map(ambilNilai)
    .map((item) => angkaAman(item))
    .filter((item) => Number.isFinite(item));

  if (nilai.length === 0) return null;
  return nilai.reduce((total, item) => total + item, 0) / nilai.length;
}

function nilaiDominan(items, ambilNilai) {
  const jumlah = {};

  items.forEach((item) => {
    const nilai = ambilNilai(item);
    if (!nilai) return;
    jumlah[nilai] = (jumlah[nilai] || 0) + 1;
  });

  return Object.entries(jumlah).sort((a, b) => b[1] - a[1])[0]?.[0] || 'Tidak diketahui';
}

function ringkasPrakiraanHarian(prakiraan = []) {
  const kelompok = {};

  prakiraan.forEach((item) => {
    const tanggal = ambilTanggalPrakiraan(item);
    if (!tanggal) return;

    if (!kelompok[tanggal]) {
      kelompok[tanggal] = [];
    }
    kelompok[tanggal].push(item);
  });

  return Object.entries(kelompok)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([tanggal, items]) => {
      const nilaiCurahHujan = items
        .map((item) => angkaAman(item.curahHujan))
        .filter((item) => Number.isFinite(item));
      const cakupanCurahHujanLengkap = nilaiCurahHujan.length === items.length;
      const curahHujan = cakupanCurahHujanLengkap
        ? nilaiCurahHujan.reduce((total, item) => total + item, 0)
        : null;

      return {
        tanggal,
        jumlahData: items.length,
        suhuRataRata: bulatkan(rataRata(items, (item) => item.suhu)),
        kelembabanRataRata: bulatkan(rataRata(items, (item) => item.kelembaban)),
        curahHujan: bulatkan(curahHujan),
        jumlahDataCurahHujan: nilaiCurahHujan.length,
        cakupanCurahHujanLengkap,
        kondisiDominan: nilaiDominan(items, (item) => item.kondisi),
      };
    });
}

function kategoriCurahHujanBulanan(curahHujanBulanan) {
  if (!Number.isFinite(curahHujanBulanan)) return null;
  if (curahHujanBulanan > 200) return 'tinggi';
  if (curahHujanBulanan >= 100) return 'sedang';
  return 'rendah';
}

function buatProfilCuacaMingguan(input, dataCuaca, jumlahMinggu = JUMLAH_MINGGU_RENCANA) {
  const ringkasanHarian = ringkasPrakiraanHarian(dataCuaca?.prakiraan || []);
  const hariTerukur = ringkasanHarian.length;
  const curahHujanLengkap =
    hariTerukur > 0 && ringkasanHarian.every((hari) => hari.cakupanCurahHujanLengkap);
  const totalCurahHujanTerukur = curahHujanLengkap
    ? ringkasanHarian.reduce((total, hari) => total + hari.curahHujan, 0)
    : angkaAman(dataCuaca?.totalCurahHujanPrakiraan);

  const rataCurahHujanHarian = hariTerukur > 0 && Number.isFinite(totalCurahHujanTerukur)
    ? totalCurahHujanTerukur / hariTerukur
    : null;

  const estimasiCurahHujanMingguan = Number.isFinite(rataCurahHujanHarian)
    ? bulatkan(rataCurahHujanHarian * 7)
    : null;
  const estimasiCurahHujanBulanan = angkaAman(dataCuaca?.estimasiCurahHujanBulanan);
  const kategoriDasar = input.curahHujan || kategoriCurahHujanBulanan(estimasiCurahHujanBulanan);
  const suhuRataRata = hariTerukur > 0
    ? bulatkan(rataRata(ringkasanHarian, (hari) => hari.suhuRataRata))
    : bulatkan(angkaAman(dataCuaca?.cuacaSaatIni?.suhu));
  const kelembabanRataRata = hariTerukur > 0
    ? bulatkan(rataRata(ringkasanHarian, (hari) => hari.kelembabanRataRata))
    : bulatkan(angkaAman(dataCuaca?.cuacaSaatIni?.kelembaban));
  const kondisiDominan = hariTerukur > 0
    ? nilaiDominan(ringkasanHarian, (hari) => hari.kondisiDominan)
    : dataCuaca?.cuacaSaatIni?.kondisi || 'Tidak diketahui';

  return Array.from({ length: jumlahMinggu }, (_, index) => ({
    minggu: index + 1,
    kategoriCurahHujan: kategoriDasar,
    estimasiCurahHujanMingguan,
    estimasiCurahHujanBulananSetara: estimasiCurahHujanBulanan,
    suhuRataRata,
    kelembabanRataRata,
    kondisiDominan,
    sumber: hariTerukur > 0
      ? (index === 0
          ? `BMKG ${hariTerukur} hari dan proyeksi rata-rata hingga akhir minggu`
          : `Proyeksi rata-rata dari horizon BMKG ${hariTerukur} hari`)
      : 'Input manual',
    tingkatKeyakinan: hariTerukur > 0 && index === 0 ? 'sedang' : 'rendah',
    ringkasanHarian: index === 0 ? ringkasanHarian : [],
  }));
}

function cariAturan(kunci, tabelAturan = ATURAN_ROTASI) {
  if (Object.prototype.hasOwnProperty.call(tabelAturan, kunci)) {
    return { aturan: tabelAturan[kunci], menggunakanDefault: false };
  }
  return { aturan: ATURAN_DEFAULT, menggunakanDefault: true };
}

function sesuaikanUrutanDenganLahan(rekomendasi, jenisLahan) {
  const urutanAsli = [...rekomendasi];
  if (jenisLahan === 'sawah') {
    return { rekomendasi: urutanAsli, disesuaikan: false, catatan: '' };
  }

  // Data tanaman proyek menyatakan padi berair tinggi dan terutama cocok di
  // sawah. Pada lahan non-sawah, pilihan lain diprioritaskan tanpa menghapus
  // padi dari alternatif yang berasal dari decision table.
  const urutanBaru = urutanAsli
    .map((kode, index) => ({ kode, index, penalti: kode === 'padi' ? 1 : 0 }))
    .sort((a, b) => a.penalti - b.penalti || a.index - b.index)
    .map((item) => item.kode);
  const disesuaikan = urutanBaru.some((kode, index) => kode !== urutanAsli[index]);

  return {
    rekomendasi: urutanBaru,
    disesuaikan,
    catatan: disesuaikan
      ? ` Urutan disesuaikan karena ${jenisLahan} bukan lahan sawah; padi tetap ditampilkan sebagai alternatif jika tersedia.`
      : '',
  };
}

function buatRuleId(kunci, jenisLahan, menggunakanDefault) {
  const basis = menggunakanDefault ? 'default' : kunci;
  return `ROT-${basis}-${jenisLahan}`.toUpperCase().replace(/_/g, '-');
}

/**
 * Dapatkan rekomendasi rotasi tanam berdasarkan aturan
 * Sesuai flowchart proposal Gambar 3.7
 */
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

    // Susun detail rekomendasi dengan info tanaman lengkap
    const detailRekomendasi = penyesuaianLahan.rekomendasi.map((namaTanaman, index) => {
      const infoTanaman = DATA_TANAMAN[namaTanaman] || {};
      return {
        prioritas: index + 1,
        kode: namaTanaman,
        nama: infoTanaman.nama || namaTanaman,
        namaIlmiah: infoTanaman.namaIlmiah || '',
        keluarga: infoTanaman.keluarga || '',
        hariTumbuh: infoTanaman.hariTumbuh || 0,
        kebutuhanAir: infoTanaman.kebutuhanAir || '',
        deskripsi: infoTanaman.deskripsi || '',
      };
    });

    // Catatan khusus jika air kurang
    let catatanTambahan = '';
    if (ketersediaanAir === 'kurang') {
      catatanTambahan = ' PERHATIAN: Ketersediaan air sangat kurang. Pertimbangkan sistem irigasi tetes atau tunda tanam hingga musim hujan.';
    }

    logger.info(`Rekomendasi berhasil (${ruleId}): ${penyesuaianLahan.rekomendasi.join(', ')}`);

    const inputSummary = {
      kondisiCuaca: curahHujan,
      jenisLahan,
      ketersediaanAir,
      tanamanSebelumnya,
    };
    const alasan = aturan.alasan + penyesuaianLahan.catatan + catatanTambahan;

    return {
      status: 'berhasil',
      input: {
        curahHujan,
        ketersediaanAir,
        tanamanSebelumnya: tanamanSebelumnya === 'kosong' ? 'Belum ada / lahan kosong' : DATA_TANAMAN[tanamanSebelumnya]?.nama,
        jenisLahan,
      },
      inputSummary,
      recommendedCrop: detailRekomendasi[0]?.kode || null,
      rekomendasi: detailRekomendasi,
      reason: alasan,
      alasan,
      ruleId,
      kunciAturan: kunci,
      menggunakanAturanDefault: hasilPencarian.menggunakanDefault,
    };

  } catch (error) {
    logger.error('Gagal memproses rekomendasi:', error.message);
    return {
      status: 'gagal',
      pesan: 'Terjadi kesalahan saat memproses rekomendasi',
      error: error.message,
    };
  }
}

/**
 * Dapatkan rencana rotasi per minggu selama 1 bulan
 * Memberikan jadwal tanam untuk Minggu 1 sampai Minggu 4
 */
function dapatkanRencanaBulanan(input, opsi = {}) {
  try {
    const { curahHujan, ketersediaanAir, tanamanSebelumnya, jenisLahan } = input;
    const { dataCuaca, tanggalAcuan } = opsi;

    // Dapatkan rekomendasi utama
    const rekomendasi = dapatkanRekomendasi(input);
    if (rekomendasi.status === 'gagal') return rekomendasi;

    const tanamanTersedia = rekomendasi.rekomendasi;
    const tanamanUtama = tanamanTersedia[0];
    const opsiAlternatif = tanamanTersedia.slice(1);

    if (!tanamanUtama) {
      return {
        status: 'gagal',
        pesan: 'Tidak ada tanaman yang dapat direkomendasikan untuk kombinasi input ini',
      };
    }

    const tanggalAwal = awalHari(tanggalAcuan || new Date());
    const profilMingguan = buatProfilCuacaMingguan(input, dataCuaca);

    const rencanaMingguan = [];
    for (let minggu = 0; minggu < JUMLAH_MINGGU_RENCANA; minggu++) {
      const tahapInfo = TAHAP_MINGGUAN[minggu];
      const profilCuaca = profilMingguan[minggu];
      const tanggalMulai = tambahHari(tanggalAwal, minggu * 7);
      const tanggalSelesai = tambahHari(tanggalMulai, 6);

      rencanaMingguan.push({
        minggu: minggu + 1,
        tanggalMulai: formatTanggal(tanggalMulai),
        tanggalSelesai: formatTanggal(tanggalSelesai),
        tanamanPrioritas: tanamanUtama,
        opsiAlternatif,
        tahap: tahapInfo.kode,
        judulTahap: tahapInfo.judul,
        kegiatan: dapatkanKegiatan(
          tahapInfo.kode,
          tanamanUtama.nama,
          profilCuaca.kategoriCurahHujan
        ),
        catatanCuaca: dapatkanCatatanCuaca(profilCuaca.kategoriCurahHujan, minggu),
        profilCuaca,
      });
    }

    const tanggalTanam = tambahHari(tanggalAwal, 7);
    const jadwalTanam = tanamanTersedia.map((t, index) => {
      const tglPanen = tambahHari(tanggalTanam, t.hariTumbuh);

      return {
        urutan: index + 1,
        prioritas: t.prioritas,
        tipe: index === 0 ? 'utama' : 'alternatif',
        kode: t.kode,
        tanaman: t.nama,
        keluarga: t.keluarga,
        mingguTanam: 2,
        tanggalTanam: formatTanggal(tanggalTanam),
        estimasiPanen: formatTanggal(tglPanen),
        hariTumbuh: t.hariTumbuh,
        kebutuhanAir: t.kebutuhanAir,
        catatan: index === 0
          ? 'Pilihan utama untuk siklus tanam ini.'
          : 'Pilihan cadangan jika kondisi lahan atau kebutuhan pasar berubah.',
      };
    });

    logger.info(`Rencana bulanan berhasil dibuat: ${rencanaMingguan.length} minggu`);

    return {
      status: 'berhasil',
      kondisi: {
        curahHujan: curahHujan,
        ketersediaanAir: ketersediaanAir,
        tanamanSebelumnya: rekomendasi.input.tanamanSebelumnya,
        jenisLahan,
      },
      inputSummary: rekomendasi.inputSummary,
      recommendedCrop: rekomendasi.recommendedCrop,
      ruleId: rekomendasi.ruleId,
      rekomendasiTanaman: tanamanTersedia,
      rencanaMingguan: rencanaMingguan,
      jadwalTanam: jadwalTanam,
      alasan: rekomendasi.alasan,
      periode: {
        mulai: formatTanggal(tanggalAwal),
        selesai: formatTanggal(tambahHari(tanggalAwal, 27)),
        durasi: '4 minggu (1 bulan)',
      },
      prakiraanCuaca: {
        ringkasanHarian: profilMingguan[0]?.ringkasanHarian || [],
        profilMingguan: profilMingguan.map(({ ringkasanHarian, ...profil }) => profil),
        catatan: dataCuaca?.prakiraan?.length
          ? 'BMKG menyediakan prakiraan jangka pendek. Minggu 2-4 adalah proyeksi rata-rata dari data yang tersedia.'
          : 'Rencana dibuat dari input manual karena prakiraan BMKG tidak tersedia.',
      },
    };

  } catch (error) {
    logger.error('Gagal membuat rencana bulanan:', error.message);
    return {
      status: 'gagal',
      pesan: 'Terjadi kesalahan saat membuat rencana bulanan',
      error: error.message,
    };
  }
}

/**
 * Dapatkan kegiatan untuk setiap tahap
 */
function dapatkanKegiatan(tahap, namaTanaman, curahHujan) {
  const kegiatan = {
    persiapan_lahan: [
      `Bersihkan lahan dari sisa tanaman sebelumnya`,
      `Lakukan pembajakan/penggemburan tanah`,
      `Campurkan pupuk dasar (kompos/pupuk kandang)`,
      `Buat saluran drainase jika diperlukan`,
      `Persiapkan bibit ${namaTanaman} berkualitas`,
    ],
    penanaman: [
      `Tanam bibit ${namaTanaman} dengan jarak yang sesuai`,
      `Lakukan penyiraman awal secara merata`,
      `Berikan pupuk dasar di lubang tanam`,
      `Pasang mulsa jika diperlukan`,
      `Catat tanggal tanam untuk monitoring`,
    ],
    perawatan_awal: [
      `Lakukan penyiraman rutin (pagi/sore)`,
      `Bersihkan gulma di sekitar tanaman`,
      `Periksa tanda-tanda hama dan penyakit`,
      `Berikan pupuk susulan pertama`,
      `Lakukan pembumbunan jika diperlukan`,
    ],
    pemupukan: [
      `Berikan pupuk utama (NPK sesuai dosis)`,
      `Lakukan pengairan yang cukup`,
      `Pantau pertumbuhan tanaman`,
      `Semprot pestisida organik jika perlu`,
      `Persiapkan panen jika tanaman sudah siap`,
    ],
  };

  // Catatan cuaca
  let catatanCuaca = '';
  if (curahHujan === 'tinggi') {
    catatanCuaca = 'Curah hujan tinggi: waspadai genangan air dan serangan jamur.';
  } else if (curahHujan === 'rendah') {
    catatanCuaca = 'Curah hujan rendah: prioritaskan irigasi dan penyiraman rutin.';
  }

  return {
    daftar: kegiatan[tahap] || kegiatan.persiapan_lahan,
    catatan: catatanCuaca,
  };
}

/**
 * Dapatkan catatan cuaca untuk minggu tertentu
 */
function dapatkanCatatanCuaca(curahHujan, minggu) {
  const catatan = {
    tinggi: [
      'Hujan lebat, siapkan drainase',
      'Kelembaban tinggi, waspadai jamur',
      'Intensitas hujan masih tinggi',
      'Mulai berkurang, waktu tanam baik',
    ],
    sedang: [
      'Cuaca mendukung untuk persiapan lahan',
      'Kondisi ideal untuk penanaman',
      'Curah hujan stabil baik untuk tanaman',
      'Mulai masuk musim kemarau, siapkan irigasi',
    ],
    rendah: [
      'Cuaca kering, butuh irigasi maksimal',
      'Pertahankan penyiraman rutin',
      'Hujan masih jarang, pantau kelembaban tanah',
      'Akhir bulan, evaluasi kebutuhan air',
    ],
  };

  const idx = minggu % 4;
  return catatan[curahHujan]?.[idx] || 'Kondisi cuaca normal untuk aktivitas bertani';
}

/**
 * Dapatkan daftar semua tanaman
 */
function dapatkanDaftarTanaman() {
  return Object.keys(DATA_TANAMAN).map((kode) => ({
    kode,
    ...DATA_TANAMAN[kode],
  }));
}

module.exports = {
  dapatkanRekomendasi,
  dapatkanRencanaBulanan,
  dapatkanDaftarTanaman,
  validasiInput,
  cariAturan,
  ringkasPrakiraanHarian,
  buatProfilCuacaMingguan,
};

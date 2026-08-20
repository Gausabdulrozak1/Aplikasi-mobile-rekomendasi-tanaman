const express = require('express');
const router = express.Router();
const rekomendasiService = require('../services/rekomendasiService');
const bmkgService = require('../services/bmkgService');
const logger = require('../utils/logger');

function buatPayloadCuaca(dataCuaca, kategoriHujan) {
  return {
    lokasi: dataCuaca.lokasi,
    cuacaSaatIni: dataCuaca.cuacaSaatIni,
    kategoriCurahHujan: kategoriHujan,
    estimasiCurahHujanBulanan: dataCuaca.estimasiCurahHujanBulanan,
    totalCurahHujanPrakiraan: dataCuaca.totalCurahHujanPrakiraan,
    totalCurahHujan3Hari: dataCuaca.totalCurahHujan3Hari,
    cakupanCurahHujan: dataCuaca.cakupanCurahHujan,
    metodologiEstimasi: dataCuaca.metodologiEstimasi,
    sumberData: dataCuaca.sumberData,
    waktuAmbil: dataCuaca.waktuAmbil,
    cache: dataCuaca.cache,
  };
}

function responsCurahHujanTidakTersedia(res, dataCuaca) {
  return res.status(422).json({
    status: 'gagal',
    kode: 'DATA_CURAH_HUJAN_TIDAK_TERSEDIA',
    pesan: 'BMKG tidak menyediakan data curah hujan lengkap pada horizon saat ini. Gunakan rekomendasi manual atau coba lagi saat data tersedia.',
    cuaca: buatPayloadCuaca(dataCuaca, null),
  });
}

router.get('/tanaman', (req, res) => {
  try {
    const daftar = rekomendasiService.dapatkanDaftarTanaman();
    res.json({
      status: 'berhasil',
      jumlah: daftar.length,
      data: daftar,
    });
  } catch (error) {
    logger.error('Gagal mengambil daftar tanaman:', error.message);
    res.status(500).json({
      status: 'gagal',
      pesan: 'Gagal mengambil daftar tanaman',
    });
  }
});

router.post('/', (req, res) => {
  try {
    const { curahHujan, ketersediaanAir, tanamanSebelumnya, jenisLahan } = req.body;

    if (!curahHujan || !ketersediaanAir || !tanamanSebelumnya || !jenisLahan) {
      return res.status(400).json({
        status: 'gagal',
        pesan: 'Field wajib: curahHujan, ketersediaanAir, tanamanSebelumnya, jenisLahan',
      });
    }

    const hasil = rekomendasiService.dapatkanRekomendasi({
      curahHujan,
      ketersediaanAir,
      tanamanSebelumnya,
      jenisLahan,
    });

    if (hasil.status === 'gagal') {
      return res.status(400).json(hasil);
    }

    return res.json(hasil);
  } catch (error) {
    logger.error('Error endpoint rekomendasi:', error.message);
    return res.status(500).json({
      status: 'gagal',
      pesan: 'Gagal memproses rekomendasi',
    });
  }
});

router.post('/otomatis', async (req, res) => {
  try {
    const { kodeWilayah, ketersediaanAir, tanamanSebelumnya, jenisLahan } = req.body;

    if (!kodeWilayah || !ketersediaanAir || !tanamanSebelumnya || !jenisLahan) {
      return res.status(400).json({
        status: 'gagal',
        pesan: 'Field wajib: kodeWilayah, ketersediaanAir, tanamanSebelumnya, jenisLahan',
      });
    }

    const dataCuaca = await bmkgService.ambilDataCuaca(kodeWilayah);
    const kategoriHujan = bmkgService.kategorisasiCurahHujan(
      dataCuaca.estimasiCurahHujanBulanan
    );
    if (!kategoriHujan) {
      return responsCurahHujanTidakTersedia(res, dataCuaca);
    }

    const hasilRekomendasi = rekomendasiService.dapatkanRekomendasi({
      curahHujan: kategoriHujan,
      ketersediaanAir,
      tanamanSebelumnya,
      jenisLahan,
    });
    if (hasilRekomendasi.status === 'gagal') {
      return res.status(400).json(hasilRekomendasi);
    }

    return res.json({
      status: 'berhasil',
      cuaca: buatPayloadCuaca(dataCuaca, kategoriHujan),
      rekomendasi: hasilRekomendasi,
    });
  } catch (error) {
    logger.error('Error rekomendasi otomatis:', error.message);
    return res.status(500).json({
      status: 'gagal',
      pesan: 'Gagal memproses rekomendasi otomatis',
      kode: error.code || 'INTERNAL_ERROR',
    });
  }
});

router.post('/kalender', async (req, res) => {
  try {
    const { kodeWilayah, ketersediaanAir, tanamanSebelumnya, jenisLahan } = req.body;

    if (!kodeWilayah || !ketersediaanAir || !tanamanSebelumnya || !jenisLahan) {
      return res.status(400).json({
        status: 'gagal',
        pesan: 'Field wajib: kodeWilayah, ketersediaanAir, tanamanSebelumnya, jenisLahan',
      });
    }

    const dataCuaca = await bmkgService.ambilDataCuaca(kodeWilayah);
    const kategoriHujan = bmkgService.kategorisasiCurahHujan(
      dataCuaca.estimasiCurahHujanBulanan
    );
    if (!kategoriHujan) {
      return responsCurahHujanTidakTersedia(res, dataCuaca);
    }

    const inputRekomendasi = {
      curahHujan: kategoriHujan,
      ketersediaanAir,
      tanamanSebelumnya,
      jenisLahan,
    };
    const hasilRekomendasi = rekomendasiService.dapatkanRekomendasi(inputRekomendasi);
    if (hasilRekomendasi.status === 'gagal') {
      return res.status(400).json(hasilRekomendasi);
    }

    const kalender = rekomendasiService.dapatkanRencanaBulanan(inputRekomendasi, {
      dataCuaca,
    });
    if (kalender.status === 'gagal') {
      return res.status(400).json(kalender);
    }

    return res.json({
      status: 'berhasil',
      cuaca: buatPayloadCuaca(dataCuaca, kategoriHujan),
      rekomendasi: hasilRekomendasi,
      kalender,
    });
  } catch (error) {
    logger.error('Error kalender rekomendasi:', error.message);
    return res.status(500).json({
      status: 'gagal',
      pesan: 'Gagal membuat kalender rekomendasi',
      kode: error.code || 'INTERNAL_ERROR',
    });
  }
});

module.exports = router;

const express = require('express');
const router = express.Router();
const bmkgService = require('../services/bmkgService');
const logger = require('../utils/logger');

// ============================================
// GET /api/cuaca/info
// Info wilayah Aikmel
// ============================================
router.get('/info', (req, res) => {
  res.json({
    status: 'berhasil',
    data: {
      provinsi: bmkgService.WILAYAH_AIKMEL.provinsi,
      kabupaten: bmkgService.WILAYAH_AIKMEL.kabupaten,
      kecamatan: bmkgService.WILAYAH_AIKMEL.kecamatan,
      kodeKecamatan: bmkgService.WILAYAH_AIKMEL.kode_kecamatan,
      koordinat: bmkgService.WILAYAH_AIKMEL.koordinat,
      desaDefault: bmkgService.WILAYAH_AIKMEL.desa_default,
    },
  });
});

// ============================================
// GET /api/cuaca/desa
// Daftar desa di Aikmel
// ============================================
router.get('/desa', (req, res) => {
  try {
    const daftarDesa = bmkgService.dapatkanDaftarDesa();
    res.json({
      status: 'berhasil',
      kecamatan: 'Aikmel',
      kabupaten: 'Lombok Timur',
      jumlah: daftarDesa.length,
      data: daftarDesa,
    });
  } catch (error) {
    res.status(500).json({
      status: 'gagal',
      pesan: 'Gagal mengambil daftar desa',
    });
  }
});

// ============================================
// GET /api/cuaca/:kodeWilayah
// Ambil cuaca berdasarkan kode ADM4
// Contoh: /api/cuaca/52.03.09.2002
// ============================================
router.get('/:kodeWilayah', async (req, res) => {
  try {
    const { kodeWilayah } = req.params;

    // Validasi format kode (harus 4 bagian: 52.03.09.2002)
    const bagian = kodeWilayah.split('.');
    if (bagian.length !== 4) {
      return res.status(400).json({
        status: 'gagal',
        pesan: 'Format kode wilayah salah. Harus: provinsi.kabupaten.kecamatan.desa (contoh: 52.03.09.2002)',
      });
    }

    // Ambil data cuaca
    const dataCuaca = await bmkgService.ambilDataCuaca(kodeWilayah);

    // Kategorisasi curah hujan
    const kategoriHujan = bmkgService.kategorisasiCurahHujan(
      dataCuaca.estimasiCurahHujanBulanan
    );

    res.json({
      status: 'berhasil',
      data: {
        ...dataCuaca,
        kategoriCurahHujan: kategoriHujan,
      },
    });

  } catch (error) {
    logger.error('Error endpoint cuaca:', error.message);
    res.status(500).json({
      status: 'gagal',
      pesan: 'Gagal mengambil data cuaca',
      error: error.message,
    });
  }
});

module.exports = router;
const axios = require('axios');
const logger = require('../utils/logger');
const WILAYAH_AIKMEL = require('../config/wilayah');

const BMKG_BASE_URL = 'https://api.bmkg.go.id/publik/prakiraan-cuaca';
const CACHE_DURASI = 30 * 60 * 1000;
const cacheCuaca = {};

function angkaAtauNull(value) {
  if (value === null || value === undefined || value === '') return null;
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function bulatkan(value, digits = 2) {
  if (!Number.isFinite(value)) return null;
  const factor = 10 ** digits;
  return Math.round(value * factor) / factor;
}

function tanggalLokal(value) {
  if (!value) return null;
  const raw = value.toString();
  const date = raw.includes(' ') ? raw.split(' ')[0] : raw.split('T')[0];
  return /^\d{4}-\d{2}-\d{2}$/.test(date) ? date : null;
}

function denganStatusCache(data, status, ageMs) {
  return {
    ...data,
    cache: {
      status,
      isStale: status === 'stale-cache',
      ageSeconds: Math.max(0, Math.round(ageMs / 1000)),
      ttlSeconds: Math.round(CACHE_DURASI / 1000),
    },
  };
}

/**
 * Ambil data cuaca berdasarkan kode ADM4. Dependency injection pada options
 * hanya dipakai agar timeout dan fallback cache dapat diuji tanpa jaringan.
 */
async function ambilDataCuaca(kodeWilayah, options = {}) {
  const httpClient = options.httpClient || axios;
  const now = options.now || (() => Date.now());
  const currentTime = now();
  const cacheItem = cacheCuaca[kodeWilayah];

  if (cacheItem && currentTime - cacheItem.waktu < CACHE_DURASI) {
    logger.info(`Menggunakan data cache untuk wilayah: ${kodeWilayah}`);
    return denganStatusCache(
      cacheItem.data,
      'fresh-cache',
      currentTime - cacheItem.waktu
    );
  }

  try {
    logger.info(`Mengambil data cuaca dari BMKG untuk: ${kodeWilayah}`);
    const url = `${BMKG_BASE_URL}?adm4=${encodeURIComponent(kodeWilayah)}`;
    const response = await httpClient.get(url, {
      timeout: 15000,
      headers: {
        'User-Agent': 'TaniAdaptif/1.0 (Aplikasi Skripsi Universitas Hamzanwadi)',
      },
    });

    if (!response.data || !Array.isArray(response.data.data)) {
      throw new Error('Format data BMKG tidak valid atau kode wilayah salah');
    }

    const dataOlahan = prosesDataCuaca(response.data, new Date(currentTime));
    cacheCuaca[kodeWilayah] = {
      data: dataOlahan,
      waktu: currentTime,
    };

    logger.info(`Data cuaca berhasil diambil untuk: ${dataOlahan.lokasi.desa}`);
    return denganStatusCache(dataOlahan, 'network', 0);
  } catch (error) {
    logger.error('Gagal ambil data cuaca BMKG:', error.message);

    if (cacheItem) {
      logger.warn('Menggunakan data cache lama sebagai fallback');
      return denganStatusCache(
        cacheItem.data,
        'stale-cache',
        currentTime - cacheItem.waktu
      );
    }

    const wrappedError = new Error(
      `Gagal mengambil data cuaca dari BMKG: ${error.message}`
    );
    wrappedError.code = 'BMKG_UNAVAILABLE';
    throw wrappedError;
  }
}

/**
 * Ubah respons BMKG menjadi kontrak aplikasi tanpa mengisi field yang hilang.
 */
function prosesDataCuaca(dataBmkg, waktuAmbil = new Date()) {
  const lokasi = dataBmkg.lokasi || {};
  const rawCuaca = dataBmkg.data?.[0]?.cuaca;
  const titikPrakiraan = Array.isArray(rawCuaca)
    ? rawCuaca.flat(Infinity).filter((item) => item && typeof item === 'object')
    : [];

  const semuaPrakiraan = titikPrakiraan.map((point) => ({
    waktu: point.local_datetime || null,
    suhu: angkaAtauNull(point.t),
    kelembaban: angkaAtauNull(point.hu),
    kondisi: point.weather_desc || 'Tidak diketahui',
    kecepatanAngin: angkaAtauNull(point.ws),
    arahAngin: point.wd || '',
    tutupanAwan: angkaAtauNull(point.tcc),
    curahHujan: angkaAtauNull(point.tp),
    jarakPandang: point.vs_text || '',
  }));

  const cuacaSaatIni = semuaPrakiraan[0] || {};
  const dataCurahHujan = semuaPrakiraan
    .map((point) => point.curahHujan)
    .filter((value) => Number.isFinite(value));
  const tanggalPrakiraan = new Set(
    semuaPrakiraan.map((point) => tanggalLokal(point.waktu)).filter(Boolean)
  );
  const jumlahHariPrakiraan = tanggalPrakiraan.size;
  const cakupanLengkap =
    semuaPrakiraan.length > 0 && dataCurahHujan.length === semuaPrakiraan.length;
  const totalCurahHujanPrakiraan = cakupanLengkap
    ? bulatkan(dataCurahHujan.reduce((total, value) => total + value, 0))
    : null;
  const estimasiCurahHujanBulanan =
    cakupanLengkap && jumlahHariPrakiraan > 0
      ? Math.round((totalCurahHujanPrakiraan / jumlahHariPrakiraan) * 30)
      : null;

  return {
    lokasi: {
      desa: lokasi.desa || 'Tidak diketahui',
      kecamatan: lokasi.kecamatan || '',
      kotkab: lokasi.kotkab || '',
      provinsi: lokasi.provinsi || '',
      latitude: angkaAtauNull(lokasi.lat),
      longitude: angkaAtauNull(lokasi.lon),
    },
    cuacaSaatIni: {
      waktu: cuacaSaatIni.waktu || null,
      suhu: cuacaSaatIni.suhu ?? null,
      kelembaban: cuacaSaatIni.kelembaban ?? null,
      kondisi: cuacaSaatIni.kondisi || 'Tidak diketahui',
      kecepatanAngin: cuacaSaatIni.kecepatanAngin ?? null,
      arahAngin: cuacaSaatIni.arahAngin || '',
      curahHujan: cuacaSaatIni.curahHujan ?? null,
    },
    totalCurahHujanPrakiraan,
    // Nama lama dipertahankan agar klien lama tidak langsung rusak.
    totalCurahHujan3Hari: totalCurahHujanPrakiraan,
    estimasiCurahHujanBulanan,
    cakupanCurahHujan: {
      jumlahTitikPrakiraan: semuaPrakiraan.length,
      jumlahTitikDenganData: dataCurahHujan.length,
      jumlahHariPrakiraan,
      lengkap: cakupanLengkap,
    },
    metodologiEstimasi: estimasiCurahHujanBulanan === null
      ? 'Tidak dihitung karena data curah hujan pada horizon prakiraan tidak lengkap.'
      : 'Proyeksi 30 hari dari rata-rata curah hujan harian pada horizon BMKG yang tersedia; bukan prakiraan bulanan BMKG.',
    prakiraan: semuaPrakiraan,
    sumberData: 'BMKG (Badan Meteorologi, Klimatologi, dan Geofisika)',
    waktuAmbil: waktuAmbil.toISOString(),
  };
}

function kategorisasiCurahHujan(curahHujanBulanan) {
  const value = angkaAtauNull(curahHujanBulanan);
  if (value === null || value < 0) return null;
  if (value > 200) return 'tinggi';
  if (value >= 100) return 'sedang';
  return 'rendah';
}

function dapatkanDaftarDesa() {
  return WILAYAH_AIKMEL.desa;
}

function kosongkanCache() {
  Object.keys(cacheCuaca).forEach((key) => delete cacheCuaca[key]);
}

module.exports = {
  ambilDataCuaca,
  prosesDataCuaca,
  kategorisasiCurahHujan,
  dapatkanDaftarDesa,
  kosongkanCache,
  WILAYAH_AIKMEL,
  BMKG_BASE_URL,
  CACHE_DURASI,
};

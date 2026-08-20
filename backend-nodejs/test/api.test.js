const test = require('node:test');
const assert = require('node:assert/strict');

const app = require('../src/app');
const bmkgService = require('../src/services/bmkgService');

let server;
let baseUrl;

test.before(async () => {
  await new Promise((resolve) => {
    server = app.listen(0, '127.0.0.1', resolve);
  });
  baseUrl = `http://127.0.0.1:${server.address().port}`;
});

test.after(async () => {
  await new Promise((resolve, reject) => {
    server.close((error) => (error ? reject(error) : resolve()));
  });
});

test('health endpoint memenuhi kontrak dasar', async () => {
  const response = await fetch(`${baseUrl}/api/kesehatan`);
  const body = await response.json();

  assert.equal(response.status, 200);
  assert.equal(body.status, 'baik');
  assert.ok(Date.parse(body.waktu));
});

test('rekomendasi manual memvalidasi input dan mengembalikan rule ID', async () => {
  const invalid = await fetch(`${baseUrl}/api/rekomendasi`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ curahHujan: 'sedang' }),
  });
  assert.equal(invalid.status, 400);

  const valid = await fetch(`${baseUrl}/api/rekomendasi`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({
      curahHujan: 'sedang',
      ketersediaanAir: 'cukup',
      tanamanSebelumnya: 'jagung',
      jenisLahan: 'sawah',
    }),
  });
  const body = await valid.json();

  assert.equal(valid.status, 200);
  assert.equal(body.status, 'berhasil');
  assert.ok(body.ruleId);
  assert.equal(body.recommendedCrop, body.rekomendasi[0].kode);
});

test('kalender BMKG mock menghasilkan empat minggu', async () => {
  const original = bmkgService.ambilDataCuaca;
  bmkgService.ambilDataCuaca = async () => ({
    lokasi: { desa: 'Aikmel', kecamatan: 'Aikmel', kotkab: 'Lombok Timur' },
    cuacaSaatIni: { waktu: '2026-08-04 08:00:00', suhu: 28, kelembaban: 75, kondisi: 'Cerah', curahHujan: 1 },
    totalCurahHujanPrakiraan: 10,
    totalCurahHujan3Hari: 10,
    estimasiCurahHujanBulanan: 150,
    cakupanCurahHujan: { jumlahTitikPrakiraan: 2, jumlahTitikDenganData: 2, jumlahHariPrakiraan: 1, lengkap: true },
    metodologiEstimasi: 'fixture',
    prakiraan: [
      { waktu: '2026-08-04 08:00:00', suhu: 28, kelembaban: 75, kondisi: 'Cerah', curahHujan: 1 },
      { waktu: '2026-08-04 11:00:00', suhu: 30, kelembaban: 70, kondisi: 'Cerah', curahHujan: 2 },
    ],
    sumberData: 'BMKG',
    waktuAmbil: '2026-08-04T00:00:00.000Z',
    cache: { status: 'network', isStale: false, ageSeconds: 0, ttlSeconds: 1800 },
  });

  try {
    const response = await fetch(`${baseUrl}/api/rekomendasi/kalender`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        kodeWilayah: '52.03.09.2002',
        ketersediaanAir: 'cukup',
        tanamanSebelumnya: 'padi',
        jenisLahan: 'sawah',
      }),
    });
    const body = await response.json();

    assert.equal(response.status, 200);
    assert.equal(body.kalender.rencanaMingguan.length, 4);
    assert.equal(body.cuaca.sumberData, 'BMKG');
  } finally {
    bmkgService.ambilDataCuaca = original;
  }
});

test('rekomendasi otomatis tidak mengarang kategori saat hujan tidak tersedia', async () => {
  const original = bmkgService.ambilDataCuaca;
  bmkgService.ambilDataCuaca = async () => ({
    lokasi: { desa: 'Aikmel' },
    cuacaSaatIni: { waktu: '2026-08-04 08:00:00', curahHujan: null },
    totalCurahHujanPrakiraan: null,
    totalCurahHujan3Hari: null,
    estimasiCurahHujanBulanan: null,
    cakupanCurahHujan: { jumlahTitikPrakiraan: 1, jumlahTitikDenganData: 0, jumlahHariPrakiraan: 1, lengkap: false },
    metodologiEstimasi: 'fixture missing rain',
    sumberData: 'BMKG',
    waktuAmbil: '2026-08-04T00:00:00.000Z',
    cache: { status: 'network', isStale: false },
  });

  try {
    const response = await fetch(`${baseUrl}/api/rekomendasi/otomatis`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        kodeWilayah: '52.03.09.2002',
        ketersediaanAir: 'cukup',
        tanamanSebelumnya: 'padi',
        jenisLahan: 'sawah',
      }),
    });
    const body = await response.json();

    assert.equal(response.status, 422);
    assert.equal(body.kode, 'DATA_CURAH_HUJAN_TIDAK_TERSEDIA');
    assert.equal(body.cuaca.kategoriCurahHujan, null);
  } finally {
    bmkgService.ambilDataCuaca = original;
  }
});

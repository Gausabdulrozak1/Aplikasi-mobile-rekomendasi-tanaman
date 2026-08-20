const test = require('node:test');
const assert = require('node:assert/strict');

const bmkgService = require('../src/services/bmkgService');
const { buatTitik, buatResponsBmkg } = require('./fixtures/bmkgFixture');

test.beforeEach(() => bmkgService.kosongkanCache());

test('parser mempertahankan field curah hujan yang hilang sebagai null', () => {
  const pointWithoutRain = buatTitik('2026-08-04 08:00:00');
  delete pointWithoutRain.tp;
  const raw = buatResponsBmkg([
    pointWithoutRain,
    buatTitik('2026-08-04 11:00:00', { tp: 2 }),
  ]);

  const result = bmkgService.prosesDataCuaca(raw, new Date('2026-08-04T00:00:00Z'));

  assert.equal(result.prakiraan[0].curahHujan, null);
  assert.equal(result.totalCurahHujanPrakiraan, null);
  assert.equal(result.estimasiCurahHujanBulanan, null);
  assert.equal(result.cakupanCurahHujan.lengkap, false);
});

test('parser memproyeksikan data lengkap dan mencatat metodologinya', () => {
  const raw = buatResponsBmkg([
    buatTitik('2026-08-04 08:00:00', { tp: 1 }),
    buatTitik('2026-08-04 11:00:00', { tp: 2 }),
    buatTitik('2026-08-05 08:00:00', { tp: 3 }),
    buatTitik('2026-08-05 11:00:00', { tp: 4 }),
  ]);

  const result = bmkgService.prosesDataCuaca(raw);

  assert.equal(result.totalCurahHujanPrakiraan, 10);
  assert.equal(result.estimasiCurahHujanBulanan, 150);
  assert.equal(result.cakupanCurahHujan.jumlahHariPrakiraan, 2);
  assert.match(result.metodologiEstimasi, /bukan prakiraan bulanan BMKG/);
});

test('kategori curah hujan menolak nilai kosong dan negatif', () => {
  assert.equal(bmkgService.kategorisasiCurahHujan(null), null);
  assert.equal(bmkgService.kategorisasiCurahHujan(undefined), null);
  assert.equal(bmkgService.kategorisasiCurahHujan(-1), null);
  assert.equal(bmkgService.kategorisasiCurahHujan(99), 'rendah');
  assert.equal(bmkgService.kategorisasiCurahHujan(100), 'sedang');
  assert.equal(bmkgService.kategorisasiCurahHujan(201), 'tinggi');
});

test('request memakai timeout, cache segar, lalu cache stale saat BMKG gagal', async () => {
  let calls = 0;
  let observedTimeout;
  let currentTime = Date.parse('2026-08-04T00:00:00Z');
  const raw = buatResponsBmkg([
    buatTitik('2026-08-04 08:00:00', { tp: 1 }),
  ]);
  const httpClient = {
    async get(url, options) {
      calls += 1;
      observedTimeout = options.timeout;
      if (calls > 1) throw new Error('simulated timeout');
      return { data: raw };
    },
  };
  const options = { httpClient, now: () => currentTime };

  const network = await bmkgService.ambilDataCuaca('52.03.09.2002', options);
  assert.equal(network.cache.status, 'network');
  assert.equal(observedTimeout, 15000);

  currentTime += 1000;
  const fresh = await bmkgService.ambilDataCuaca('52.03.09.2002', options);
  assert.equal(fresh.cache.status, 'fresh-cache');
  assert.equal(calls, 1);

  currentTime += bmkgService.CACHE_DURASI + 1;
  const stale = await bmkgService.ambilDataCuaca('52.03.09.2002', options);
  assert.equal(stale.cache.status, 'stale-cache');
  assert.equal(stale.cache.isStale, true);
  assert.equal(calls, 2);
});

test('kegagalan tanpa cache menghasilkan kode terstruktur', async () => {
  const httpClient = { get: async () => { throw new Error('timeout'); } };

  await assert.rejects(
    bmkgService.ambilDataCuaca('52.03.09.9999', { httpClient }),
    (error) => error.code === 'BMKG_UNAVAILABLE' && /timeout/.test(error.message)
  );
});

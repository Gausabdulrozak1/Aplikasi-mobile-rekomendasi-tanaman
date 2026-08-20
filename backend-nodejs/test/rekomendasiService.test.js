const test = require('node:test');
const assert = require('node:assert/strict');

const { ATURAN_ROTASI } = require('../src/config/aturanRotasi');
const service = require('../src/services/rekomendasiService');

const TANAMAN_VALID = new Set(['padi', 'jagung', 'cabai', 'kacang_tanah']);

test('seluruh decision table menghasilkan output valid dan dapat diaudit', () => {
  for (const kunci of Object.keys(ATURAN_ROTASI)) {
    const [curahHujan, ketersediaanAir, ...tanamanParts] = kunci.split('_');
    const tanamanSebelumnya = tanamanParts.join('_');
    const result = service.dapatkanRekomendasi({
      curahHujan,
      ketersediaanAir,
      tanamanSebelumnya,
      jenisLahan: 'sawah',
    });

    assert.equal(result.status, 'berhasil', kunci);
    assert.equal(result.kunciAturan, kunci);
    assert.equal(result.menggunakanAturanDefault, false);
    assert.ok(result.ruleId.startsWith('ROT-'));
    assert.equal(result.recommendedCrop, result.rekomendasi[0].kode);
    assert.deepEqual(result.inputSummary, {
      kondisiCuaca: curahHujan,
      jenisLahan: 'sawah',
      ketersediaanAir,
      tanamanSebelumnya,
    });
    assert.ok(result.rekomendasi.every((item) => TANAMAN_VALID.has(item.kode)));
  }
});

test('gabungan seluruh aturan mencakup empat kelas keluaran', () => {
  const output = new Set(
    Object.values(ATURAN_ROTASI).flatMap((aturan) => aturan.rekomendasi)
  );
  assert.deepEqual(output, TANAMAN_VALID);
});

test('input tidak lengkap dan input tidak valid ditolak', () => {
  const incomplete = service.dapatkanRekomendasi({
    curahHujan: 'sedang',
    ketersediaanAir: 'cukup',
    tanamanSebelumnya: 'padi',
  });
  assert.equal(incomplete.status, 'gagal');
  assert.match(incomplete.errors.join(' '), /Jenis lahan/);

  const invalid = service.dapatkanRekomendasi({
    curahHujan: 'ekstrem',
    ketersediaanAir: 'cukup',
    tanamanSebelumnya: 'padi',
    jenisLahan: 'sawah',
  });
  assert.equal(invalid.status, 'gagal');
});

test('pencarian rule yang tidak ditemukan memakai default secara eksplisit', () => {
  const result = service.cariAturan('tidak_ada', {});
  assert.equal(result.menggunakanDefault, true);
  assert.ok(result.aturan.rekomendasi.length > 0);
});

test('hasil deterministik dan jenis lahan memengaruhi prioritas', () => {
  const input = {
    curahHujan: 'tinggi',
    ketersediaanAir: 'cukup',
    tanamanSebelumnya: 'padi',
    jenisLahan: 'tegalan',
  };
  const first = service.dapatkanRekomendasi(input);
  const second = service.dapatkanRekomendasi(input);

  assert.deepEqual(first, second);
  assert.equal(first.recommendedCrop, 'jagung');
  assert.match(first.reason, /bukan lahan sawah/);
});

test('rencana bulanan menghasilkan empat minggu dengan tanggal stabil', () => {
  const result = service.dapatkanRencanaBulanan(
    {
      curahHujan: 'sedang',
      ketersediaanAir: 'cukup',
      tanamanSebelumnya: 'jagung',
      jenisLahan: 'sawah',
    },
    { tanggalAcuan: new Date(2026, 7, 4) }
  );

  assert.equal(result.status, 'berhasil');
  assert.equal(result.rencanaMingguan.length, 4);
  assert.equal(result.periode.mulai, '2026-08-04');
  assert.equal(result.periode.selesai, '2026-08-31');
  assert.equal(result.rencanaMingguan[1].tanggalMulai, '2026-08-11');
  assert.ok(result.ruleId);
});

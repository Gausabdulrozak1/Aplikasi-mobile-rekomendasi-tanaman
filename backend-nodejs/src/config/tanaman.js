// Data komoditas sesuai ruang lingkup proposal (BAB I.4):
// padi, jagung, cabai, kacang tanah

const DATA_TANAMAN = {
  padi: {
    nama: 'Padi',
    namaIlmiah: 'Oryza sativa',
    keluarga: 'Sereal',
    hariTumbuh: 120,
    kebutuhanAir: 'tinggi',
    curahHujanIdeal: 'tinggi',
    deskripsi: 'Tanaman pangan utama, membutuhkan banyak air dan cocok di sawah.',
  },
  jagung: {
    nama: 'Jagung',
    namaIlmiah: 'Zea mays',
    keluarga: 'Sereal',
    hariTumbuh: 90,
    kebutuhanAir: 'sedang',
    curahHujanIdeal: 'sedang',
    deskripsi: 'Tanaman dengan siklus pendek, cocok untuk lahan kering hingga sedang.',
  },
  cabai: {
    nama: 'Cabai',
    namaIlmiah: 'Capsicum annuum',
    keluarga: 'Sayuran',
    hariTumbuh: 120,
    kebutuhanAir: 'sedang',
    curahHujanIdeal: 'rendah',
    deskripsi: 'Bernilai jual tinggi, cocok di musim kemarau dengan irigasi cukup.',
  },
  kacang_tanah: {
    nama: 'Kacang Tanah',
    namaIlmiah: 'Arachis hypogaea',
    keluarga: 'Legum',
    hariTumbuh: 100,
    kebutuhanAir: 'rendah',
    curahHujanIdeal: 'sedang',
    deskripsi: 'Tanaman legum yang memperbaiki kesuburan tanah (mengikat nitrogen).',
  },
};

module.exports = DATA_TANAMAN;
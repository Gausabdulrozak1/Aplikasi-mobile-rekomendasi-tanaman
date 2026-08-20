// ============================================
// DECISION TABLE - ATURAN ROTASI TANAM
// Sesuai proposal BAB III.2.3 (Rule-Based Engine)
// ============================================
//
// Prinsip rotasi tanam:
// 1. Utamakan kesesuaian dengan kondisi cuaca dan ketersediaan air
// 2. Padi sebagai tanaman utama muncul di hampir semua kondisi
// 3. Variasikan dengan jagung (sereal lain), cabai (sayuran), kacang tanah (legum)
//
// Format kunci: "curahHujan_ketersediaanAir_tanamanSebelumnya"
// ============================================

const ATURAN_ROTASI = {
  // ===== SETELAH PADI =====
  'tinggi_cukup_padi': {
    rekomendasi: ['padi', 'jagung'],
    alasan: 'Curah hujan tinggi dan air cukup sangat cocok untuk padi. Jagung sebagai alternatif dengan siklus lebih pendek.',
  },
  'sedang_cukup_padi': {
    rekomendasi: ['padi', 'jagung', 'kacang_tanah'],
    alasan: 'Curah hujan sedang dengan air cukup masih ideal untuk padi. Jagung dan kacang tanah sebagai variasi rotasi untuk menjaga kesuburan tanah.',
  },
  'rendah_cukup_padi': {
    rekomendasi: ['cabai', 'kacang_tanah', 'padi'],
    alasan: 'Curah hujan rendah, padi masih bisa dengan irigasi. Cabai bernilai jual tinggi dan kacang tanah hemat air menjadi alternatif.',
  },
  'tinggi_terbatas_padi': {
    rekomendasi: ['padi', 'jagung', 'kacang_tanah'],
    alasan: 'Curah hujan tinggi membantu mencukupi kebutuhan air padi. Jagung dan kacang tanah sebagai variasi rotasi.',
  },
  'sedang_terbatas_padi': {
    rekomendasi: ['jagung', 'kacang_tanah', 'padi'],
    alasan: 'Air terbatas, jagung dan kacang tanah lebih hemat air. Padi masih mungkin dengan pengelolaan air yang baik.',
  },
  'rendah_terbatas_padi': {
    rekomendasi: ['kacang_tanah', 'cabai', 'jagung'],
    alasan: 'Kondisi kering dengan air terbatas, kacang tanah dan cabai lebih tahan. Jagung sebagai alternatif ketiga.',
  },

  // ===== SETELAH JAGUNG =====
  'tinggi_cukup_jagung': {
    rekomendasi: ['padi', 'jagung', 'kacang_tanah'],
    alasan: 'Air melimpah cocok untuk padi. Jagung masih bisa dengan rotasi varietas. Kacang tanah memulihkan nitrogen.',
  },
  'sedang_cukup_jagung': {
    rekomendasi: ['padi', 'jagung', 'kacang_tanah'],
    alasan: 'Padi cocok dengan curah hujan sedang. Jagung dan kacang tanah sebagai pilihan rotasi.',
  },
  'rendah_cukup_jagung': {
    rekomendasi: ['cabai', 'kacang_tanah', 'jagung'],
    alasan: 'Curah hujan rendah ideal untuk cabai dengan irigasi. Kacang tanah menyuburkan tanah.',
  },
  'tinggi_terbatas_jagung': {
    rekomendasi: ['padi', 'jagung', 'kacang_tanah'],
    alasan: 'Curah hujan tinggi mendukung padi. Jagung dan kacang tanah sebagai variasi.',
  },
  'sedang_terbatas_jagung': {
    rekomendasi: ['jagung', 'kacang_tanah', 'padi'],
    alasan: 'Jagung adaptif dengan air terbatas. Kacang tanah hemat air dan menyuburkan tanah.',
  },
  'rendah_terbatas_jagung': {
    rekomendasi: ['kacang_tanah', 'cabai', 'jagung'],
    alasan: 'Kondisi kering, kacang tanah paling sesuai. Cabai dan jagung sebagai alternatif.',
  },

  // ===== SETELAH CABAI =====
  'tinggi_cukup_cabai': {
    rekomendasi: ['padi', 'jagung', 'cabai'],
    alasan: 'Setelah cabai, padi dan jagung memutus siklus hama. Cabai masih bisa dengan rotasi varietas.',
  },
  'sedang_cukup_cabai': {
    rekomendasi: ['padi', 'jagung', 'kacang_tanah'],
    alasan: 'Padi dan jagung cocok setelah cabai. Kacang tanah sebagai legum penyubur tanah.',
  },
  'rendah_cukup_cabai': {
    rekomendasi: ['cabai', 'kacang_tanah', 'jagung'],
    alasan: 'Cabai tetap cocok di musim kemarau. Kacang tanah dan jagung untuk variasi rotasi.',
  },
  'tinggi_terbatas_cabai': {
    rekomendasi: ['padi', 'jagung', 'kacang_tanah'],
    alasan: 'Curah hujan tinggi mendukung padi meski air terbatas. Jagung dan kacang tanah sebagai alternatif.',
  },
  'sedang_terbatas_cabai': {
    rekomendasi: ['jagung', 'kacang_tanah', 'cabai'],
    alasan: 'Jagung adaptif dengan air terbatas. Kacang tanah dan cabai sebagai alternatif.',
  },
  'rendah_terbatas_cabai': {
    rekomendasi: ['kacang_tanah', 'cabai', 'jagung'],
    alasan: 'Kondisi kering, kacang tanah paling tahan. Cabai dengan penyiraman terjadwal.',
  },

  // ===== SETELAH KACANG TANAH =====
  'tinggi_cukup_kacang_tanah': {
    rekomendasi: ['padi', 'jagung', 'kacang_tanah'],
    alasan: 'Tanah subur setelah kacang tanah. Padi memanfaatkan nitrogen yang tersedia. Jagung sebagai alternatif sereal.',
  },
  'sedang_cukup_kacang_tanah': {
    rekomendasi: ['padi', 'jagung', 'cabai'],
    alasan: 'Padi cocok setelah legum karena tanah subur. Jagung dan cabai sebagai variasi rotasi.',
  },
  'rendah_cukup_kacang_tanah': {
    rekomendasi: ['cabai', 'jagung', 'padi'],
    alasan: 'Curah hujan rendah, cabai dan jagung lebih cocok. Padi masih mungkin dengan irigasi.',
  },
  'tinggi_terbatas_kacang_tanah': {
    rekomendasi: ['padi', 'jagung', 'kacang_tanah'],
    alasan: 'Curah hujan tinggi mendukung padi. Jagung dan kacang tanah sebagai variasi.',
  },
  'sedang_terbatas_kacang_tanah': {
    rekomendasi: ['jagung', 'padi', 'kacang_tanah'],
    alasan: 'Jagung adaptif dengan air terbatas. Padi dan kacang tanah sebagai alternatif.',
  },
  'rendah_terbatas_kacang_tanah': {
    rekomendasi: ['cabai', 'kacang_tanah', 'jagung'],
    alasan: 'Cabai cocok di musim kemarau. Kacang tanah dan jagung sebagai variasi.',
  },

  // ===== LAHAN KOSONG (BELUM ADA TANAMAN) =====
  'tinggi_cukup_kosong': {
    rekomendasi: ['padi', 'jagung', 'kacang_tanah'],
    alasan: 'Air melimpah ideal untuk padi. Jagung dan kacang tanah sebagai variasi awal tanam.',
  },
  'sedang_cukup_kosong': {
    rekomendasi: ['padi', 'jagung', 'cabai'],
    alasan: 'Curah hujan sedang cocok untuk padi. Jagung dan cabai sebagai alternatif diversifikasi.',
  },
  'rendah_cukup_kosong': {
    rekomendasi: ['cabai', 'kacang_tanah', 'padi'],
    alasan: 'Kondisi kering cocok untuk cabai dan kacang tanah. Padi masih mungkin dengan irigasi.',
  },
  'tinggi_terbatas_kosong': {
    rekomendasi: ['padi', 'jagung', 'kacang_tanah'],
    alasan: 'Curah hujan tinggi membantu memenuhi kebutuhan air. Jagung dan kacang tanah sebagai variasi.',
  },
  'sedang_terbatas_kosong': {
    rekomendasi: ['jagung', 'kacang_tanah', 'padi'],
    alasan: 'Jagung dan kacang tanah lebih hemat air. Padi dengan pengelolaan air yang baik.',
  },
  'rendah_terbatas_kosong': {
    rekomendasi: ['kacang_tanah', 'cabai', 'jagung'],
    alasan: 'Kondisi paling kering, kacang tanah paling tahan. Cabai dan jagung sebagai alternatif.',
  },
};

// Aturan default jika kombinasi tidak ditemukan
const ATURAN_DEFAULT = {
  rekomendasi: ['padi', 'jagung', 'kacang_tanah'],
  alasan: 'Rekomendasi umum: padi sebagai tanaman utama, jagung dan kacang tanah untuk diversifikasi.',
};

module.exports = { ATURAN_ROTASI, ATURAN_DEFAULT };

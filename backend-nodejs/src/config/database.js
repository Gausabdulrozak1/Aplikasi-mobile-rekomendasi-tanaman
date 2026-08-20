const sqlite3 = require('sqlite3').verbose();
const path = require('path');
const fs = require('fs');
const logger = require('../utils/logger');

// Buat folder data jika belum ada
const dataDir = path.join(__dirname, '../../data');
if (!fs.existsSync(dataDir)) {
  fs.mkdirSync(dataDir, { recursive: true });
}

// Path database
const dbPath = path.join(dataDir, 'tani_adaptif.db');

// Koneksi ke database
const db = new sqlite3.Database(dbPath, (err) => {
  if (err) {
    logger.error('Gagal koneksi database:', err.message);
  } else {
    logger.info('Database SQLite terhubung di: ' + dbPath);
    buatTabel();
  }
});

// Fungsi membuat semua tabel
function buatTabel() {
  db.serialize(() => {
    // Tabel Petani (sesuai ERD di proposal)
    db.run(`
      CREATE TABLE IF NOT EXISTS petani (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nama TEXT NOT NULL,
        email TEXT,
        nomor_hp TEXT,
        latitude REAL,
        longitude REAL,
        dibuat_pada DATETIME DEFAULT CURRENT_TIMESTAMP
      )
    `, (err) => {
      if (!err) logger.info('Tabel petani siap');
    });

    // Tabel Lahan (sesuai ERD di proposal)
    db.run(`
      CREATE TABLE IF NOT EXISTS lahan (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        petani_id INTEGER,
        nama_lahan TEXT NOT NULL,
        jenis_lahan TEXT,
        ketersediaan_air TEXT,
        tanaman_sebelumnya TEXT,
        latitude REAL,
        longitude REAL,
        dibuat_pada DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (petani_id) REFERENCES petani(id)
      )
    `, (err) => {
      if (!err) logger.info('Tabel lahan siap');
    });

    // Tabel Cuaca (sesuai ERD di proposal)
    db.run(`
      CREATE TABLE IF NOT EXISTS cuaca (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lahan_id INTEGER,
        tanggal DATE,
        suhu REAL,
        curah_hujan REAL,
        kategori_curah_hujan TEXT,
        kelembaban REAL,
        kondisi TEXT,
        dibuat_pada DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (lahan_id) REFERENCES lahan(id)
      )
    `, (err) => {
      if (!err) logger.info('Tabel cuaca siap');
    });

    // Tabel Rekomendasi (sesuai ERD di proposal)
    db.run(`
      CREATE TABLE IF NOT EXISTS rekomendasi (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lahan_id INTEGER,
        tanaman_sebelumnya TEXT,
        tanaman_direkomendasikan TEXT,
        alasan TEXT,
        dibuat_pada DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (lahan_id) REFERENCES lahan(id)
      )
    `, (err) => {
      if (!err) logger.info('Tabel rekomendasi siap');
    });

    // Tabel Simulasi Visual (sesuai ERD di proposal)
    db.run(`
      CREATE TABLE IF NOT EXISTS simulasi_visual (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        rekomendasi_id INTEGER,
        prompt TEXT,
        negative_prompt TEXT,
        seed INTEGER,
        url_gambar TEXT,
        dibuat_pada DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (rekomendasi_id) REFERENCES rekomendasi(id)
      )
    `, (err) => {
      if (!err) logger.info('Tabel simulasi_visual siap');
    });

    // Tabel UAT (untuk pengujian penerimaan pengguna)
    db.run(`
      CREATE TABLE IF NOT EXISTS uat (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        responden TEXT,
        skor INTEGER,
        catatan TEXT,
        dibuat_pada DATETIME DEFAULT CURRENT_TIMESTAMP
      )
    `, (err) => {
      if (!err) logger.info('Tabel uat siap');
    });

    logger.info('Semua tabel database berhasil dibuat!');
  });
}

module.exports = db;
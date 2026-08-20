const fs = require('fs');
const path = require('path');

// Buat folder logs jika belum ada
const logsDir = path.join(__dirname, '../../logs');
if (!fs.existsSync(logsDir)) {
  fs.mkdirSync(logsDir, { recursive: true });
}

// Fungsi untuk mendapatkan waktu sekarang
function getWaktu() {
  return new Date().toISOString();
}

// Fungsi mencatat log
function catat(level, pesan, data = '') {
  const logPesan = `[${getWaktu()}] ${level}: ${pesan} ${data}`;
  
  // Tampilkan di console
  console.log(logPesan);
  
  // Simpan ke file
  const namaFile = `app-${new Date().toISOString().split('T')[0]}.log`;
  const logFile = path.join(logsDir, namaFile);
  fs.appendFileSync(logFile, logPesan + '\n');
}

// Export fungsi-fungsi log
module.exports = {
  info: (pesan, data) => catat('INFO', pesan, data),
  error: (pesan, data) => catat('ERROR', pesan, data),
  warn: (pesan, data) => catat('WARNING', pesan, data),
};
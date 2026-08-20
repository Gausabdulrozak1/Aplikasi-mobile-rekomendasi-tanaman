const express = require('express');
const cors = require('cors');
const logger = require('./utils/logger');
const cuacaRoutes = require('./routes/cuacaRoutes');
const rekomendasiRoutes = require('./routes/rekomendasiRoutes');
const visualRoutes = require('./routes/visualRoutes');

const app = express();

app.disable('x-powered-by');
if (process.env.TRUST_PROXY) app.set('trust proxy', process.env.TRUST_PROXY);

const configuredOrigins = (process.env.CORS_ORIGINS || '*')
  .split(',')
  .map((value) => value.trim())
  .filter(Boolean);
app.use(cors({
  origin: configuredOrigins.includes('*')
    ? true
    : (origin, callback) => callback(null, !origin || configuredOrigins.includes(origin)),
}));
app.use(express.json({ limit: '100kb' }));
app.use(express.urlencoded({ extended: true, limit: '100kb' }));
app.use((req, res, next) => {
  res.set({
    'X-Content-Type-Options': 'nosniff',
    'X-Frame-Options': 'DENY',
    'Referrer-Policy': 'no-referrer',
  });
  next();
});

app.use((req, res, next) => {
  logger.info(`${req.method} ${req.path}`);
  next();
});

app.get('/api/kesehatan', (req, res) => {
  res.json({
    status: 'baik',
    pesan: 'Server TaniAdaptif berjalan dengan baik.',
    versi: '1.1.0',
    waktu: new Date().toISOString(),
  });
});

app.use('/api/cuaca', cuacaRoutes);
app.use('/api/rekomendasi', rekomendasiRoutes);
app.use('/api/visual', visualRoutes);

app.use((req, res) => {
  res.status(404).json({
    status: 'gagal',
    pesan: 'Endpoint tidak ditemukan',
  });
});

module.exports = app;

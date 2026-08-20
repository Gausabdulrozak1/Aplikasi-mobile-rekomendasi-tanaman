require('dotenv').config();
require('./config/database');

const app = require('./app');
const logger = require('./utils/logger');

const port = Number(process.env.PORT || 3000);

const server = app.listen(port, () => {
  logger.info('Server TaniAdaptif berjalan');
  logger.info(`Alamat: http://localhost:${port}`);
  logger.info(`Cek kesehatan: http://localhost:${port}/api/kesehatan`);
});

module.exports = server;

const axios = require('axios');

class InferenceServiceError extends Error {
  constructor(statusCode, code, message, retryable = false, details = undefined) {
    super(message);
    this.name = 'InferenceServiceError';
    this.statusCode = statusCode;
    this.code = code;
    this.retryable = retryable;
    this.details = details;
  }
}

function parseBoundedInteger(rawValue, fallback, minimum, maximum) {
  const value = Number(rawValue || fallback);
  if (!Number.isInteger(value) || value < minimum || value > maximum) {
    throw new Error(`Nilai konfigurasi harus berupa integer ${minimum}-${maximum}`);
  }
  return value;
}

function getConfiguration() {
  const rawBaseUrl = process.env.INFERENCE_API_BASE_URL || 'http://127.0.0.1:5000';
  let parsed;
  try {
    parsed = new URL(rawBaseUrl);
  } catch {
    throw new Error('INFERENCE_API_BASE_URL bukan URL valid');
  }
  if (!['http:', 'https:'].includes(parsed.protocol) || parsed.username || parsed.password) {
    throw new Error('INFERENCE_API_BASE_URL harus HTTP(S) tanpa credential pada URL');
  }
  parsed.search = '';
  parsed.hash = '';
  parsed.pathname = parsed.pathname.replace(/\/+$/, '');
  return {
    baseUrl: parsed.toString().replace(/\/$/, ''),
    token: (process.env.INFERENCE_API_TOKEN || '').trim(),
    timeoutMs: parseBoundedInteger(process.env.INFERENCE_API_TIMEOUT_MS, 120000, 1000, 300000),
    imageMaxBytes: parseBoundedInteger(
      process.env.INFERENCE_IMAGE_MAX_BYTES,
      10 * 1024 * 1024,
      1024,
      25 * 1024 * 1024,
    ),
  };
}

function requestHeaders(requestId) {
  const config = getConfiguration();
  return {
    Accept: 'application/json',
    ...(requestId ? { 'X-Request-ID': requestId } : {}),
    ...(config.token ? { 'X-Inference-Token': config.token } : {}),
  };
}

function normalizeTransportError(error) {
  if (error.code === 'ECONNABORTED' || error.code === 'ETIMEDOUT') {
    return new InferenceServiceError(
      504,
      'INFERENCE_TIMEOUT',
      'Layanan GPU melewati batas waktu backend.',
      true,
    );
  }
  return new InferenceServiceError(
    503,
    'INFERENCE_UNAVAILABLE',
    'Layanan inference GPU belum dapat dijangkau.',
    true,
  );
}

function normalizeUpstreamError(response) {
  const body = response.data && typeof response.data === 'object' ? response.data : {};
  const upstream = body.error && typeof body.error === 'object' ? body.error : {};
  const statusCode = response.status >= 400 && response.status <= 599 ? response.status : 502;
  return new InferenceServiceError(
    statusCode,
    String(upstream.code || 'INFERENCE_UPSTREAM_ERROR'),
    String(upstream.message || 'Layanan inference menolak permintaan.'),
    upstream.retryable === true,
    { upstream_status: response.status },
  );
}

async function requestJson(method, url, { data, requestId } = {}) {
  const config = getConfiguration();
  let response;
  try {
    response = await axios.request({
      method,
      baseURL: config.baseUrl,
      url,
      data,
      timeout: config.timeoutMs,
      headers: requestHeaders(requestId),
      maxBodyLength: 128 * 1024,
      maxContentLength: 2 * 1024 * 1024,
      validateStatus: () => true,
    });
  } catch (error) {
    throw normalizeTransportError(error);
  }
  if (response.status < 200 || response.status >= 300) {
    throw normalizeUpstreamError(response);
  }
  if (!response.data || typeof response.data !== 'object') {
    throw new InferenceServiceError(
      502,
      'INFERENCE_INVALID_RESPONSE',
      'Layanan inference mengembalikan respons yang tidak valid.',
      true,
    );
  }
  return response.data;
}

async function fetchGeneratedImage(fileName, requestId) {
  const config = getConfiguration();
  let response;
  try {
    response = await axios.get(`/static/generated/${encodeURIComponent(fileName)}`, {
      baseURL: config.baseUrl,
      timeout: config.timeoutMs,
      headers: {
        ...requestHeaders(requestId),
        Accept: 'image/png',
      },
      responseType: 'arraybuffer',
      maxContentLength: config.imageMaxBytes,
      validateStatus: () => true,
    });
  } catch (error) {
    throw normalizeTransportError(error);
  }
  if (response.status < 200 || response.status >= 300) {
    throw normalizeUpstreamError(response);
  }
  const contentType = String(response.headers['content-type'] || '').toLowerCase();
  const image = Buffer.from(response.data);
  if (contentType !== 'image/png' || image.length === 0 || image.length > config.imageMaxBytes) {
    throw new InferenceServiceError(
      502,
      'INFERENCE_INVALID_IMAGE',
      'Layanan inference mengembalikan gambar yang tidak valid.',
      true,
    );
  }
  return image;
}

module.exports = {
  InferenceServiceError,
  fetchGeneratedImage,
  generate: (payload, requestId) =>
    requestJson('POST', '/v1/generate', { data: payload, requestId }),
  getModelInfo: (requestId) => requestJson('GET', '/v1/model-info', { requestId }),
  getReadiness: (requestId) => requestJson('GET', '/ready', { requestId }),
  getConfiguration,
};

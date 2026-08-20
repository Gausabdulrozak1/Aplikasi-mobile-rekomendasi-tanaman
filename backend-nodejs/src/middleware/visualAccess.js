const crypto = require('crypto');

const requestBuckets = new Map();

function parseBoundedInteger(rawValue, fallback, minimum, maximum) {
  const value = Number(rawValue ?? fallback);
  if (!Number.isInteger(value) || value < minimum || value > maximum) {
    return null;
  }
  return value;
}

function secureEqual(left, right) {
  const leftBuffer = Buffer.from(left);
  const rightBuffer = Buffer.from(right);
  return leftBuffer.length === rightBuffer.length && crypto.timingSafeEqual(leftBuffer, rightBuffer);
}

function sendAccessError(res, requestId, statusCode, code, message, retryable = false) {
  return res.status(statusCode).json({
    success: false,
    request_id: requestId,
    error: { code, message, retryable },
  });
}

function requireVisualClientToken(req, res, next) {
  if (String(process.env.BACKEND_VISUAL_REQUIRE_TOKEN).toLowerCase() !== 'true') {
    return next();
  }
  const expected = (process.env.BACKEND_VISUAL_API_TOKEN || '').trim();
  if (expected.length < 32 || expected.toLowerCase().startsWith('replace-with')) {
    return sendAccessError(
      res,
      req.visualRequestId,
      503,
      'VISUAL_AUTH_MISCONFIGURED',
      'Autentikasi layanan visual belum dikonfigurasi dengan benar.',
      false,
    );
  }
  const supplied = req.get('X-Client-Token') || '';
  if (!secureEqual(supplied, expected)) {
    return sendAccessError(
      res,
      req.visualRequestId,
      401,
      'VISUAL_AUTH_REQUIRED',
      'Kredensial layanan visual tidak valid.',
      false,
    );
  }
  return next();
}

function limitVisualRequests(req, res, next) {
  const windowMs = parseBoundedInteger(
    process.env.VISUAL_RATE_LIMIT_WINDOW_MS,
    60000,
    1000,
    3600000,
  );
  const maximum = parseBoundedInteger(process.env.VISUAL_RATE_LIMIT_MAX, 0, 0, 1000);
  if (windowMs === null || maximum === null) {
    return sendAccessError(
      res,
      req.visualRequestId,
      503,
      'VISUAL_RATE_LIMIT_MISCONFIGURED',
      'Pembatasan permintaan layanan visual belum dikonfigurasi dengan benar.',
      false,
    );
  }
  if (maximum === 0) return next();

  const now = Date.now();
  const key = req.ip || req.socket.remoteAddress || 'unknown';
  const recent = (requestBuckets.get(key) || []).filter((timestamp) => now - timestamp < windowMs);
  if (recent.length >= maximum) {
    const retryAfterSeconds = Math.max(1, Math.ceil((windowMs - (now - recent[0])) / 1000));
    requestBuckets.set(key, recent);
    res.set('Retry-After', String(retryAfterSeconds));
    return sendAccessError(
      res,
      req.visualRequestId,
      429,
      'VISUAL_RATE_LIMITED',
      'Batas permintaan simulasi visual sementara tercapai.',
      true,
    );
  }
  recent.push(now);
  requestBuckets.set(key, recent);
  return next();
}

function resetVisualAccessForTests() {
  requestBuckets.clear();
}

module.exports = {
  limitVisualRequests,
  requireVisualClientToken,
  resetVisualAccessForTests,
};

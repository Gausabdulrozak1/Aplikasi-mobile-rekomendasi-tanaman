const crypto = require('crypto');
const express = require('express');

const {
  limitVisualRequests,
  requireVisualClientToken,
} = require('../middleware/visualAccess');
const inferenceService = require('../services/inferenceService');
const logger = require('../utils/logger');

const router = express.Router();
const SAFE_REQUEST_ID = /^[A-Za-z0-9._-]{1,64}$/;
const SAFE_PNG_NAME = /^[A-Za-z0-9._-]{1,180}\.png$/;

function requestIdFor(req) {
  const candidates = [req.body?.request_id, req.get('X-Request-ID')];
  const candidate = candidates.find((value) => typeof value === 'string' && SAFE_REQUEST_ID.test(value));
  return candidate || crypto.randomBytes(8).toString('hex');
}

router.use((req, res, next) => {
  req.visualRequestId = requestIdFor(req);
  res.set('X-Request-ID', req.visualRequestId);
  next();
});
router.use(requireVisualClientToken);

function publicBaseUrl(req) {
  const configured = (process.env.PUBLIC_API_BASE_URL || '').trim().replace(/\/+$/, '');
  if (configured) {
    let parsed;
    try {
      parsed = new URL(configured);
    } catch {
      throw new Error('PUBLIC_API_BASE_URL bukan URL valid');
    }
    if (!['http:', 'https:'].includes(parsed.protocol) || parsed.username || parsed.password) {
      throw new Error('PUBLIC_API_BASE_URL harus HTTP(S) tanpa credential');
    }
    return configured;
  }
  return `${req.protocol}://${req.get('host')}`;
}

function generatedFileName(rawUrl) {
  let parsed;
  try {
    parsed = new URL(rawUrl);
  } catch {
    throw new inferenceService.InferenceServiceError(
      502,
      'INFERENCE_INVALID_IMAGE_URL',
      'Layanan inference tidak mengembalikan URL gambar yang valid.',
      true,
    );
  }
  const fileName = decodeURIComponent(parsed.pathname.split('/').pop() || '');
  if (!SAFE_PNG_NAME.test(fileName)) {
    throw new inferenceService.InferenceServiceError(
      502,
      'INFERENCE_INVALID_IMAGE_URL',
      'Nama file gambar dari layanan inference tidak valid.',
      true,
    );
  }
  return fileName;
}

function handleError(res, error, requestId) {
  const known = error instanceof inferenceService.InferenceServiceError;
  const statusCode = known ? error.statusCode : 500;
  if (!known) logger.error('Visual proxy error:', error.message);
  res.status(statusCode).json({
    success: false,
    request_id: requestId,
    error: {
      code: known ? error.code : 'VISUAL_PROXY_ERROR',
      message: known ? error.message : 'Backend gagal memproses simulasi visual.',
      retryable: known ? error.retryable : false,
      ...(known && error.details ? { details: error.details } : {}),
    },
  });
}

router.get('/ready', async (req, res) => {
  const requestId = req.visualRequestId;
  try {
    return res.json(await inferenceService.getReadiness(requestId));
  } catch (error) {
    return handleError(res, error, requestId);
  }
});

router.get('/model-info', async (req, res) => {
  const requestId = req.visualRequestId;
  try {
    return res.json(await inferenceService.getModelInfo(requestId));
  } catch (error) {
    return handleError(res, error, requestId);
  }
});

router.post('/generate', limitVisualRequests, async (req, res) => {
  const requestId = req.visualRequestId;
  try {
    const payload = { ...req.body, request_id: requestId };
    const result = await inferenceService.generate(payload, requestId);
    const fileName = generatedFileName(result.image_url);
    return res.json({
      ...result,
      request_id: requestId,
      image_url: `${publicBaseUrl(req)}/api/visual/images/${encodeURIComponent(fileName)}`,
      metadata: {
        ...(result.metadata || {}),
        delivery_path: 'backend_proxy',
        upstream_image_url_exposed: false,
      },
    });
  } catch (error) {
    return handleError(res, error, requestId);
  }
});

router.get('/images/:fileName', async (req, res) => {
  const requestId = req.visualRequestId;
  if (!SAFE_PNG_NAME.test(req.params.fileName)) {
    return res.status(400).json({
      success: false,
      request_id: requestId,
      error: {
        code: 'INVALID_IMAGE_NAME',
        message: 'Nama file gambar tidak valid.',
        retryable: false,
      },
    });
  }
  try {
    const image = await inferenceService.fetchGeneratedImage(req.params.fileName, requestId);
    res.set({
      'Content-Type': 'image/png',
      'Content-Length': String(image.length),
      'Cache-Control': 'private, max-age=300',
      'X-Content-Type-Options': 'nosniff',
    });
    return res.send(image);
  } catch (error) {
    return handleError(res, error, requestId);
  }
});

module.exports = router;

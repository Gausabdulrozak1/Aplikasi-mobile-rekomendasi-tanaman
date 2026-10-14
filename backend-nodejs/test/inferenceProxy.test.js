const test = require('node:test');
const assert = require('node:assert/strict');
const http = require('node:http');

const app = require('../src/app');
const { resetVisualAccessForTests } = require('../src/middleware/visualAccess');

const PNG_1X1 = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=',
  'base64',
);
const TRIGGER_TOKENS = {
  padi: 'taniadaptif_padi',
  jagung: 'taniadaptif_jagung',
  cabai: 'taniadaptif_cabai',
  kacang_tanah: 'taniadaptif_kacang_tanah',
};

let upstreamServer;
let backendServer;
let upstreamUrl;
let backendUrl;
let lastUpstreamRequest;
const originalEnvironment = {};

async function readJson(request) {
  const chunks = [];
  for await (const chunk of request) chunks.push(chunk);
  return chunks.length ? JSON.parse(Buffer.concat(chunks).toString('utf8')) : {};
}

test.before(async () => {
  for (const key of [
    'INFERENCE_API_BASE_URL',
    'INFERENCE_API_TOKEN',
    'INFERENCE_API_TIMEOUT_MS',
    'PUBLIC_API_BASE_URL',
    'BACKEND_VISUAL_REQUIRE_TOKEN',
    'BACKEND_VISUAL_API_TOKEN',
    'VISUAL_RATE_LIMIT_WINDOW_MS',
    'VISUAL_RATE_LIMIT_MAX',
  ]) {
    originalEnvironment[key] = process.env[key];
  }
  upstreamServer = http.createServer(async (request, response) => {
    lastUpstreamRequest = {
      method: request.method,
      url: request.url,
      token: request.headers['x-inference-token'],
      requestId: request.headers['x-request-id'],
      body: request.method === 'POST' ? await readJson(request) : null,
    };
    if (request.url === '/ready') {
      response.writeHead(200, { 'content-type': 'application/json' });
      response.end(JSON.stringify({ status: 'ready', provider: 'diffusers', device: 'cuda', model_loaded: true }));
      return;
    }
    if (request.url === '/v1/model-info') {
      response.writeHead(200, { 'content-type': 'application/json' });
      response.end(JSON.stringify({
        base_model: 'stable-diffusion-v1-5/stable-diffusion-v1-5',
        lora_identifier: 'multisource_multicrop_lora_sd15_20260820T143551Z',
        provider: 'diffusers',
        supported_crops: ['padi', 'jagung', 'cabai', 'kacang_tanah'],
        trigger_tokens: {},
        pilot_trigger_tokens: {},
        supported_request_modes: ['structured_context'],
        supported_width: [512],
        supported_height: [512],
        default_parameters: {},
      }));
      return;
    }
    if (request.url === '/v1/generate') {
      response.writeHead(200, { 'content-type': 'application/json' });
      response.end(JSON.stringify({
        success: true,
        request_id: lastUpstreamRequest.body.request_id,
        crop: lastUpstreamRequest.body.crop,
        image_url: `${upstreamUrl}/static/generated/test.png`,
        image_id: 'test',
        seed: 42,
        generation_time_seconds: 1.25,
        model: 'stable-diffusion-v1-5/stable-diffusion-v1-5',
        metadata: {
          provider: 'diffusers',
          is_mock: false,
          crop: lastUpstreamRequest.body.crop,
          trigger_token: TRIGGER_TOKENS[lastUpstreamRequest.body.crop],
        },
      }));
      return;
    }
    if (request.url === '/static/generated/test.png') {
      response.writeHead(200, {
        'content-type': 'image/png',
        'content-length': PNG_1X1.length,
      });
      response.end(PNG_1X1);
      return;
    }
    response.writeHead(404, { 'content-type': 'application/json' });
    response.end(JSON.stringify({
      error: { code: 'NOT_FOUND', message: 'missing fixture', retryable: false },
    }));
  });
  await new Promise((resolve) => upstreamServer.listen(0, '127.0.0.1', resolve));
  upstreamUrl = `http://127.0.0.1:${upstreamServer.address().port}`;
  process.env.INFERENCE_API_BASE_URL = upstreamUrl;
  process.env.INFERENCE_API_TOKEN = 'private-inference-token-for-test';
  process.env.INFERENCE_API_TIMEOUT_MS = '5000';
  process.env.PUBLIC_API_BASE_URL = 'https://api.tani.test';
  process.env.BACKEND_VISUAL_REQUIRE_TOKEN = 'true';
  process.env.BACKEND_VISUAL_API_TOKEN = 'temporary-client-token-for-backend-tests';
  process.env.VISUAL_RATE_LIMIT_WINDOW_MS = '60000';
  process.env.VISUAL_RATE_LIMIT_MAX = '100';

  await new Promise((resolve) => {
    backendServer = app.listen(0, '127.0.0.1', resolve);
  });
  backendUrl = `http://127.0.0.1:${backendServer.address().port}`;
});

test.after(async () => {
  await Promise.all([
    new Promise((resolve, reject) => backendServer.close((error) => (error ? reject(error) : resolve()))),
    new Promise((resolve, reject) => upstreamServer.close((error) => (error ? reject(error) : resolve()))),
  ]);
  for (const [key, value] of Object.entries(originalEnvironment)) {
    if (value === undefined) delete process.env[key];
    else process.env[key] = value;
  }
  resetVisualAccessForTests();
});

const clientHeaders = {
  'X-Client-Token': 'temporary-client-token-for-backend-tests',
};

test('backend rejects visual access without the temporary client token', async () => {
  const response = await fetch(`${backendUrl}/api/visual/model-info`);
  const body = await response.json();

  assert.equal(response.status, 401);
  assert.equal(body.error.code, 'VISUAL_AUTH_REQUIRED');
  assert.equal(lastUpstreamRequest, undefined);
});

test('backend rejects an unchanged client-token placeholder', async () => {
  const activeToken = process.env.BACKEND_VISUAL_API_TOKEN;
  process.env.BACKEND_VISUAL_API_TOKEN = 'replace-with-a-temporary-random-client-token';
  try {
    const response = await fetch(`${backendUrl}/api/visual/model-info`, {
      headers: { 'X-Client-Token': process.env.BACKEND_VISUAL_API_TOKEN },
    });
    const body = await response.json();
    assert.equal(response.status, 503);
    assert.equal(body.error.code, 'VISUAL_AUTH_MISCONFIGURED');
  } finally {
    process.env.BACKEND_VISUAL_API_TOKEN = activeToken;
  }
});

test('backend rate-limits the controlled visual route', async () => {
  const activeMaximum = process.env.VISUAL_RATE_LIMIT_MAX;
  process.env.VISUAL_RATE_LIMIT_MAX = '1';
  resetVisualAccessForTests();
  try {
    const request = {
      method: 'POST',
      headers: { ...clientHeaders, 'content-type': 'application/json' },
      body: JSON.stringify({
        selected_crop: 'padi',
        land_type: 'sawah',
        water_availability: 'cukup',
        previous_crop: 'jagung',
        weather_summary: 'Cerah berawan',
        seed: 42,
      }),
    };
    const first = await fetch(`${backendUrl}/api/visual/generate`, request);
    const second = await fetch(`${backendUrl}/api/visual/generate`, request);
    const body = await second.json();
    assert.equal(first.status, 200);
    assert.equal(second.status, 429);
    assert.equal(body.error.code, 'VISUAL_RATE_LIMITED');
  } finally {
    process.env.VISUAL_RATE_LIMIT_MAX = activeMaximum;
    resetVisualAccessForTests();
  }
});

test('backend proxies readiness and model info with private token', async () => {
  const ready = await fetch(`${backendUrl}/api/visual/ready`, {
    headers: { ...clientHeaders, 'X-Request-ID': 'backend-ready-1' },
  });
  assert.equal(ready.status, 200);
  assert.equal((await ready.json()).device, 'cuda');
  assert.equal(lastUpstreamRequest.token, 'private-inference-token-for-test');
  assert.equal(lastUpstreamRequest.requestId, 'backend-ready-1');

  const modelInfo = await fetch(`${backendUrl}/api/visual/model-info`, { headers: clientHeaders });
  assert.equal(modelInfo.status, 200);
  assert.equal((await modelInfo.json()).provider, 'diffusers');
});

test('backend generation proxy preserves request and hides upstream image URL', async () => {
  const response = await fetch(`${backendUrl}/api/visual/generate`, {
    method: 'POST',
    headers: {
      ...clientHeaders,
      'content-type': 'application/json',
      'X-Request-ID': 'flutter-proxy-42',
    },
    body: JSON.stringify({
      selected_crop: 'padi',
      land_type: 'sawah',
      water_availability: 'cukup',
      previous_crop: 'jagung',
      weather_summary: 'Cerah berawan',
      seed: 42,
    }),
  });
  const body = await response.json();

  assert.equal(response.status, 200);
  assert.equal(body.request_id, 'flutter-proxy-42');
  assert.equal(lastUpstreamRequest.body.request_id, 'flutter-proxy-42');
  assert.equal(lastUpstreamRequest.body.crop, 'padi');
  assert.equal(lastUpstreamRequest.body.selected_crop, undefined);
  assert.equal(body.selected_crop, 'padi');
  assert.equal(body.metadata.selected_crop, 'padi');
  assert.equal(body.image_url, 'https://api.tani.test/api/visual/images/test.png');
  assert.equal(body.metadata.delivery_path, 'backend_proxy');
  assert.equal(body.metadata.upstream_image_url_exposed, false);
  assert.equal(body.image_url.includes(upstreamUrl), false);
});

test('backend preserves explicit seed and does not invent a missing seed', async () => {
  const explicit = await fetch(`${backendUrl}/api/visual/generate`, {
    method: 'POST',
    headers: { ...clientHeaders, 'content-type': 'application/json' },
    body: JSON.stringify({
      selected_crop: 'cabai',
      land_type: 'tegalan',
      water_availability: 'cukup',
      previous_crop: 'padi',
      weather_summary: 'Cerah',
      seed: 42,
    }),
  });
  assert.equal(explicit.status, 200);
  assert.equal(lastUpstreamRequest.body.seed, 42);

  const automatic = await fetch(`${backendUrl}/api/visual/generate`, {
    method: 'POST',
    headers: { ...clientHeaders, 'content-type': 'application/json' },
    body: JSON.stringify({
      selected_crop: 'cabai',
      land_type: 'tegalan',
      water_availability: 'cukup',
      previous_crop: 'padi',
      weather_summary: 'Cerah',
    }),
  });
  assert.equal(automatic.status, 200);
  assert.equal(Object.hasOwn(lastUpstreamRequest.body, 'seed'), false);
});

test('backend preserves the explicit selected crop for all four commodities', async () => {
  for (const crop of Object.keys(TRIGGER_TOKENS)) {
    const response = await fetch(`${backendUrl}/api/visual/generate`, {
      method: 'POST',
      headers: { ...clientHeaders, 'content-type': 'application/json' },
      body: JSON.stringify({
        selected_crop: crop,
        land_type: 'sawah',
        water_availability: 'cukup',
        previous_crop: 'padi',
        weather_summary: 'Cerah berawan',
        seed: 42,
      }),
    });
    const body = await response.json();

    assert.equal(response.status, 200);
    assert.equal(lastUpstreamRequest.body.crop, crop);
    assert.equal(lastUpstreamRequest.body.selected_crop, undefined);
    assert.equal(body.selected_crop, crop);
    assert.equal(body.metadata.crop, crop);
    assert.equal(body.metadata.trigger_token, TRIGGER_TOKENS[crop]);
  }
});

test('backend normalizes Kacang Tanah and rejects ambiguous crop input', async () => {
  const normalized = await fetch(`${backendUrl}/api/visual/generate`, {
    method: 'POST',
    headers: { ...clientHeaders, 'content-type': 'application/json' },
    body: JSON.stringify({
      selected_crop: 'Kacang Tanah',
      land_type: 'tegalan',
      water_availability: 'cukup',
      previous_crop: 'padi',
      weather_summary: 'Cerah',
    }),
  });
  assert.equal(normalized.status, 200);
  assert.equal((await normalized.json()).selected_crop, 'kacang_tanah');
  assert.equal(lastUpstreamRequest.body.crop, 'kacang_tanah');

  const conflict = await fetch(`${backendUrl}/api/visual/generate`, {
    method: 'POST',
    headers: { ...clientHeaders, 'content-type': 'application/json' },
    body: JSON.stringify({ selected_crop: 'cabai', crop: 'padi' }),
  });
  assert.equal(conflict.status, 422);
  assert.equal((await conflict.json()).error.code, 'SELECTED_CROP_CONFLICT');

  const array = await fetch(`${backendUrl}/api/visual/generate`, {
    method: 'POST',
    headers: { ...clientHeaders, 'content-type': 'application/json' },
    body: JSON.stringify({ selected_crop: ['padi', 'jagung'] }),
  });
  assert.equal(array.status, 422);
  assert.equal((await array.json()).error.code, 'INVALID_SELECTED_CROP');
});

test('backend serves generated PNG through the same public API', async () => {
  const response = await fetch(`${backendUrl}/api/visual/images/test.png`, { headers: clientHeaders });
  const image = Buffer.from(await response.arrayBuffer());

  assert.equal(response.status, 200);
  assert.equal(response.headers.get('content-type'), 'image/png');
  assert.deepEqual(image, PNG_1X1);

  const invalid = await fetch(`${backendUrl}/api/visual/images/not-an-image.jpg`, {
    headers: clientHeaders,
  });
  assert.equal(invalid.status, 400);
});

test('backend returns structured error when inference host is unavailable', async () => {
  const activeUrl = process.env.INFERENCE_API_BASE_URL;
  process.env.INFERENCE_API_BASE_URL = 'http://127.0.0.1:1';
  try {
    const response = await fetch(`${backendUrl}/api/visual/model-info`, {
      headers: { ...clientHeaders, 'X-Request-ID': 'unavailable-1' },
    });
    const body = await response.json();
    assert.equal(response.status, 503);
    assert.equal(body.request_id, 'unavailable-1');
    assert.equal(body.error.code, 'INFERENCE_UNAVAILABLE');
    assert.equal(body.error.retryable, true);
  } finally {
    process.env.INFERENCE_API_BASE_URL = activeUrl;
  }
});

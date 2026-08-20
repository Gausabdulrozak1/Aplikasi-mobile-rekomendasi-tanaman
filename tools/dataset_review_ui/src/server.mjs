import fs from "node:fs";
import fsp from "node:fs/promises";
import http from "node:http";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { ReviewUiError, ValidationError } from "./errors.mjs";
import { FinalizationManager } from "./finalizer.mjs";
import { buildReviewPaths, resolveRepoRoot } from "./paths.mjs";
import { ReviewStore } from "./review-store.mjs";

const STATIC_FILES = new Map([
  ["/", ["index.html", "text/html; charset=utf-8"]],
  ["/index.html", ["index.html", "text/html; charset=utf-8"]],
  ["/styles.css", ["styles.css", "text/css; charset=utf-8"]],
  ["/app.js", ["app.js", "text/javascript; charset=utf-8"]],
]);

const SECURITY_HEADERS = {
  "Content-Security-Policy":
    "default-src 'self'; img-src 'self'; style-src 'self'; script-src 'self'; " +
    "connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'",
  "Cross-Origin-Opener-Policy": "same-origin",
  "Referrer-Policy": "no-referrer",
  "X-Content-Type-Options": "nosniff",
  "X-Frame-Options": "DENY",
};

function jsonResponse(response, statusCode, value, extraHeaders = {}) {
  const body = `${JSON.stringify(value)}\n`;
  response.writeHead(statusCode, {
    ...SECURITY_HEADERS,
    "Cache-Control": "no-store",
    "Content-Type": "application/json; charset=utf-8",
    "Content-Length": Buffer.byteLength(body),
    ...extraHeaders,
  });
  response.end(body);
}

function errorResponse(response, error) {
  const known = error instanceof ReviewUiError;
  const statusCode = known ? error.statusCode : 500;
  jsonResponse(response, statusCode, {
    error: {
      code: known ? error.code : "INTERNAL_ERROR",
      message: known ? error.message : "Terjadi kesalahan internal pada review UI",
      ...(known && error.details !== undefined ? { details: error.details } : {}),
    },
  });
}

async function readJsonBody(request, limit = 64 * 1024) {
  const chunks = [];
  let size = 0;
  for await (const chunk of request) {
    size += chunk.length;
    if (size > limit) {
      throw new ReviewUiError("Request body terlalu besar", 413, "BODY_TOO_LARGE");
    }
    chunks.push(chunk);
  }
  if (!chunks.length) {
    return {};
  }
  try {
    return JSON.parse(Buffer.concat(chunks).toString("utf8"));
  } catch {
    throw new ValidationError("Request body bukan JSON valid", "INVALID_JSON");
  }
}

function assertLocalHost(request) {
  const host = String(request.headers.host || "").toLowerCase();
  const hostname = host.startsWith("[")
    ? host.slice(1, host.indexOf("]"))
    : host.split(":", 1)[0];
  if (!["127.0.0.1", "localhost", "::1"].includes(hostname)) {
    throw new ReviewUiError("Host tidak diizinkan", 403, "HOST_NOT_ALLOWED");
  }
}

function assertMutationHeader(request) {
  if (request.headers["x-review-ui"] !== "1") {
    throw new ReviewUiError(
      "Header keamanan review UI tidak tersedia",
      403,
      "MUTATION_HEADER_REQUIRED",
    );
  }
}

async function sendStatic(response, publicDirectory, route) {
  const [fileName, contentType] = STATIC_FILES.get(route);
  const filePath = path.join(publicDirectory, fileName);
  const body = await fsp.readFile(filePath);
  response.writeHead(200, {
    ...SECURITY_HEADERS,
    "Cache-Control": "no-cache",
    "Content-Type": contentType,
    "Content-Length": body.length,
  });
  response.end(body);
}

async function sendImage(response, imagePath) {
  const stat = await fsp.stat(imagePath);
  response.writeHead(200, {
    ...SECURITY_HEADERS,
    "Cache-Control": "private, max-age=300",
    "Content-Type": "image/jpeg",
    "Content-Length": stat.size,
  });
  await new Promise((resolve, reject) => {
    const stream = fs.createReadStream(imagePath);
    stream.on("error", reject);
    response.on("close", resolve);
    stream.on("end", resolve);
    stream.pipe(response);
  });
}

export function createReviewServer({ store, finalizer, paths }) {
  return http.createServer(async (request, response) => {
    try {
      assertLocalHost(request);
      const url = new URL(request.url || "/", "http://127.0.0.1");
      const route = url.pathname;

      if (request.method === "GET" && STATIC_FILES.has(route)) {
        await sendStatic(response, paths.publicDirectory, route);
        return;
      }
      if (request.method === "GET" && route === "/favicon.ico") {
        response.writeHead(204, SECURITY_HEADERS);
        response.end();
        return;
      }
      if (request.method === "GET" && route === "/api/health") {
        const progress = await store.getProgress();
        jsonResponse(response, 200, {
          status: "ok",
          service: "taniadaptif-dataset-review",
          total_candidates: progress.total_candidates,
        });
        return;
      }
      if (request.method === "GET" && route === "/api/state") {
        jsonResponse(response, 200, {
          ...(await store.getState()),
          finalization: finalizer.getStatus(),
        });
        return;
      }
      if (request.method === "GET" && route === "/api/validation") {
        jsonResponse(response, 200, await store.validate());
        return;
      }
      if (request.method === "GET" && route === "/api/finalization") {
        jsonResponse(response, 200, finalizer.getStatus());
        return;
      }
      if (request.method === "GET" && route === "/api/export") {
        const csv = await store.getCsvContent();
        response.writeHead(200, {
          ...SECURITY_HEADERS,
          "Cache-Control": "no-store",
          "Content-Type": "text/csv; charset=utf-8",
          "Content-Disposition": 'attachment; filename="manual_review_template.csv"',
          "Content-Length": Buffer.byteLength(csv),
        });
        response.end(csv);
        return;
      }
      if (request.method === "GET" && route.startsWith("/api/images/")) {
        const name = decodeURIComponent(route.slice("/api/images/".length));
        if (name !== path.basename(name)) {
          throw new ValidationError("Nama gambar tidak valid", "INVALID_IMAGE_NAME");
        }
        const imagePath = await store.getImagePath(name);
        if (!imagePath) {
          throw new ReviewUiError("Gambar tidak ditemukan", 404, "IMAGE_NOT_FOUND");
        }
        await sendImage(response, imagePath);
        return;
      }
      if (request.method === "PATCH" && route.startsWith("/api/reviews/")) {
        assertMutationHeader(request);
        const name = decodeURIComponent(route.slice("/api/reviews/".length));
        const result = await store.updateReview(name, await readJsonBody(request));
        jsonResponse(response, 200, result);
        return;
      }
      if (request.method === "POST" && route === "/api/finalize") {
        assertMutationHeader(request);
        await readJsonBody(request);
        jsonResponse(response, 202, await finalizer.start());
        return;
      }

      throw new ReviewUiError("Route tidak ditemukan", 404, "NOT_FOUND");
    } catch (error) {
      if (!response.headersSent) {
        errorResponse(response, error);
      } else {
        response.destroy();
      }
    }
  });
}

function parseArgument(name, fallback) {
  const prefix = `--${name}=`;
  const inline = process.argv.find((argument) => argument.startsWith(prefix));
  if (inline) {
    return inline.slice(prefix.length);
  }
  const index = process.argv.indexOf(`--${name}`);
  return index >= 0 ? process.argv[index + 1] : fallback;
}

export async function startReviewServer({
  repoRoot = resolveRepoRoot(parseArgument("repo-root", undefined)),
  host = parseArgument("host", "127.0.0.1"),
  port = Number(parseArgument("port", process.env.DATASET_REVIEW_PORT || 4173)),
} = {}) {
  if (host !== "127.0.0.1") {
    throw new Error("Dataset review UI hanya boleh bind ke 127.0.0.1");
  }
  if (!Number.isInteger(port) || port < 0 || port > 65535) {
    throw new Error("Port dataset review tidak valid");
  }
  const paths = buildReviewPaths(repoRoot);
  const store = new ReviewStore({ paths });
  const finalizer = new FinalizationManager({ paths, store });
  await store.initialize();
  await finalizer.initialize();
  const server = createReviewServer({ store, finalizer, paths });
  await new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(port, host, resolve);
  });
  const address = server.address();
  const actualPort = typeof address === "object" && address ? address.port : port;
  return { server, store, finalizer, url: `http://${host}:${actualPort}` };
}

const isDirectRun = process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url);
if (isDirectRun) {
  startReviewServer()
    .then(({ server, url }) => {
      console.log(`Dataset review UI: ${url}`);
      console.log("Tekan Ctrl+C untuk menghentikan server.");
      const stop = () => server.close(() => process.exit(0));
      process.once("SIGINT", stop);
      process.once("SIGTERM", stop);
    })
    .catch((error) => {
      console.error(`Gagal menjalankan dataset review UI: ${error.message}`);
      process.exitCode = 1;
    });
}

import fs from "node:fs";
import path from "node:path";

const root = process.cwd();
const ignoredParts = new Set([
  ".git",
  ".dart_tool",
  "build",
  "node_modules",
  "__pycache__",
  ".pytest_cache",
  ".venv",
  "venv",
]);
const ignoredRelativePrefixes = [
  "artifacts/dataset_build/kaggle_imagefolder_validation_env",
];
const allowedFalsePositiveFragments = [
  "hf_download",
  "hf_cache",
  "rg \"sk-|hf_|KAGGLE_KEY|password|api_key\"",
];
const patterns = [
  /sk-[A-Za-z0-9]{20,}/,
  /hf_[A-Za-z0-9]{20,}/,
  /KAGGLE_KEY\s*=/,
  /KAGGLE_USERNAME\s*=/,
  /password\s*=\s*["'][^"']+["']/i,
  /api[_-]?key\s*=\s*["'][^"']+["']/i,
];

function* walk(directory) {
  for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
    if (ignoredParts.has(entry.name) || /^\.venv(?:[-_].+)?$/.test(entry.name)) continue;
    const fullPath = path.join(directory, entry.name);
    const relative = path.relative(root, fullPath).replaceAll("\\", "/");
    if (ignoredRelativePrefixes.some((prefix) => relative === prefix || relative.startsWith(`${prefix}/`))) {
      continue;
    }
    if (entry.isDirectory()) {
      yield* walk(fullPath);
    } else {
      yield fullPath;
    }
  }
}

let failed = false;

for (const filePath of walk(root)) {
  const relative = path.relative(root, filePath);
  const extension = path.extname(filePath).toLowerCase();
  if (
    [
      ".png",
      ".jpg",
      ".jpeg",
      ".ico",
      ".drawio",
      ".apk",
      ".zip",
      ".pyc",
      ".safetensors",
      ".bin",
      ".pt",
    ].includes(extension)
  ) {
    continue;
  }

  let text;
  try {
    text = fs.readFileSync(filePath, "utf8");
  } catch {
    continue;
  }

  for (const pattern of patterns) {
    const match = text.match(pattern);
    if (!match) continue;
    const line = text.slice(0, match.index).split(/\r?\n/).length;
    const fragment = text
      .split(/\r?\n/)
      [line - 1]?.trim() ?? "";
    if (allowedFalsePositiveFragments.some((allowed) => fragment.includes(allowed))) {
      continue;
    }
    console.error(`${relative}:${line}: possible secret matched ${pattern}`);
    failed = true;
  }
}

if (failed) {
  process.exit(1);
}

console.log("No obvious secrets found.");

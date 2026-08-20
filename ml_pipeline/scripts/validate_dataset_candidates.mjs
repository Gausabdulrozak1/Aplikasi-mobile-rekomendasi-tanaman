import fs from "node:fs";

const path = "ml_pipeline/configs/dataset_candidates.json";
const raw = fs.readFileSync(path, "utf8");
const registry = JSON.parse(raw);

let failed = false;

function fail(message) {
  console.error(`${path}: ${message}`);
  failed = true;
}

if (!/^\d{4}-\d{2}-\d{2}$/.test(registry.access_date ?? "")) {
  fail("access_date must use YYYY-MM-DD");
}

if (!Array.isArray(registry.required_commodities) || registry.required_commodities.length === 0) {
  fail("required_commodities must be a non-empty array");
}

if (!Array.isArray(registry.candidates) || registry.candidates.length === 0) {
  fail("candidates must be a non-empty array");
}

const coveredCommodities = new Set();
const ids = new Set();
const allowedLicenseStatuses = new Set([
  "verified_on_source_page",
  "verified_from_search_result",
  "needs_verification",
]);

for (const [index, candidate] of (registry.candidates ?? []).entries()) {
  const prefix = `candidate[${index}]`;
  for (const field of ["id", "platform", "source_url", "access", "fit", "visual_scope", "caveats"]) {
    if (!candidate[field] || typeof candidate[field] !== "string") {
      fail(`${prefix}.${field} must be a non-empty string`);
    }
  }

  if (candidate.id && ids.has(candidate.id)) {
    fail(`${prefix}.id is duplicated: ${candidate.id}`);
  }
  ids.add(candidate.id);

  if (candidate.source_url && !candidate.source_url.startsWith("https://")) {
    fail(`${prefix}.source_url must start with https://`);
  }

  if (!Array.isArray(candidate.commodities) || candidate.commodities.length === 0) {
    fail(`${prefix}.commodities must be a non-empty array`);
  } else {
    for (const commodity of candidate.commodities) {
      coveredCommodities.add(commodity);
    }
  }

  const license = candidate.license ?? {};
  if (!license.name || typeof license.name !== "string") {
    fail(`${prefix}.license.name must be a non-empty string`);
  }
  if (!allowedLicenseStatuses.has(license.status)) {
    fail(`${prefix}.license.status must be one of ${Array.from(allowedLicenseStatuses).join(", ")}`);
  }
  if (license.status === "needs_verification" && license.name !== "needs verification") {
    fail(`${prefix}.license.name must be "needs verification" when status is needs_verification`);
  }
}

for (const commodity of registry.required_commodities ?? []) {
  if (!coveredCommodities.has(commodity)) {
    fail(`required commodity has no candidate coverage: ${commodity}`);
  }
}

if (failed) {
  process.exit(1);
}

console.log(`${path}: ok (${registry.candidates.length} candidates)`);

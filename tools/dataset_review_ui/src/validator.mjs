import fs from "node:fs";

import { hasRecordedRejectionReason } from "./review-notes.mjs";

export const VALID_CLASS_IDS = Object.freeze([
  "padi",
  "jagung",
  "cabai",
  "kacang_tanah",
]);
export const VALID_SOURCE_TYPES = Object.freeze(["public", "local_aikmel"]);
export const VALID_ACCEPTED_VALUES = Object.freeze(["", "yes", "no", "unsure"]);
export const ORIGINAL_REVIEW_BATCH = "original_350";

const CLASS_SET = new Set(VALID_CLASS_IDS);
const SOURCE_SET = new Set(VALID_SOURCE_TYPES);
const ACCEPTED_SET = new Set(VALID_ACCEPTED_VALUES);
const PUBLIC_ONLY_CLASSES = new Set(["jagung", "cabai", "kacang_tanah"]);

function clean(value) {
  return String(value ?? "").trim();
}

function decision(value) {
  return clean(value).toLowerCase();
}

function reviewBatch(row) {
  return clean(row.review_batch) || ORIGINAL_REVIEW_BATCH;
}

function isValidReviewBatch(value) {
  return value === ORIGINAL_REVIEW_BATCH || /^additional_batch_v[1-9][0-9]*$/.test(value);
}

function issue(code, message, file = undefined) {
  return { code, message, ...(file ? { curated_file_name: file } : {}) };
}

function emptyDecisionCounts() {
  return { total: 0, reviewed: 0, accepted_yes: 0, accepted_no: 0, accepted_unsure: 0, pending: 0 };
}

function addDecisionCount(target, accepted) {
  target.total += 1;
  if (accepted === "yes") {
    target.reviewed += 1;
    target.accepted_yes += 1;
  } else if (accepted === "no") {
    target.reviewed += 1;
    target.accepted_no += 1;
  } else if (accepted === "unsure") {
    target.reviewed += 1;
    target.accepted_unsure += 1;
  } else {
    target.pending += 1;
  }
}

export function summarizeReview(rows) {
  const totals = emptyDecisionCounts();
  const countsPerClass = Object.fromEntries(
    VALID_CLASS_IDS.map((classId) => [classId, emptyDecisionCounts()]),
  );
  const countsPerSource = Object.fromEntries(
    VALID_SOURCE_TYPES.map((sourceType) => [sourceType, emptyDecisionCounts()]),
  );
  const countsPerBatch = {};

  for (const row of rows) {
    const accepted = decision(row.accepted);
    addDecisionCount(totals, accepted);
    const classId = clean(row.class_id);
    const sourceType = clean(row.source_type);
    const batch = reviewBatch(row);
    if (!countsPerClass[classId]) {
      countsPerClass[classId] = emptyDecisionCounts();
    }
    if (!countsPerSource[sourceType]) {
      countsPerSource[sourceType] = emptyDecisionCounts();
    }
    if (!countsPerBatch[batch]) {
      countsPerBatch[batch] = emptyDecisionCounts();
    }
    addDecisionCount(countsPerClass[classId], accepted);
    addDecisionCount(countsPerSource[sourceType], accepted);
    addDecisionCount(countsPerBatch[batch], accepted);
  }

  return {
    total_candidates: totals.total,
    reviewed: totals.reviewed,
    accepted_yes: totals.accepted_yes,
    accepted_no: totals.accepted_no,
    accepted_unsure: totals.accepted_unsure,
    pending: totals.pending,
    counts_per_class: countsPerClass,
    counts_per_source: countsPerSource,
    counts_per_batch: countsPerBatch,
  };
}

export function validateReviewDataset({
  rows,
  expectedRows,
  imagePaths,
  requiredTotal = null,
}) {
  const errors = [];
  const warnings = [];
  const expectedByName = new Map();
  for (const row of expectedRows) {
    const name = clean(row.curated_file_name || row.new_file_name);
    if (!name) {
      errors.push(issue("EXPECTED_NAME_MISSING", "Curation mapping contains an empty name"));
    } else if (expectedByName.has(name)) {
      errors.push(issue("EXPECTED_NAME_DUPLICATE", "Curation mapping contains duplicate names", name));
    } else {
      expectedByName.set(name, row);
    }
  }

  const effectiveTotal = requiredTotal ?? expectedRows.length;
  if (requiredTotal !== null && expectedRows.length !== requiredTotal) {
    errors.push(
      issue(
        "EXPECTED_TOTAL_MISMATCH",
        `Curation mapping has ${expectedRows.length} candidates; expected ${requiredTotal}`,
      ),
    );
  }
  if (rows.length !== expectedRows.length) {
    errors.push(
      issue(
        "TEMPLATE_ROW_COUNT_MISMATCH",
        `Review CSV has ${rows.length} rows; expected ${expectedRows.length}`,
      ),
    );
  }

  const seen = new Set();
  for (const row of rows) {
    const name = clean(row.curated_file_name);
    if (!name) {
      errors.push(issue("CURATED_NAME_MISSING", "Review row has no curated_file_name"));
      continue;
    }
    if (seen.has(name)) {
      errors.push(issue("CURATED_NAME_DUPLICATE", "Duplicate curated_file_name", name));
      continue;
    }
    seen.add(name);

    const expected = expectedByName.get(name);
    if (!expected) {
      errors.push(issue("UNEXPECTED_CANDIDATE", "Candidate is not present in curation mapping", name));
      continue;
    }

    for (const field of [
      "original_file_name",
      "class_id",
      "source_type",
      "sha256",
      "review_batch",
    ]) {
      if (field === "review_batch" && !clean(row[field]) && !clean(expected[field])) {
        continue;
      }
      if (clean(row[field]) !== clean(expected[field])) {
        errors.push(issue("IDENTITY_MISMATCH", `Identity field '${field}' differs from mapping`, name));
      }
    }

    const classId = clean(row.class_id);
    const sourceType = clean(row.source_type);
    const batch = reviewBatch(row);
    const accepted = decision(row.accepted);
    if (!CLASS_SET.has(classId)) {
      errors.push(issue("INVALID_CLASS", `Unsupported class_id '${classId}'`, name));
    }
    if (!SOURCE_SET.has(sourceType)) {
      errors.push(issue("INVALID_SOURCE", `Unsupported source_type '${sourceType}'`, name));
    }
    if (sourceType === "local_aikmel" && classId !== "padi") {
      errors.push(issue("INVALID_LOCAL_SOURCE", `${classId} cannot use local_aikmel`, name));
    }
    if (PUBLIC_ONLY_CLASSES.has(classId) && sourceType !== "public") {
      errors.push(issue("PUBLIC_ONLY_SOURCE_VIOLATION", `${classId} must be public`, name));
    }
    if (!ACCEPTED_SET.has(accepted)) {
      errors.push(issue("INVALID_ACCEPTED", `Unsupported accepted value '${accepted}'`, name));
    }
    if (!isValidReviewBatch(batch)) {
      errors.push(issue("INVALID_REVIEW_BATCH", `Unsupported review_batch '${batch}'`, name));
    }
    if (accepted === "no" && !hasRecordedRejectionReason(row)) {
      warnings.push(issue("REJECTION_REASON_MISSING", "Rejected image has no recorded reason", name));
    }
    if (clean(expected.technical_status).toLowerCase() !== "valid") {
      errors.push(issue("TECHNICAL_STATUS_INVALID", "Candidate is not technically valid", name));
    }

    const imagePath = imagePaths.get(name);
    if (!imagePath || !fs.existsSync(imagePath) || !fs.statSync(imagePath).isFile()) {
      errors.push(issue("IMAGE_PATH_MISSING", "Candidate image is unavailable", name));
    }
  }

  for (const name of expectedByName.keys()) {
    if (!seen.has(name)) {
      errors.push(issue("CANDIDATE_MISSING", "Expected candidate is missing from review CSV", name));
    }
  }

  const counts = summarizeReview(rows);
  const mappingUsesBatches = expectedRows.some((row) => clean(row.review_batch));
  if (
    mappingUsesBatches &&
    (counts.counts_per_batch[ORIGINAL_REVIEW_BATCH]?.total || 0) !== 350
  ) {
    errors.push(
      issue(
        "ORIGINAL_BATCH_TOTAL_MISMATCH",
        `Original review batch has ${counts.counts_per_batch[ORIGINAL_REVIEW_BATCH]?.total || 0} candidates; expected 350`,
      ),
    );
  }
  const canFinalize =
    errors.length === 0 &&
    counts.total_candidates === effectiveTotal &&
    counts.pending === 0 &&
    counts.accepted_unsure === 0 &&
    counts.accepted_yes + counts.accepted_no === effectiveTotal;
  return {
    valid: errors.length === 0,
    can_finalize: canFinalize,
    errors,
    warnings,
    required_total: effectiveTotal,
    ...counts,
  };
}

export function buildProgress(validation, {
  lastReviewedFile = null,
  updatedAt = new Date().toISOString(),
  reviewStatus = undefined,
} = {}) {
  const derivedStatus = validation.can_finalize ? "ready_to_finalize" : "in_progress";
  return {
    total_candidates: validation.total_candidates,
    reviewed: validation.reviewed,
    accepted_yes: validation.accepted_yes,
    accepted_no: validation.accepted_no,
    accepted_unsure: validation.accepted_unsure,
    pending: validation.pending,
    last_reviewed_file: lastReviewedFile,
    updated_at: updatedAt,
    review_status: reviewStatus || derivedStatus,
    counts_per_class: validation.counts_per_class,
    counts_per_source: validation.counts_per_source,
    counts_per_batch: validation.counts_per_batch,
  };
}

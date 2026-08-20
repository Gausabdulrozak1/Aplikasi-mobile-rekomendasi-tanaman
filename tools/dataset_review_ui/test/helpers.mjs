import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";

import { serializeCsv } from "../src/csv.mjs";
import { buildReviewPaths } from "../src/paths.mjs";

export const REVIEW_HEADERS = [
  "curated_file_name",
  "original_file_name",
  "original_path",
  "class_id",
  "source_type",
  "is_local_aikmel",
  "width",
  "height",
  "sha256",
  "duplicate_group",
  "duplicate_warning",
  "crop_correct",
  "shows_plant",
  "shows_whole_plant_or_multiple_plants",
  "shows_field_or_growing_environment",
  "too_close_up",
  "harvested_product_only",
  "food_or_market_image",
  "watermark_present",
  "blurred",
  "severe_occlusion",
  "near_duplicate_excessive",
  "ai_generated_suspected",
  "accepted",
  "reviewer_notes",
];

const MAPPING_HEADERS = [
  "curated_file_name",
  "new_file_name",
  "curated_path",
  "original_file_name",
  "original_path",
  "class_id",
  "source_type",
  "is_local_aikmel",
  "width",
  "height",
  "sha256",
  "duplicate_group",
  "duplicate_warning",
  "technical_status",
  "manual_review_status",
  "validation_status",
  "final_status",
  "rejection_reason",
  "reviewer_notes",
];

const SEMANTIC_HEADERS = [
  "curated_file_name",
  "screening_status",
  "semantic_class_confidence",
  "proxy_flags",
  "plant_visible_proxy",
  "growing_environment_proxy",
  "too_close_up_proxy",
  "blur_proxy",
  "watermark_proxy",
  "method",
];

const INVENTORY_HEADERS = [
  "original_path",
  "sha256",
  "file_size",
  "width",
  "height",
  "technical_status",
];

async function writeCsv(filePath, headers, rows) {
  await fs.mkdir(path.dirname(filePath), { recursive: true });
  await fs.writeFile(filePath, serializeCsv(headers, rows), "utf8");
}

export async function createReviewFixture({ decisions = ["", ""] } = {}) {
  const root = await fs.mkdtemp(path.join(os.tmpdir(), "taniadaptif-review-"));
  const paths = buildReviewPaths(root);
  await fs.mkdir(paths.publicDirectory, { recursive: true });

  const definitions = [
    { name: "padi_0001.jpg", classId: "padi", sourceType: "local_aikmel" },
    { name: "jagung_0001.jpg", classId: "jagung", sourceType: "public" },
  ];
  const reviewRows = [];
  const mappingRows = [];
  const semanticRows = [];
  const inventoryRows = [];

  for (const [index, item] of definitions.entries()) {
    const originalPath = path.join(root, "raw", item.classId, `original_${index + 1}.jpg`);
    const candidatePath = path.join(paths.candidatesDirectory, item.classId, item.name);
    const sha256 = String(index + 1).repeat(64);
    await fs.mkdir(path.dirname(candidatePath), { recursive: true });
    await fs.writeFile(candidatePath, `fixture-image-${index + 1}`);
    reviewRows.push({
      curated_file_name: item.name,
      original_file_name: path.basename(originalPath),
      original_path: originalPath,
      class_id: item.classId,
      source_type: item.sourceType,
      is_local_aikmel: String(item.sourceType === "local_aikmel"),
      width: "640",
      height: "512",
      sha256,
      duplicate_group: `image-${index + 1}`,
      duplicate_warning: "",
      accepted: decisions[index] || "",
      reviewer_notes: "",
    });
    mappingRows.push({
      ...reviewRows.at(-1),
      new_file_name: item.name,
      curated_path: candidatePath,
      technical_status: "valid",
      manual_review_status: "pending",
      validation_status: "technical_valid_pending_manual_review",
      final_status: "pending_manual_review",
      rejection_reason: "",
    });
    semanticRows.push({
      curated_file_name: item.name,
      screening_status: index ? "proxy_review" : "proxy_pass",
      semantic_class_confidence: "",
      proxy_flags: index ? "vegetation_not_detected" : "",
      method: "fixture proxy",
    });
    inventoryRows.push({
      original_path: originalPath,
      sha256,
      file_size: String(1000 + index),
      width: "640",
      height: "512",
      technical_status: "valid",
    });
  }

  await writeCsv(paths.manualReviewCsv, REVIEW_HEADERS, reviewRows);
  await writeCsv(paths.mappingCsv, MAPPING_HEADERS, mappingRows);
  await writeCsv(paths.semanticCsv, SEMANTIC_HEADERS, semanticRows);
  await writeCsv(paths.inventoryCsv, INVENTORY_HEADERS, inventoryRows);
  await writeCsv(paths.exactDuplicatesCsv, [
    "sha256",
    "canonical_path",
    "duplicate_path",
  ], []);
  await writeCsv(paths.nearDuplicatesCsv, [
    "left_path",
    "right_path",
    "distance",
    "threshold",
  ], []);
  await writeCsv(paths.crossClassDuplicatesCsv, [
    "duplicate_type",
    "left_path",
    "right_path",
  ], []);
  return {
    root,
    paths,
    cleanup: () => fs.rm(root, { recursive: true, force: true }),
  };
}

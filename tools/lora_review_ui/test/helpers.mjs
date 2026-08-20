import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";

import { serializeCsv } from "../../dataset_review_ui/src/csv.mjs";
import { buildLoraReviewPaths } from "../src/paths.mjs";
import { REVIEW_HEADERS } from "../src/store.mjs";

const PNG_1X1 = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=",
  "base64",
);

export async function createLoraReviewFixture() {
  const root = await fs.mkdtemp(path.join(os.tmpdir(), "taniadaptif-lora-review-"));
  const paths = buildLoraReviewPaths(root, "fixture1234");
  await fs.mkdir(paths.runDirectory, { recursive: true });
  const rows = [];
  for (const variant of ["base", "lora"]) {
    const relativeImage = `generated/evaluation/${variant}/padi_p1_s42_${variant}.png`;
    const imagePath = path.join(paths.runDirectory, relativeImage);
    await fs.mkdir(path.dirname(imagePath), { recursive: true });
    await fs.writeFile(imagePath, PNG_1X1);
    rows.push({
      condition_id: "padi_p1_s42",
      variant,
      class_id: "padi",
      prompt: "a realistic agricultural photograph of rice plants",
      seed: "42",
      expected_image_path: relativeImage,
      crop_correct: "",
      field_context_quality: "",
      visual_realism_score: "",
      class_confusion: "",
      reviewer_role: "",
      reviewer_notes: "",
    });
  }
  await fs.writeFile(paths.reviewCsv, serializeCsv(REVIEW_HEADERS, rows), "utf8");
  return {
    root,
    paths,
    cleanup: () => fs.rm(root, { recursive: true, force: true }),
  };
}

export function completeAssessment(overrides = {}) {
  return {
    crop_correct: true,
    field_context_quality: 4,
    visual_realism_score: 4,
    class_confusion: "none",
    reviewer_role: "peneliti",
    reviewer_notes: "",
    ...overrides,
  };
}

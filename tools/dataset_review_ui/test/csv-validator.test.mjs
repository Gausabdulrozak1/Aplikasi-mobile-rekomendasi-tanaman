import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

import { parseCsv, serializeCsv } from "../src/csv.mjs";
import { summarizeReview, validateReviewDataset } from "../src/validator.mjs";
import { createReviewFixture } from "./helpers.mjs";

test("CSV parser and serializer preserve commas, quotes, and line breaks", () => {
  const headers = ["name", "notes"];
  const rows = [{ name: "padi, satu", notes: 'baris "satu"\nbaris dua' }];
  assert.deepEqual(parseCsv(serializeCsv(headers, rows)), { headers, rows });
});

test("validator accepts pending structure but blocks pending and unsure finalization", async (t) => {
  const fixture = await createReviewFixture({ decisions: ["unsure", ""] });
  t.after(fixture.cleanup);
  const { readCsvFile } = await import("../src/csv.mjs");
  const manual = await readCsvFile(fixture.paths.manualReviewCsv);
  const mapping = await readCsvFile(fixture.paths.mappingCsv);
  const imagePaths = new Map(
    mapping.rows.map((row) => [row.curated_file_name, row.curated_path]),
  );
  const result = validateReviewDataset({
    rows: manual.rows,
    expectedRows: mapping.rows,
    imagePaths,
    requiredTotal: 2,
  });
  assert.equal(result.valid, true);
  assert.equal(result.can_finalize, false);
  assert.equal(result.accepted_unsure, 1);
  assert.equal(result.pending, 1);
});

test("validator rejects a local source for a public-only class", async (t) => {
  const fixture = await createReviewFixture();
  t.after(fixture.cleanup);
  const { readCsvFile } = await import("../src/csv.mjs");
  const manual = await readCsvFile(fixture.paths.manualReviewCsv);
  const mapping = await readCsvFile(fixture.paths.mappingCsv);
  manual.rows[1].source_type = "local_aikmel";
  mapping.rows[1].source_type = "local_aikmel";
  const imagePaths = new Map(
    mapping.rows.map((row) => [row.curated_file_name, row.curated_path]),
  );
  const result = validateReviewDataset({
    rows: manual.rows,
    expectedRows: mapping.rows,
    imagePaths,
    requiredTotal: 2,
  });
  assert.equal(result.valid, false);
  assert.ok(result.errors.some((error) => error.code === "PUBLIC_ONLY_SOURCE_VIOLATION"));
  assert.ok(fs.existsSync(imagePaths.get("jagung_0001.jpg")));
});

test("review summary preserves original and additional batch progress", () => {
  const result = summarizeReview([
    {
      class_id: "jagung",
      source_type: "public",
      review_batch: "original_350",
      accepted: "yes",
    },
    {
      class_id: "jagung",
      source_type: "public",
      review_batch: "additional_batch_v1",
      accepted: "",
    },
    {
      class_id: "cabai",
      source_type: "public",
      review_batch: "additional_batch_v1",
      accepted: "no",
    },
  ]);

  assert.deepEqual(result.counts_per_batch.original_350, {
    total: 1,
    reviewed: 1,
    accepted_yes: 1,
    accepted_no: 0,
    accepted_unsure: 0,
    pending: 0,
  });
  assert.deepEqual(result.counts_per_batch.additional_batch_v1, {
    total: 2,
    reviewed: 1,
    accepted_yes: 0,
    accepted_no: 1,
    accepted_unsure: 0,
    pending: 1,
  });
});

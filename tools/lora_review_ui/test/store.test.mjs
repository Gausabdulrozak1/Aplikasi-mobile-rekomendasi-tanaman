import assert from "node:assert/strict";
import fs from "node:fs/promises";
import test from "node:test";

import { parseCsv } from "../../dataset_review_ui/src/csv.mjs";
import { LoraReviewStore } from "../src/store.mjs";
import { completeAssessment, createLoraReviewFixture } from "./helpers.mjs";

test("blank LoRA review initializes as valid pending evidence", async (t) => {
  const fixture = await createLoraReviewFixture();
  t.after(fixture.cleanup);
  const store = new LoraReviewStore({ paths: fixture.paths, expectedRows: 2 });

  await store.initialize();
  const state = await store.getState();

  assert.equal(state.validation.valid, true);
  assert.equal(state.validation.complete, false);
  assert.equal(state.validation.completed_rows, 0);
  assert.equal(state.validation.valid_image_rows, 2);
  assert.equal(state.conditions.length, 1);
  assert.equal(state.conditions[0].complete, false);
});

test("review updates are validated, backed up, and written atomically", async (t) => {
  const fixture = await createLoraReviewFixture();
  t.after(fixture.cleanup);
  const store = new LoraReviewStore({ paths: fixture.paths, expectedRows: 2 });
  await store.initialize();

  await assert.rejects(
    store.updateReview("padi_p1_s42", "base", completeAssessment({ visual_realism_score: 6 })),
    (error) => error.code === "INVALID_SCORE",
  );
  const saved = await store.updateReview(
    "padi_p1_s42",
    "base",
    completeAssessment({ reviewer_notes: "base reviewed" }),
  );
  const parsed = parseCsv(await fs.readFile(fixture.paths.reviewCsv, "utf8"));
  const backups = await fs.readdir(fixture.paths.backupsDirectory);

  assert.equal(saved.row.assessment.complete, true);
  assert.equal(saved.validation.completed_rows, 1);
  assert.equal(parsed.rows[0].reviewer_notes, "base reviewed");
  assert.equal(backups.length, 1);
});

test("complete pair can be finalized into human-only summary", async (t) => {
  const fixture = await createLoraReviewFixture();
  t.after(fixture.cleanup);
  const store = new LoraReviewStore({ paths: fixture.paths, expectedRows: 2 });
  await store.initialize();
  await store.updateReview("padi_p1_s42", "base", completeAssessment());
  await store.updateReview(
    "padi_p1_s42",
    "lora",
    completeAssessment({ crop_correct: false, class_confusion: "unclear" }),
  );

  const report = await store.finalize();
  const persisted = JSON.parse(await fs.readFile(fixture.paths.completionJson, "utf8"));

  assert.equal(report.status, "complete");
  assert.equal(report.validation.completed_rows, 2);
  assert.equal(persisted.human_review_source, "reviewer_entered_local_ui");
  assert.equal(persisted.automated_scores_inserted, false);
  assert.deepEqual(persisted.reviewer_roles, ["peneliti"]);
  assert.equal(report.summary.find((row) => row.variant === "lora").crop_correct_percent, 0);
  assert.equal(report.summary.find((row) => row.variant === "lora").confusion_count, 1);
  assert.match(await fs.readFile(fixture.paths.completionMarkdown, "utf8"), /Human LoRA Review/);
});

test("finalization rejects incomplete review", async (t) => {
  const fixture = await createLoraReviewFixture();
  t.after(fixture.cleanup);
  const store = new LoraReviewStore({ paths: fixture.paths, expectedRows: 2 });
  await store.initialize();

  await assert.rejects(store.finalize(), (error) => error.code === "HUMAN_REVIEW_INCOMPLETE");
});

test("editing a finalized review invalidates stale completion artifacts", async (t) => {
  const fixture = await createLoraReviewFixture();
  t.after(fixture.cleanup);
  const store = new LoraReviewStore({ paths: fixture.paths, expectedRows: 2 });
  await store.initialize();
  await store.updateReview("padi_p1_s42", "base", completeAssessment());
  await store.updateReview("padi_p1_s42", "lora", completeAssessment());
  await store.finalize();
  await fs.writeFile(fixture.paths.analysisJson, "stale analysis\n", "utf8");
  await fs.writeFile(fixture.paths.analysisCsv, "stale analysis\n", "utf8");
  await fs.writeFile(fixture.paths.analysisMarkdown, "stale analysis\n", "utf8");

  await store.clearReview("padi_p1_s42", "base");

  await assert.rejects(fs.access(fixture.paths.completionJson));
  await assert.rejects(fs.access(fixture.paths.completionMarkdown));
  await assert.rejects(fs.access(fixture.paths.analysisJson));
  await assert.rejects(fs.access(fixture.paths.analysisCsv));
  await assert.rejects(fs.access(fixture.paths.analysisMarkdown));
  assert.equal((await store.validate()).complete, false);
});

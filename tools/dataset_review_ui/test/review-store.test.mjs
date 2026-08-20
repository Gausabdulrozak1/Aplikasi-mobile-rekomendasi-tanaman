import assert from "node:assert/strict";
import fs from "node:fs/promises";
import test from "node:test";

import { readCsvFile } from "../src/csv.mjs";
import { ReviewStore } from "../src/review-store.mjs";
import { createReviewFixture } from "./helpers.mjs";

test("review store reads metadata and uses source labels safely", async (t) => {
  const fixture = await createReviewFixture();
  t.after(fixture.cleanup);
  const store = new ReviewStore({ paths: fixture.paths, requiredTotal: 2 });
  const state = await store.initialize();
  assert.equal(state.candidates.length, 2);
  assert.equal(state.candidates[0].source_label, "LOCAL AIKMEL");
  assert.equal(state.candidates[1].source_label, "PUBLIC");
  assert.equal(state.candidates[1].semantic.screening_status, "proxy_review");
  assert.equal(state.candidates[0].file_size, 1000);
});

test("autosave is atomic, creates one initial backup, and resumes progress", async (t) => {
  const fixture = await createReviewFixture();
  t.after(fixture.cleanup);
  const store = new ReviewStore({ paths: fixture.paths, requiredTotal: 2 });
  await store.initialize();
  await store.updateReview("padi_0001.jpg", {
    accepted: "yes",
    note: "tanaman terlihat jelas",
    rejection_reasons: [],
  });
  await store.updateReview("jagung_0001.jpg", {
    accepted: "no",
    note: "",
    rejection_reasons: ["wrong_crop", "unrelated_image"],
  });

  const backups = await fs.readdir(fixture.paths.backupsDirectory);
  assert.equal(backups.length, 1);
  const saved = await readCsvFile(fixture.paths.manualReviewCsv);
  assert.equal(saved.rows[0].accepted, "yes");
  assert.equal(saved.rows[1].accepted, "no");
  assert.match(saved.rows[1].reviewer_notes, /wrong_crop/);
  assert.equal((await fs.readdir(fixture.paths.reviewDirectory)).some((name) => name.endsWith(".tmp")), false);

  const resumedStore = new ReviewStore({ paths: fixture.paths, requiredTotal: 2 });
  const resumed = await resumedStore.initialize();
  assert.equal(resumed.progress.last_reviewed_file, "jagung_0001.jpg");
  assert.equal(resumed.progress.accepted_yes, 1);
  assert.equal(resumed.progress.accepted_no, 1);
  assert.equal(resumed.validation.can_finalize, true);
});

test("unsure is saved but keeps the finalization gate closed", async (t) => {
  const fixture = await createReviewFixture({ decisions: ["yes", ""] });
  t.after(fixture.cleanup);
  const store = new ReviewStore({ paths: fixture.paths, requiredTotal: 2 });
  await store.initialize();
  const result = await store.updateReview("jagung_0001.jpg", {
    accepted: "unsure",
    note: "perlu dilihat ulang",
    rejection_reasons: [],
  });
  assert.equal(result.progress.accepted_unsure, 1);
  assert.equal(result.validation.can_finalize, false);
});

test("completed review status survives server resume", async (t) => {
  const fixture = await createReviewFixture({ decisions: ["yes", "yes"] });
  t.after(fixture.cleanup);
  const store = new ReviewStore({ paths: fixture.paths, requiredTotal: 2 });
  await store.initialize();
  const completed = await store.markReviewComplete();
  assert.equal(completed.review_status, "complete");

  const resumedStore = new ReviewStore({ paths: fixture.paths, requiredTotal: 2 });
  const resumed = await resumedStore.initialize();
  assert.equal(resumed.progress.review_status, "complete");
  assert.equal((await resumedStore.getProgress()).review_status, "complete");
});

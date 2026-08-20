import assert from "node:assert/strict";
import test from "node:test";

import { createLoraReviewServer } from "../src/server.mjs";
import { LoraReviewStore } from "../src/store.mjs";
import { completeAssessment, createLoraReviewFixture } from "./helpers.mjs";

async function listen(server) {
  await new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(0, "127.0.0.1", resolve);
  });
  return `http://127.0.0.1:${server.address().port}`;
}

test("LoRA review HTTP service serves pairs and protects mutations", async (t) => {
  const fixture = await createLoraReviewFixture();
  t.after(fixture.cleanup);
  const store = new LoraReviewStore({ paths: fixture.paths, expectedRows: 2 });
  await store.initialize();
  const server = createLoraReviewServer({ store, paths: fixture.paths });
  t.after(() => new Promise((resolve) => server.close(resolve)));
  const baseUrl = await listen(server);

  const pageResponse = await fetch(baseUrl);
  const page = await pageResponse.text();
  assert.equal(pageResponse.status, 200);
  assert.match(page, /Review Visual LoRA/);

  const stateResponse = await fetch(`${baseUrl}/api/state`);
  const state = await stateResponse.json();
  assert.equal(stateResponse.status, 200);
  assert.equal(state.conditions.length, 1);
  assert.equal(state.validation.completed_rows, 0);

  const imageResponse = await fetch(
    `${baseUrl}/api/images/base/padi_p1_s42_base.png`,
  );
  assert.equal(imageResponse.status, 200);
  assert.equal(imageResponse.headers.get("content-type"), "image/png");

  const blocked = await fetch(`${baseUrl}/api/reviews/padi_p1_s42/base`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(completeAssessment()),
  });
  assert.equal(blocked.status, 403);

  const saved = await fetch(`${baseUrl}/api/reviews/padi_p1_s42/base`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", "X-Review-UI": "1" },
    body: JSON.stringify(completeAssessment()),
  });
  assert.equal(saved.status, 200);
  assert.equal((await saved.json()).row.assessment.complete, true);
});

test("LoRA review HTTP finalization remains blocked while rows are pending", async (t) => {
  const fixture = await createLoraReviewFixture();
  t.after(fixture.cleanup);
  const store = new LoraReviewStore({ paths: fixture.paths, expectedRows: 2 });
  await store.initialize();
  const server = createLoraReviewServer({ store, paths: fixture.paths });
  t.after(() => new Promise((resolve) => server.close(resolve)));
  const baseUrl = await listen(server);

  const response = await fetch(`${baseUrl}/api/finalize`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Review-UI": "1" },
    body: "{}",
  });
  const payload = await response.json();

  assert.equal(response.status, 409);
  assert.equal(payload.error.code, "HUMAN_REVIEW_INCOMPLETE");
});

import assert from "node:assert/strict";
import fs from "node:fs/promises";
import path from "node:path";
import test from "node:test";

import { FinalizationManager } from "../src/finalizer.mjs";
import { ReviewStore } from "../src/review-store.mjs";
import { createReviewServer } from "../src/server.mjs";
import { createReviewFixture } from "./helpers.mjs";

async function listen(server) {
  await new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(0, "127.0.0.1", resolve);
  });
  return `http://127.0.0.1:${server.address().port}`;
}

test("HTTP UI serves state and protects mutations", async (t) => {
  const fixture = await createReviewFixture();
  t.after(fixture.cleanup);
  const store = new ReviewStore({ paths: fixture.paths, requiredTotal: 2 });
  await store.initialize();
  const finalizer = {
    getStatus: () => ({ state: "idle" }),
    start: async () => ({ state: "running" }),
  };
  const server = createReviewServer({ store, finalizer, paths: fixture.paths });
  t.after(() => new Promise((resolve) => server.close(resolve)));
  const baseUrl = await listen(server);

  const stateResponse = await fetch(`${baseUrl}/api/state`);
  const state = await stateResponse.json();
  assert.equal(stateResponse.status, 200);
  assert.equal(state.candidates.length, 2);

  const pageResponse = await fetch(baseUrl);
  const page = await pageResponse.text();
  assert.equal(pageResponse.status, 200);
  assert.match(page, /Finalisasi Review/);
  assert.match(page, /Alasan penolakan/);

  const blocked = await fetch(`${baseUrl}/api/reviews/padi_0001.jpg`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ accepted: "yes" }),
  });
  assert.equal(blocked.status, 403);

  const saved = await fetch(`${baseUrl}/api/reviews/padi_0001.jpg`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", "X-Review-UI": "1" },
    body: JSON.stringify({ accepted: "yes", note: "", rejection_reasons: [] }),
  });
  assert.equal(saved.status, 200);
  assert.equal((await saved.json()).candidate.accepted, "yes");
});

test("finalization manager refuses pending review before running commands", async (t) => {
  const fixture = await createReviewFixture({ decisions: ["yes", ""] });
  t.after(fixture.cleanup);
  const store = new ReviewStore({ paths: fixture.paths, requiredTotal: 2 });
  await store.initialize();
  let commandCount = 0;
  const finalizer = new FinalizationManager({
    paths: fixture.paths,
    store,
    runner: async () => {
      commandCount += 1;
      return { code: 0, stdout: "", stderr: "" };
    },
  });
  await assert.rejects(
    finalizer.start(),
    (error) => error.code === "FINALIZATION_GATE_BLOCKED",
  );
  assert.equal(commandCount, 0);
});

test("finalization stops after exact class shortfall result", async (t) => {
  const fixture = await createReviewFixture({ decisions: ["yes", "yes"] });
  t.after(fixture.cleanup);
  const python = path.join(fixture.root, ".venv", "Scripts", "python.exe");
  await fs.mkdir(path.dirname(python), { recursive: true });
  await fs.writeFile(python, "fixture executable");
  const store = new ReviewStore({ paths: fixture.paths, requiredTotal: 2 });
  await store.initialize();
  const labels = [];
  const finalizer = new FinalizationManager({
    paths: fixture.paths,
    store,
    runner: async ({ args }) => {
      const command = args[1].endsWith("additional_candidates") ? "additional-v2" : args[2];
      labels.push(command);
      const outputIndex = args.indexOf("--json-out");
      await fs.writeFile(
        args[outputIndex + 1],
        JSON.stringify(
          command === "additional-v2"
            ? {
                status: "additional_review_batch_ready",
                review_batch: "additional_batch_v2",
                counts: { jagung: 2 },
              }
            : {
                status: "insufficient_final_images",
                shortfalls: { jagung: { accepted: 79, minimum: 80, shortfall: 1 } },
              },
        ),
      );
      return { code: 0, stdout: "", stderr: "" };
    },
  });

  const started = await finalizer.start();
  assert.equal(started.state, "running");
  const completed = await finalizer.waitForCompletion();
  assert.equal(completed.state, "blocked");
  assert.equal(completed.step, "additional_batch_v2_ready");
  assert.equal(completed.shortfalls.jagung.shortfall, 1);
  assert.equal(completed.package_created, false);
  assert.deepEqual(labels, ["finalize-reviewed", "additional-v2"]);
});

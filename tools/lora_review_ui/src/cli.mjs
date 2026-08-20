import { buildLoraReviewPaths, resolveRepoRoot } from "./paths.mjs";
import { LoraReviewStore } from "./store.mjs";

function argument(name, fallback) {
  const index = process.argv.indexOf(`--${name}`);
  return index >= 0 ? process.argv[index + 1] : fallback;
}

const paths = buildLoraReviewPaths(
  resolveRepoRoot(argument("repo-root", undefined)),
  argument("run-id", process.env.LORA_REVIEW_RUN_ID),
);
const store = new LoraReviewStore({ paths });

try {
  await store.initialize();
  const validation = await store.validate();
  console.log(JSON.stringify(validation, null, 2));
  if (!validation.valid || (process.argv.includes("--require-complete") && !validation.complete)) {
    process.exitCode = 1;
  }
} catch (error) {
  console.error(error.message);
  process.exitCode = 1;
}

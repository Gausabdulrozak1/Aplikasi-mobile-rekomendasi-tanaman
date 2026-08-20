import { buildReviewPaths, resolveRepoRoot } from "./paths.mjs";
import { ReviewStore } from "./review-store.mjs";

function argumentValue(name) {
  const prefix = `--${name}=`;
  const inline = process.argv.find((value) => value.startsWith(prefix));
  if (inline) {
    return inline.slice(prefix.length);
  }
  const index = process.argv.indexOf(`--${name}`);
  return index >= 0 ? process.argv[index + 1] : undefined;
}

async function main() {
  const command = process.argv[2] || "validate";
  if (command !== "validate") {
    throw new Error(`Perintah tidak didukung: ${command}`);
  }
  const paths = buildReviewPaths(resolveRepoRoot(argumentValue("repo-root")));
  const store = new ReviewStore({ paths });
  await store.initialize();
  const validation = await store.validate();
  console.log(JSON.stringify(validation, null, 2));
  if (!validation.valid) {
    process.exitCode = 1;
  }
}

main().catch((error) => {
  console.error(`dataset-review:validate gagal: ${error.message}`);
  process.exitCode = 1;
});

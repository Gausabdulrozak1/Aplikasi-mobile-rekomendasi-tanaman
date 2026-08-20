import path from "node:path";
import { fileURLToPath } from "node:url";

const SOURCE_DIRECTORY = path.dirname(fileURLToPath(import.meta.url));
export const TOOL_ROOT = path.resolve(SOURCE_DIRECTORY, "..");
export const DEFAULT_REPO_ROOT = path.resolve(TOOL_ROOT, "..", "..");
export const DEFAULT_RUN_ID = "20260820T143551Z";

export function resolveRepoRoot(value = process.env.TANIADAPTIF_REPO_ROOT) {
  return path.resolve(value || DEFAULT_REPO_ROOT);
}

export function buildLoraReviewPaths(
  repoRoot = resolveRepoRoot(),
  runId = process.env.LORA_REVIEW_RUN_ID || DEFAULT_RUN_ID,
) {
  if (!/^[A-Za-z0-9_-]{4,80}$/.test(runId)) {
    throw new Error("Run ID review LoRA tidak valid");
  }
  const runDirectory = path.join(
    repoRoot,
    "artifacts",
    "model_evaluation",
    `kaggle_run_${runId}`,
  );
  return {
    repoRoot,
    runId,
    toolRoot: TOOL_ROOT,
    publicDirectory: path.join(TOOL_ROOT, "public"),
    runDirectory,
    reviewCsv: path.join(runDirectory, "human_evaluation_template_local.csv"),
    imagesDirectory: path.join(runDirectory, "generated", "evaluation"),
    backupsDirectory: path.join(runDirectory, "human_review_backups"),
    progressJson: path.join(runDirectory, "human_review_ui_progress.json"),
    completionJson: path.join(runDirectory, "human_review_completion.json"),
    completionMarkdown: path.join(runDirectory, "HUMAN_REVIEW_RESULTS.md"),
    analysisJson: path.join(runDirectory, "human_review_analysis.json"),
    analysisCsv: path.join(runDirectory, "human_review_analysis.csv"),
    analysisMarkdown: path.join(runDirectory, "BAB_IV_HUMAN_REVIEW_RESULTS.md"),
  };
}

import path from "node:path";
import { fileURLToPath } from "node:url";

const SOURCE_DIRECTORY = path.dirname(fileURLToPath(import.meta.url));
export const TOOL_ROOT = path.resolve(SOURCE_DIRECTORY, "..");
export const DEFAULT_REPO_ROOT = path.resolve(TOOL_ROOT, "..", "..");

export function resolveRepoRoot(value = process.env.TANIADAPTIF_REPO_ROOT) {
  return path.resolve(value || DEFAULT_REPO_ROOT);
}

export function buildReviewPaths(repoRoot = resolveRepoRoot()) {
  const reviewDirectory = path.join(repoRoot, "artifacts", "dataset_review");
  const reportsDirectory = path.join(repoRoot, "ml_pipeline", "data", "reports");
  return {
    repoRoot,
    toolRoot: TOOL_ROOT,
    publicDirectory: path.join(TOOL_ROOT, "public"),
    reviewDirectory,
    manualReviewCsv: path.join(reviewDirectory, "manual_review_template.csv"),
    backupsDirectory: path.join(reviewDirectory, "backups"),
    exportsDirectory: path.join(reviewDirectory, "exports"),
    progressJson: path.join(reviewDirectory, "review_progress.json"),
    finalizationStatusJson: path.join(reviewDirectory, "finalization_status.json"),
    finalizationLogsDirectory: path.join(reviewDirectory, "finalization_logs"),
    candidatesDirectory: path.join(reviewDirectory, "candidates"),
    mappingCsv: path.join(reportsDirectory, "curation_mapping.csv"),
    semanticCsv: path.join(reportsDirectory, "automated_semantic_review.csv"),
    inventoryCsv: path.join(reportsDirectory, "inventory_all_classes.csv"),
    invalidImagesCsv: path.join(reportsDirectory, "invalid_images.csv"),
    exactDuplicatesCsv: path.join(reportsDirectory, "exact_duplicates.csv"),
    nearDuplicatesCsv: path.join(reportsDirectory, "near_duplicates.csv"),
    crossClassDuplicatesCsv: path.join(reportsDirectory, "cross_class_duplicates.csv"),
    configPath: path.join(repoRoot, "ml_pipeline", "configs", "dataset_public_multicrop.yaml"),
    packagesDirectory: path.join(repoRoot, "artifacts", "dataset_packages"),
  };
}

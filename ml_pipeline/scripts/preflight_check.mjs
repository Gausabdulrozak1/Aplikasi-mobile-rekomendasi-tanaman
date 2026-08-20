import fs from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";

const root = process.cwd();
let failed = false;

function fail(message) {
  console.error(`preflight: ${message}`);
  failed = true;
}

function ok(message) {
  console.log(`preflight: ok - ${message}`);
}

function assertFile(filePath) {
  if (!fs.existsSync(path.join(root, filePath))) {
    fail(`missing file: ${filePath}`);
  }
}

function assertDirectory(directoryPath) {
  const absolute = path.join(root, directoryPath);
  if (!fs.existsSync(absolute) || !fs.statSync(absolute).isDirectory()) {
    fail(`missing directory: ${directoryPath}`);
  }
}

function read(filePath) {
  return fs.readFileSync(path.join(root, filePath), "utf8");
}

function assertIncludes(filePath, fragments) {
  const text = read(filePath);
  for (const fragment of fragments) {
    if (!text.includes(fragment)) {
      fail(`${filePath} does not include required fragment: ${fragment}`);
    }
  }
}

function assertNotIncludes(filePath, fragments) {
  const text = read(filePath);
  for (const fragment of fragments) {
    if (text.includes(fragment)) {
      fail(`${filePath} includes forbidden fragment: ${fragment}`);
    }
  }
}

function* walk(directory) {
  for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
    if ([".git", ".dart_tool", ".gradle", "build", "node_modules", ".venv", "venv"].includes(entry.name)) {
      continue;
    }
    const fullPath = path.join(directory, entry.name);
    const relative = path.relative(root, fullPath).replaceAll("\\", "/");
    if (relative === "artifacts/dataset_build/kaggle_imagefolder_validation_env") {
      continue;
    }
    if (entry.isDirectory()) {
      yield* walk(fullPath);
    } else {
      yield fullPath;
    }
  }
}

function isGitIgnored(relativePath) {
  const result = spawnSync("git", ["check-ignore", "-q", "--", relativePath], {
    cwd: root,
    stdio: "ignore",
  });
  return result.status === 0;
}

const requiredFiles = [
  ".gitignore",
  "README.md",
  "TASKS.md",
  "STATUS.md",
  "ml_pipeline/configs/pilot_padi.yaml",
  "ml_pipeline/configs/pilot_padi_riceseg_hf.example.yaml",
  "ml_pipeline/configs/dataset_candidates.json",
  "ml_pipeline/configs/dataset_public_multicrop.yaml",
  "ml_pipeline/configs/training_public_multicrop.yaml",
  "ml_pipeline/configs/evaluation_public_multicrop.yaml",
  "ml_pipeline/data/dataset_source_manifest.csv",
  "ml_pipeline/notebooks/00_run_complete_lora_pipeline_colab.ipynb",
  "ml_pipeline/notebooks/00_train_lora_multicrop_kaggle_final.ipynb",
  "ml_pipeline/notebooks/00_train_lora_multicrop_kaggle_final.py",
  "ml_pipeline/notebooks/01_prepare_dataset_colab.ipynb",
  "ml_pipeline/notebooks/01_prepare_dataset_colab.py",
  "ml_pipeline/notebooks/01_prepare_public_multicrop_dataset_colab.ipynb",
  "ml_pipeline/notebooks/01_prepare_public_multicrop_dataset_colab.py",
  "ml_pipeline/notebooks/02_train_lora_sd15_colab.ipynb",
  "ml_pipeline/notebooks/02_train_lora_sd15_colab.py",
  "ml_pipeline/notebooks/02_train_public_multicrop_lora_sd15_colab.ipynb",
  "ml_pipeline/notebooks/02_train_public_multicrop_lora_sd15_colab.py",
  "ml_pipeline/notebooks/03_evaluate_lora_colab.ipynb",
  "ml_pipeline/notebooks/03_evaluate_lora_colab.py",
  "ml_pipeline/notebooks/03_evaluate_public_multicrop_lora_colab.ipynb",
  "ml_pipeline/notebooks/03_evaluate_public_multicrop_lora_colab.py",
  "ml_pipeline/scripts/validate_dataset_candidates.mjs",
  "ml_pipeline/scripts/validate_notebooks.mjs",
  "ml_pipeline/scripts/security_scan.mjs",
  "ml_pipeline/scripts/prepare_colab_upload_parts.ps1",
  "ml_pipeline/scripts/build_kaggle_dataset.py",
  "ml_pipeline/scripts/materialize_kaggle_evidence.py",
  "ml_pipeline/scripts/render_kaggle_notebook.py",
  "ml_pipeline/scripts/validate_kaggle_imagefolder.py",
  "ml_pipeline/src/dataset/kaggle_package.py",
  "ml_pipeline/src/training/kaggle_runtime.py",
  "ml_pipeline/tests/test_kaggle_dataset_package.py",
  "ml_pipeline/tests/test_kaggle_notebook_contract.py",
  "ml_pipeline/src/training/validate_run.py",
  "ml_pipeline/src/training/validate_kaggle_export.py",
  "ml_pipeline/src/evaluation/validate_human_review.py",
  "ml_pipeline/src/evaluation/analyze_human_review.py",
  "ml_pipeline/tests/test_human_review_analysis.py",
  "tools/lora_review_ui/src/server.mjs",
  "tools/lora_review_ui/src/store.mjs",
  "tools/lora_review_ui/src/cli.mjs",
  "tools/lora_review_ui/public/index.html",
  "tools/lora_review_ui/public/styles.css",
  "tools/lora_review_ui/public/app.js",
  "tools/lora_review_ui/test/store.test.mjs",
  "tools/lora_review_ui/test/server.test.mjs",
  "ml_pipeline/tests/test_colab_runtime_notebook_contract.py",
  "ml_pipeline/tests/test_lora_filename_contract.py",
  "inference_api/app/main.py",
  "inference_api/app/api/routes.py",
  "inference_api/app/providers/mock.py",
  "inference_api/app/providers/diffusers_provider.py",
  "inference_api/app/providers/lora_validation.py",
  "inference_api/requirements-diffusers.txt",
  "inference_api/gpu.env.example",
  "inference_api/.env.example",
  "inference_api/scripts/gpu_preflight.py",
  "inference_api/scripts/e2e_probe.py",
  "inference_api/tests/test_api.py",
  "inference_api/tests/test_e2e_probe.py",
  "backend-nodejs/.env.example",
  "backend-nodejs/src/middleware/visualAccess.js",
  "backend-nodejs/src/routes/visualRoutes.js",
  "backend-nodejs/src/services/inferenceService.js",
  "backend-nodejs/test/inferenceProxy.test.js",
  "mobile-flutter/tani_adaptif/lib/services/stable_diffusion_service.dart",
  "mobile-flutter/tani_adaptif/lib/models/generate_visual_model.dart",
  "mobile-flutter/tani_adaptif/test/stable_diffusion_service_test.dart",
  "deployment/runpod/runtime.env.example",
  "deployment/runpod/bootstrap_runpod.sh",
  "deployment/runpod/start_stack.sh",
  "deployment/runpod/build_bundle.ps1",
  "docs/API_CONTRACT.md",
  "docs/COLAB_RUNBOOK.md",
  "docs/COLAB_RESOURCE_PLAN.md",
  "docs/KAGGLE_FINAL_RUN_GUIDE.md",
  "docs/LORA_HUMAN_REVIEW_GUIDE.md",
  "docs/KAGGLE_NOTEBOOK_CELL_BY_CELL.md",
  "docs/KAGGLE_CELLS_COPY_PASTE.txt",
  "docs/DATASET_CANDIDATES.md",
  "docs/DATASET_CARD.md",
  "docs/DATASET_REVIEW_GUIDE.md",
  "docs/DATASET_SELECTION_DECISION.md",
  "docs/EXPERIMENT_GUIDE.md",
  "docs/LOCAL_MOCK_API_SMOKE.md",
  "docs/GPU_INFERENCE_DEPLOYMENT_REPORT.md",
  "docs/MODEL_CARD.md",
  "docs/PYTHON_SETUP.md",
  "docs/RUN_COMMANDS.md",
  "docs/THESIS_EVIDENCE.md",
  "docs/THESIS_DATASET_REVISION_NOTES.md",
  "artifacts/dataset_review/manual_review_template.csv",
  "artifacts/dataset_packages/dataset_multicrop_v1_kaggle_fixed.zip",
  "artifacts/dataset_packages/dataset_multicrop_v1_kaggle_fixed.sha256",
  "artifacts/dataset_packages/KAGGLE_DATASET_PACKAGE_REPORT.md",
  "artifacts/dataset_packages/KAGGLE_DATASET_PACKAGE_REPORT.json",
  "artifacts/dataset_build/kaggle_imagefolder_validation_report.json",
  "ml_pipeline/data/reports/kaggle_physical_image_index.csv",
  "ml_pipeline/data/reports/kaggle_metadata_resolution.csv",
  "package.json",
  "tools/dataset_review_ui/src/server.mjs",
  "tools/dataset_review_ui/src/review-store.mjs",
  "tools/dataset_review_ui/public/index.html",
];

const requiredDirectories = [
  "ml_pipeline/configs",
  "ml_pipeline/data/examples",
  "ml_pipeline/notebooks",
  "ml_pipeline/src/dataset",
  "ml_pipeline/src/evaluation",
  "ml_pipeline/src/training",
  "ml_pipeline/tests",
  "inference_api/app/api",
  "inference_api/app/providers",
  "inference_api/tests",
  "artifacts/samples",
  "artifacts/evaluation",
  "artifacts/reports",
  "artifacts/dataset_review",
  "artifacts/dataset_build/kaggle_fixed_v1",
  "artifacts/dataset_packages",
  "tools/dataset_review_ui/public",
  "tools/dataset_review_ui/src",
  "tools/dataset_review_ui/test",
];

for (const directory of requiredDirectories) {
  assertDirectory(directory);
}
ok("required directories exist");

for (const file of requiredFiles) {
  assertFile(file);
}
ok("required files exist");

assertIncludes(".gitignore", [
  ".env",
  ".env.*",
  "!.env.example",
  "*kaggle.json",
  "*.safetensors",
  "checkpoint-*/",
  "ml_pipeline/data/raw/",
  "ml_pipeline/data/processed/",
  "ml_pipeline/data/downloads/",
  "inference_api/generated/",
  "deployment/runpod/runtime.env",
  "mobile-flutter/tani_adaptif/config/*.local.json",
  "artifacts/dataset_review/backups/",
  "artifacts/colab_upload/",
]);
ok(".gitignore protects secrets, datasets, generated images, and model weights");

assertIncludes("ml_pipeline/configs/pilot_padi.yaml", [
  "base_model: stable-diffusion-v1-5/stable-diffusion-v1-5",
  "trigger_token: gaus_padi_public",
  "resolution: 512",
  "seed: 42",
  "rank: 8",
  "batch_size: 1",
  "gradient_accumulation_steps: 4",
  "dataloader_num_workers: 0",
  "max_train_steps: 800",
  "checkpointing_steps: 200",
  "max_images_per_class: 100",
  "max_images_total: 100",
  "minimum_width: 512",
  "minimum_height: 512",
]);
ok("pilot padi config matches required pilot constraints");

assertIncludes("ml_pipeline/configs/dataset_public_multicrop.yaml", [
  "trigger_token: taniadaptif_padi",
  "trigger_token: taniadaptif_jagung",
  "trigger_token: taniadaptif_cabai",
  "trigger_token: taniadaptif_kacang_tanah",
  "type: local_aikmel",
  "source_manifest: ml_pipeline/data/dataset_source_manifest.csv",
]);
ok("multisource dataset config uses final source policy and triggers");

assertIncludes("ml_pipeline/configs/training_public_multicrop.yaml", [
  "max_train_steps: 1600",
  "checkpointing_steps: 200",
  "smoke_test:",
  "max_train_steps: 100",
  "checkpointing_steps: 50",
  "outputs/smoke_test",
  "outputs/multicrop_v1",
]);
ok("multicrop training config separates smoke and main outputs");

const candidates = JSON.parse(read("ml_pipeline/configs/dataset_candidates.json"));
const covered = new Set(candidates.candidates.flatMap((candidate) => candidate.commodities));
for (const commodity of candidates.required_commodities) {
  if (!covered.has(commodity)) {
    fail(`dataset registry does not cover commodity: ${commodity}`);
  }
}
ok("dataset registry covers required commodities");

assertIncludes("ml_pipeline/notebooks/01_prepare_dataset_colab.ipynb", [
  "drive.mount",
  "TANIADAPTIF_CONFIG",
  "huggingface-cli",
  "PROCESSED_DRIVE_DIR",
  "run_cli(\\\"audit\\\")",
  "run_cli(\\\"prepare\\\")",
]);
assertIncludes("ml_pipeline/notebooks/02_train_lora_sd15_colab.ipynb", [
  "RESUME_FROM_CHECKPOINT",
  "checkpointing_steps",
  "--rank",
  "pytorch_lora_weights.safetensors",
  "train_text_to_image_lora.py",
  "COLAB_RELEASE_TAG",
  "FP16_SUPPORTED",
  "DIFFUSERS_REF",
  "DRIVE_ROOT / \\\"datasets\\\"",
  "TANIADAPTIF_CONFIG",
  "--dataloader_num_workers",
  "--report_to",
]);
assertIncludes("ml_pipeline/notebooks/03_evaluate_lora_colab.ipynb", [
  "load_lora_weights",
  "contact_sheet",
  "human_eval",
  "negative_prompt",
]);
assertIncludes("ml_pipeline/notebooks/02_train_lora_sd15_colab.py", [
  "RESUME_FROM_CHECKPOINT",
  "DIFFUSERS_REF",
  "FP16_SUPPORTED",
  "DRIVE_ROOT / \"datasets\"",
  "TANIADAPTIF_CONFIG",
  "--dataloader_num_workers",
  "--report_to",
]);
ok("notebooks include prepare, checkpoint/resume, training, and evaluation signals");

assertIncludes("ml_pipeline/src/training/validate_run.py", [
  "training_manifest.json",
  "checkpoint-{expected_steps}",
  "loss_log.csv",
  "training_environment_report.json",
  "validation_images",
  "SafeTensors",
  "Image.open",
  "checkpoint_file_count",
]);
ok("CPU-only training artifact validator checks structure and reproducibility evidence");

assertIncludes("ml_pipeline/notebooks/01_prepare_public_multicrop_dataset_colab.ipynb", [
  "/content/dataset_multicrop_v1.zip",
  "/content/dataset_multicrop_v1_upload_parts",
  "assemble_runtime_package",
  "upload_manifest.json",
  "f6aa060658cf95e48996f10f0ffde200938d340dd15e6b60adace5bb5cecfb33",
  "/content/taniadaptif_dataset/multicrop_v1",
  "PACKAGE_MANIFEST.json",
  "manual_review_status",
  "Padi source distribution",
  "Caption:",
]);
assertNotIncludes("ml_pipeline/notebooks/01_prepare_public_multicrop_dataset_colab.ipynb", [
  "dataset_multicrop_v1.sha256",
  "DRIVE_ROOT / \"datasets\"",
]);
assertIncludes("ml_pipeline/notebooks/00_run_complete_lora_pipeline_colab.ipynb", [
  "f6aa060658cf95e48996f10f0ffde200938d340dd15e6b60adace5bb5cecfb33",
  "2026-08-14-imagefolder-probe-v8",
  "/content/drive/MyDrive/skripsi_lora/datasets/dataset_multicrop_v1.zip",
  "return package_path, \\\"google_drive\\\"",
  "/content/dataset_multicrop_v1_upload_parts",
  "assemble_runtime_package",
  "upload_manifest.json",
  "PREP_NOTEBOOK",
  "TANIADAPTIF_RUN_MODE",
  "TANIADAPTIF_RESUME_FROM_CHECKPOINT",
  "environment={",
  "orchestrator_smoke_validation.json",
  "orchestrator_main_validation.json",
  "base_vs_lora_manifest.csv",
  "complete_pipeline_state.json",
  "SMOKE_LORA = smoke_config",
  "MAIN_LORA = main_config",
  "lora_valid",
  "training_failure",
]);
assertNotIncludes("ml_pipeline/notebooks/00_run_complete_lora_pipeline_colab.ipynb", [
  "Parameter source tidak unik",
  "all_source.count",
]);
assertIncludes("ml_pipeline/notebooks/02_train_public_multicrop_lora_sd15_colab.ipynb", [
  "taniadaptif_padi",
  "/content/taniadaptif_dataset/multicrop_v1",
  "runtime_dataset_manifest.json",
  "source_type",
  "SMOKE_TEST",
  "RESUME_FROM_CHECKPOINT",
  "RUN_MODE",
  "loss_log.csv",
  "training_manifest.json",
  "validation_images",
  "DIFFUSERS_DEFAULT_LORA_FILENAME",
  "normalize_diffusers_lora",
  "sha256_file",
  "os.replace",
  "SKIP_TRAINING",
  "COLAB_TRAINING_REQUIREMENTS",
  "peft>=0.17.0,<1",
  "dependency_probe_source",
  "TRAINING_REPORT_TO",
  "TRAINING_LOGGING_DIR",
  "UNUSED_CONFLICTING_PACKAGES",
  "for unused_package in (\\\"torchao\\\", \\\"wandb\\\")",
  "Training entrypoint import probe: passed",
  "peft_adapter_probe",
  "validate_runtime_split",
  "HF_DATASETS_CACHE",
  "Fresh HF Datasets cache:",
  "training_error_excerpt",
  "ImageFolder decoder probe: passed",
]);
assertNotIncludes("ml_pipeline/notebooks/02_train_public_multicrop_lora_sd15_colab.ipynb", [
  "examples/text_to_image/requirements.txt",
]);
assertIncludes("ml_pipeline/notebooks/03_evaluate_public_multicrop_lora_colab.ipynb", [
  "class_confusion_review.csv",
  "base_vs_lora_manifest.csv",
  "automated_metrics.csv",
  "class_confusion_proxy.csv",
  "evaluation_summary.md",
  "human_evaluation_template.csv",
  "load_lora_weights",
]);
assertIncludes("ml_pipeline/notebooks/02_train_public_multicrop_lora_sd15_colab.py", [
  "RUN_MODE",
  "loss_log.csv",
  "training_manifest.json",
  "validation_images",
  "DIFFUSERS_DEFAULT_LORA_FILENAME",
  "normalize_diffusers_lora",
  "sha256_file",
  "os.replace",
  "SKIP_TRAINING",
  "COLAB_TRAINING_REQUIREMENTS",
  "peft>=0.17.0,<1",
  "dependency_probe_source",
  "TRAINING_REPORT_TO = \"tensorboard\"",
  "TRAINING_LOGGING_DIR = \"tensorboard\"",
  "UNUSED_CONFLICTING_PACKAGES = (\"torchao\", \"wandb\")",
  "for unused_package in (\"torchao\", \"wandb\")",
  "Training entrypoint import probe: passed",
  "peft_adapter_probe",
  "validate_runtime_split",
  "HF_DATASETS_CACHE",
  "Fresh HF Datasets cache:",
  "training_error_excerpt",
  "ImageFolder decoder probe: passed",
]);
assertNotIncludes("ml_pipeline/notebooks/02_train_public_multicrop_lora_sd15_colab.py", [
  '"--report_to",\n    "none",',
]);
ok("multicrop notebooks include source-aware preparation, training, and evaluation");

assertIncludes("ml_pipeline/notebooks/00_train_lora_multicrop_kaggle_final.ipynb", [
  "e232f79d2f8ae20b4fb765efb38435ce05e929406e88faba6b02aaaafd1ad42d",
  "dataset_multicrop_v1_kaggle_fixed.zip",
  "stable-diffusion-v1-5/stable-diffusion-v1-5",
  "0f252be0ed42006c125ef4429156cb13ae6c1d60",
  "materialize_checkpoint",
  "copied_and_sha256_verified_from_kaggle_input",
  "--cache_dir",
  "multisource_multicrop_lora.safetensors",
  "complete_pipeline_state.json",
  "FINAL STATUS: SUCCESS",
]);
assertNotIncludes("ml_pipeline/notebooks/00_train_lora_multicrop_kaggle_final.ipynb", [
  "/content/drive",
  "drive.mount",
  "google.colab",
  "execute_notebook",
  "003_lahan_cabai.jpg",
  "IMG_20240923_181506.jpg",
]);
const kaggleNotebook = JSON.parse(
  read("ml_pipeline/notebooks/00_train_lora_multicrop_kaggle_final.ipynb"),
);
if (kaggleNotebook.cells.length !== 52) {
  fail(`Kaggle notebook cell count is ${kaggleNotebook.cells.length}, expected 52`);
}
const fixedChecksum = read(
  "artifacts/dataset_packages/dataset_multicrop_v1_kaggle_fixed.sha256",
).trim();
if (!fixedChecksum.startsWith("e232f79d2f8ae20b4fb765efb38435ce05e929406e88faba6b02aaaafd1ad42d")) {
  fail("Kaggle fixed package checksum record does not match the validated artifact");
}
ok("Kaggle fixed package, standalone notebook, resume, and fail-fast contracts are present");

assertIncludes("inference_api/app/providers/mock.py", ["class MockImageGenerator", "placeholder"]);
assertIncludes("inference_api/app/providers/diffusers_provider.py", [
  "class DiffusersImageGenerator",
  "load_lora_weights",
  "require_gpu",
  "validate_lora_artifact",
]);
assertIncludes("inference_api/requirements-diffusers.txt", [
  "diffusers==0.35.1",
  "transformers==4.57.6",
  "safetensors==0.8.0",
]);
assertIncludes("inference_api/app/api/routes.py", ["/health", "/ready", "/v1/model-info", "/v1/generate"]);
assertIncludes("inference_api/app/services/prompt_builder.py", [
  "gaus_padi_public",
  "direct_prompt",
  "rule_engine_input",
]);
assertIncludes("inference_api/.env.example", [
  "INFERENCE_PROVIDER=mock",
  "LORA_PATH=",
  "LORA_SHA256=",
  "REQUIRE_GPU=false",
  "INFERENCE_REQUIRE_TOKEN=false",
]);
assertIncludes("inference_api/gpu.env.example", [
  "INFERENCE_PROVIDER=diffusers",
  "REQUIRE_GPU=true",
  "INFERENCE_REQUIRE_TOKEN=true",
  "INFERENCE_API_TOKEN=",
  "0bda8908d577513110c22cf5ec1b8a7e008d2b26dd90525732a5c4e4b1bdd43a",
]);
assertIncludes("inference_api/app/main.py", [
  "X-Inference-Token",
  "INFERENCE_AUTH_REQUIRED",
]);
ok("inference API provider, artifact identity, and private-token contracts are present");

assertIncludes("backend-nodejs/.env.example", [
  "PUBLIC_API_BASE_URL=",
  "INFERENCE_API_BASE_URL=",
  "INFERENCE_API_TOKEN=",
  "INFERENCE_API_TIMEOUT_MS=",
  "BACKEND_VISUAL_REQUIRE_TOKEN=false",
  "BACKEND_VISUAL_API_TOKEN=",
  "VISUAL_RATE_LIMIT_MAX=0",
]);
assertIncludes("backend-nodejs/src/middleware/visualAccess.js", [
  "X-Client-Token",
  "VISUAL_AUTH_REQUIRED",
  "VISUAL_RATE_LIMITED",
]);
assertIncludes("backend-nodejs/src/routes/visualRoutes.js", [
  "'/ready'",
  "'/model-info'",
  "'/generate'",
  "'/images/:fileName'",
  "delivery_path: 'backend_proxy'",
  "upstream_image_url_exposed: false",
  "router.post('/generate', limitVisualRequests",
]);
assertNotIncludes("backend-nodejs/src/routes/visualRoutes.js", [
  "router.use(limitVisualRequests)",
]);
assertIncludes("backend-nodejs/src/services/inferenceService.js", [
  "X-Inference-Token",
  "'/v1/generate'",
  "'/v1/model-info'",
  "'/ready'",
]);
assertIncludes("backend-nodejs/src/app.js", ["/api/visual"]);
ok("backend owns the authenticated inference proxy and generated-image delivery path");

assertIncludes("deployment/runpod/runtime.env.example", [
  "INFERENCE_PROVIDER=diffusers",
  "INFERENCE_REQUIRE_TOKEN=true",
  "BACKEND_VISUAL_REQUIRE_TOKEN=true",
  "GENERATION_TIMEOUT_SECONDS=80",
  "VISUAL_RATE_LIMIT_MAX=6",
  "multisource_multicrop_lora_sd15_20260820T143551Z",
  "0bda8908d577513110c22cf5ec1b8a7e008d2b26dd90525732a5c4e4b1bdd43a",
]);
assertIncludes("inference_api/scripts/e2e_probe.py", [
  '"provider": "diffusers"',
  '"device": "cuda"',
  '"is_mock": False',
  "final_lora_sha256_matches",
  "rule_engine_succeeded",
  "generation_uses_rule_engine_crop",
  "delivery_uses_backend_proxy",
  "automatic_quality_score_created",
]);
ok("RunPod startup and real end-to-end evidence gates are present");

assertIncludes("package.json", [
  '"dataset-review"',
  '"dataset-review:validate"',
  '"dataset-review:test"',
  '"lora-review"',
  '"lora-review:validate"',
  '"lora-review:test"',
]);
assertIncludes("tools/dataset_review_ui/src/server.mjs", [
  "127.0.0.1",
  'request.headers["x-review-ui"]',
  "/api/finalize",
]);
ok("local dataset review UI, validator, and test commands are present");

assertIncludes("tools/lora_review_ui/src/server.mjs", [
  "127.0.0.1",
  'request.headers["x-review-ui"]',
  "/api/finalize",
]);
assertIncludes("tools/lora_review_ui/src/store.mjs", [
  "human_review_source",
  "reviewer_entered_local_ui",
  "completionJson",
  "completionMarkdown",
]);
assertIncludes("tools/lora_review_ui/src/paths.mjs", [
  "human_review_ui_progress.json",
  "human_review_analysis.json",
  "human_review_analysis.csv",
  "BAB_IV_HUMAN_REVIEW_RESULTS.md",
]);
assertNotIncludes("tools/lora_review_ui/src/paths.mjs", [
  'progressJson: path.join(runDirectory, "human_review_progress.json")',
]);
ok("local LoRA review UI, evidence separation, and finalization gate are present");

assertIncludes("ml_pipeline/src/evaluation/analyze_human_review.py", [
  "complete_validated_human_review",
  "exact_mcnemar_discordant_pairs",
  "exact_sign_test_ties_excluded",
  "BAB_IV_HUMAN_REVIEW_RESULTS.md",
  "reviewer_identity_independently_verified",
]);
ok("paired human-review analyzer and conservative BAB IV outputs are present");

assertIncludes("mobile-flutter/tani_adaptif/lib/config/app_config.dart", [
  "BACKEND_API_BASE_URL",
  "BACKEND_VISUAL_API_TOKEN",
]);
assertNotIncludes("mobile-flutter/tani_adaptif/lib/config/app_config.dart", [
  "INFERENCE_API_BASE_URL",
]);
assertIncludes("mobile-flutter/tani_adaptif/lib/services/stable_diffusion_service.dart", [
  "weatherSummary",
  "visual/generate",
  "visual/model-info",
]);
assertNotIncludes("mobile-flutter/tani_adaptif/lib/services/stable_diffusion_service.dart", [
  "/v1/generate",
  "INFERENCE_API_BASE_URL",
]);
assertIncludes("mobile-flutter/tani_adaptif/lib/screens/hasil_screen.dart", [
  "LocalStorageService",
  "saveVisualHistory",
  "StableDiffusionService",
]);
ok("Flutter inference integration keeps generated visual separate from recommendation");

const forbiddenArtifactExtensions = new Set([".safetensors", ".ckpt", ".pt", ".bin", ".zip", ".tar", ".7z"]);
const allowedGeneratedArchives = new Set([
  "artifacts/dataset_packages/dataset_multicrop_v1.zip",
  "artifacts/dataset_packages/dataset_multicrop_v1_kaggle_fixed.zip",
]);
let protectedLocalArtifactCount = 0;
for (const filePath of walk(root)) {
  const relative = path.relative(root, filePath).replaceAll("\\", "/");
  const extension = path.extname(filePath).toLowerCase();
  if (forbiddenArtifactExtensions.has(extension) && !allowedGeneratedArchives.has(relative)) {
    if (isGitIgnored(relative)) {
      protectedLocalArtifactCount += 1;
    } else {
      fail(`large/model/archive artifact is not protected by .gitignore: ${relative}`);
    }
  }
}
ok(
  `${protectedLocalArtifactCount} local model/archive artifacts are protected by .gitignore`,
);

const envExample = read("inference_api/.env.example");
const secretPatterns = [/sk-[A-Za-z0-9]{20,}/, /hf_[A-Za-z0-9]{20,}/, /KAGGLE_KEY\s*=/];
for (const pattern of secretPatterns) {
  if (pattern.test(envExample)) {
    fail(`inference_api/.env.example contains possible secret: ${pattern}`);
  }
}
ok(".env.example contains placeholders only");

if (failed) {
  process.exit(1);
}

console.log("preflight: all checks passed");

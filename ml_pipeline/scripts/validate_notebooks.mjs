import fs from "node:fs";

const notebooks = [
  "ml_pipeline/notebooks/00_train_lora_multicrop_kaggle_final.ipynb",
  "ml_pipeline/notebooks/00_run_complete_lora_pipeline_colab.ipynb",
  "ml_pipeline/notebooks/01_prepare_dataset_colab.ipynb",
  "ml_pipeline/notebooks/01_prepare_public_multicrop_dataset_colab.ipynb",
  "ml_pipeline/notebooks/02_train_lora_sd15_colab.ipynb",
  "ml_pipeline/notebooks/02_train_public_multicrop_lora_sd15_colab.ipynb",
  "ml_pipeline/notebooks/03_evaluate_lora_colab.ipynb",
  "ml_pipeline/notebooks/03_evaluate_public_multicrop_lora_colab.ipynb",
];

let failed = false;

for (const notebookPath of notebooks) {
  const raw = fs.readFileSync(notebookPath, "utf8");
  const notebook = JSON.parse(raw);

  if (notebook.nbformat !== 4) {
    console.error(`${notebookPath}: nbformat must be 4`);
    failed = true;
  }

  if (!Array.isArray(notebook.cells) || notebook.cells.length === 0) {
    console.error(`${notebookPath}: notebook has no cells`);
    failed = true;
  }

  if (
    notebookPath.endsWith("00_train_lora_multicrop_kaggle_final.ipynb") &&
    notebook.cells.length !== 52
  ) {
    console.error(`${notebookPath}: Kaggle notebook must have exactly 52 cells`);
    failed = true;
  }

  const source = notebook.cells.flatMap((cell) => cell.source ?? []).join("");
  const forbiddenPatterns = [
    /hf_[A-Za-z0-9]{20,}/,
    /sk-[A-Za-z0-9]{20,}/,
    /KAGGLE_KEY\s*=/,
    /api[_-]?key\s*=/i,
  ];
  for (const pattern of forbiddenPatterns) {
    if (pattern.test(source)) {
      console.error(`${notebookPath}: possible secret matched ${pattern}`);
      failed = true;
    }
  }

  console.log(`${notebookPath}: ok (${notebook.cells.length} cells)`);
}

if (failed) {
  process.exit(1);
}

import { spawn } from "node:child_process";
import crypto from "node:crypto";
import fs from "node:fs";
import fsp from "node:fs/promises";
import path from "node:path";

import { atomicWriteJson } from "./atomic.mjs";
import { ConflictError } from "./errors.mjs";

async function readJsonOptional(filePath) {
  try {
    return JSON.parse(await fsp.readFile(filePath, "utf8"));
  } catch (error) {
    if (error?.code === "ENOENT") {
      return null;
    }
    throw error;
  }
}

async function sha256File(filePath) {
  const hash = crypto.createHash("sha256");
  const stream = fs.createReadStream(filePath);
  for await (const chunk of stream) {
    hash.update(chunk);
  }
  return hash.digest("hex");
}

export function runCommand({ executable, args, cwd, logPath }) {
  return new Promise((resolve, reject) => {
    const log = fs.createWriteStream(logPath, { flags: "a", encoding: "utf8" });
    log.write(`\n> ${executable} ${args.join(" ")}\n`);
    let spawnFailed = false;
    const child = spawn(executable, args, {
      cwd,
      shell: false,
      windowsHide: true,
      env: { ...process.env, PYTHONUNBUFFERED: "1" },
    });
    const stdout = [];
    const stderr = [];
    child.stdout.on("data", (chunk) => {
      stdout.push(chunk);
      log.write(chunk);
    });
    child.stderr.on("data", (chunk) => {
      stderr.push(chunk);
      log.write(chunk);
    });
    child.on("error", (error) => {
      spawnFailed = true;
      log.end();
      reject(error);
    });
    child.on("close", (code) => {
      if (spawnFailed) {
        return;
      }
      log.write(`\n[exit ${code}]\n`);
      log.end();
      resolve({
        code: code ?? 1,
        stdout: Buffer.concat(stdout).toString("utf8"),
        stderr: Buffer.concat(stderr).toString("utf8"),
      });
    });
  });
}

function commandSummary(label, result) {
  return {
    label,
    exit_code: result.code,
    completed_at: new Date().toISOString(),
  };
}

export class FinalizationManager {
  constructor({ paths, store, runner = runCommand, now = () => new Date() }) {
    this.paths = paths;
    this.store = store;
    this.runner = runner;
    this.now = now;
    this.status = {
      state: "idle",
      step: "waiting_for_review",
      message: "Finalisasi belum dijalankan.",
      commands: [],
    };
    this.activeRun = null;
  }

  async initialize() {
    const saved = await readJsonOptional(this.paths.finalizationStatusJson);
    if (saved?.state === "running") {
      this.status = {
        ...saved,
        state: "interrupted",
        step: "interrupted",
        message: "Proses sebelumnya terhenti. Validasi ulang lalu jalankan finalisasi kembali.",
        finished_at: this.now().toISOString(),
      };
      await this.#persist();
    } else if (saved) {
      this.status = saved;
    }
    return this.getStatus();
  }

  getStatus() {
    return structuredClone(this.status);
  }

  async start() {
    if (this.activeRun) {
      throw new ConflictError(
        "Finalisasi sedang berjalan",
        "FINALIZATION_ALREADY_RUNNING",
        this.getStatus(),
      );
    }
    const validation = await this.store.validate();
    if (!validation.can_finalize) {
      throw new ConflictError(
        "Seluruh kandidat harus berstatus yes atau no sebelum finalisasi",
        "FINALIZATION_GATE_BLOCKED",
        validation,
      );
    }

    const backupPath = await this.store.createBackup({ force: true, label: "pre_finalize" });
    await this.store.markReviewComplete();
    const runId = this.now().toISOString().replace(/[-:.TZ]/g, "");
    await fsp.mkdir(this.paths.finalizationLogsDirectory, { recursive: true });
    const logPath = path.join(
      this.paths.finalizationLogsDirectory,
      `dataset_finalization_${runId}.log`,
    );
    this.status = {
      run_id: runId,
      state: "running",
      step: "prepare",
      message: "Menjalankan kurasi final dan menghitung kelayakan setiap kelas.",
      started_at: this.now().toISOString(),
      finished_at: null,
      backup: backupPath,
      log: logPath,
      commands: [],
      training_started: false,
      package_created: false,
    };
    await this.#persist();
    this.activeRun = this.#run(logPath).finally(() => {
      this.activeRun = null;
    });
    return this.getStatus();
  }

  async waitForCompletion() {
    if (this.activeRun) {
      await this.activeRun;
    }
    return this.getStatus();
  }

  async #run(logPath) {
    try {
      const python = await this.#pythonExecutable();
      const prepareOut = path.join(this.paths.reviewDirectory, "finalization_prepare_result.json");
      const prepare = await this.#runStep({
        label: "dataset prepare",
        executable: python,
        args: this.#pipelineArgs("finalize-reviewed", prepareOut),
        logPath,
      });
      const prepareResult = await readJsonOptional(prepareOut);
      if (!prepareResult) {
        throw new Error("Pipeline prepare tidak menghasilkan JSON status");
      }
      this.status.prepare_result = prepareResult;

      if (prepareResult.status === "insufficient_final_images") {
        const targets =
          prepareResult.next_batch_candidate_targets ||
          Object.fromEntries(
            Object.entries(prepareResult.shortfalls || {}).map(([classId, item]) => [
              classId,
              Math.max(1, Math.ceil(Number(item.shortfall || 0) * 1.3)),
            ]),
          );
        const additionalOut = path.join(
          this.paths.reviewDirectory,
          "additional_batch_v2_preparation.json",
        );
        await this.#runStep({
          label: "prepare additional batch v2",
          executable: python,
          args: this.#additionalBatchArgs(targets, additionalOut),
          logPath,
        });
        const additionalResult = await readJsonOptional(additionalOut);
        if (
          !additionalResult ||
          !["additional_review_batch_ready", "already_prepared"].includes(
            additionalResult.status,
          )
        ) {
          throw new Error("Additional batch v2 tidak berhasil disiapkan");
        }
        await this.#finish({
          state: "blocked",
          step: "additional_batch_v2_ready",
          message: "Kelas masih kurang; additional_batch_v2 sudah disiapkan untuk direview.",
          shortfalls: prepareResult.shortfalls || {},
          additional_batch: additionalResult,
          package_created: false,
        });
        return;
      }
      if (prepareResult.status !== "final_dataset_prepared") {
        throw new Error(`Pipeline prepare berhenti dengan status '${prepareResult.status}'`);
      }
      if (prepare.code !== 0) {
        throw new Error("Pipeline prepare gagal");
      }

      this.status.step = "automated_checks";
      this.status.message = "Menjalankan test dataset, Ruff, notebook, dan preflight.";
      await this.#persist();
      await this.#runStep({
        label: "dataset pytest",
        executable: python,
        args: ["-m", "pytest", "ml_pipeline/tests", "-q"],
        logPath,
      });
      await this.#runStep({
        label: "Ruff lint",
        executable: python,
        args: ["-m", "ruff", "check", "ml_pipeline", "inference_api"],
        logPath,
      });
      await this.#runStep({
        label: "Ruff format check",
        executable: python,
        args: ["-m", "ruff", "format", "--check", "ml_pipeline", "inference_api"],
        logPath,
      });
      await this.#runStep({
        label: "notebook validation",
        executable: process.execPath,
        args: ["ml_pipeline/scripts/validate_notebooks.mjs"],
        logPath,
      });
      await this.#runStep({
        label: "preflight",
        executable: process.execPath,
        args: ["ml_pipeline/scripts/preflight_check.mjs"],
        logPath,
      });

      this.status.step = "metadata_validation";
      this.status.message = "Memvalidasi metadata dan isolasi split.";
      await this.#persist();
      const validateOut = path.join(this.paths.reviewDirectory, "finalization_validate_result.json");
      await this.#runStep({
        label: "dataset validate",
        executable: python,
        args: this.#pipelineArgs("validate", validateOut),
        logPath,
      });
      const validationResult = await readJsonOptional(validateOut);
      if (!validationResult?.valid) {
        throw new Error("Validasi metadata final gagal");
      }
      this.status.metadata_validation = validationResult;

      this.status.step = "package";
      this.status.message = "Membuat dan memvalidasi paket dataset final.";
      await this.#persist();
      const packageOut = path.join(this.paths.reviewDirectory, "finalization_package_result.json");
      await this.#runStep({
        label: "dataset package",
        executable: python,
        args: [...this.#pipelineArgs("package", packageOut), "--tests-passed"],
        logPath,
      });
      const packageResult = await readJsonOptional(packageOut);
      if (!packageResult?.zip || !packageResult?.sha256) {
        throw new Error("Pipeline package tidak menghasilkan artefak yang valid");
      }
      const actualHash = await sha256File(packageResult.zip);
      if (actualHash !== packageResult.sha256) {
        throw new Error("Checksum ZIP sesudah finalisasi tidak cocok");
      }
      await this.#finish({
        state: "completed",
        step: "complete",
        message: "Dataset final, metadata, dan paket ZIP berhasil divalidasi.",
        package_created: true,
        package_result: packageResult,
      });
    } catch (error) {
      await this.#finish({
        state: "failed",
        step: "failed",
        message: error instanceof Error ? error.message : String(error),
        package_created: false,
      });
    }
  }

  async #runStep({ label, executable, args, logPath }) {
    this.status.current_command = label;
    await this.#persist();
    const result = await this.runner({
      executable,
      args,
      cwd: this.paths.repoRoot,
      logPath,
    });
    this.status.commands.push(commandSummary(label, result));
    this.status.current_command = null;
    await this.#persist();
    if (result.code !== 0) {
      const detail = String(result.stderr || result.stdout || "").trim().slice(-1200);
      throw new Error(`${label} gagal (exit ${result.code})${detail ? `: ${detail}` : ""}`);
    }
    return result;
  }

  #pipelineArgs(command, jsonOut) {
    return [
      "-m",
      "ml_pipeline.src.dataset.cli",
      command,
      "--config",
      this.paths.configPath,
      "--all-classes",
      "--json-out",
      jsonOut,
    ];
  }

  #additionalBatchArgs(targets, jsonOut) {
    return [
      "-m",
      "ml_pipeline.src.dataset.additional_candidates",
      "--config",
      this.paths.configPath,
      "--sources-config",
      path.join(this.paths.repoRoot, "ml_pipeline", "configs", "additional_public_sources.yaml"),
      "--review-batch",
      "additional_batch_v2",
      "--class-targets-json",
      JSON.stringify(targets),
      "--json-out",
      jsonOut,
    ];
  }

  async #pythonExecutable() {
    const candidates = [
      path.join(this.paths.repoRoot, ".venv", "Scripts", "python.exe"),
      path.join(this.paths.repoRoot, ".venv", "bin", "python"),
    ];
    for (const candidate of candidates) {
      try {
        await fsp.access(candidate);
        return candidate;
      } catch {
        // Try the next verified repository-local interpreter.
      }
    }
    throw new Error("Python .venv repository tidak ditemukan; finalisasi tidak dijalankan");
  }

  async #finish(fields) {
    this.status = {
      ...this.status,
      ...fields,
      current_command: null,
      finished_at: this.now().toISOString(),
      training_started: false,
    };
    await this.#persist();
  }

  async #persist() {
    await atomicWriteJson(this.paths.finalizationStatusJson, this.status);
  }
}

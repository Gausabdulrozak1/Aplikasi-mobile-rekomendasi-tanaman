import fs from "node:fs/promises";
import path from "node:path";

import { atomicWriteFile, atomicWriteJson } from "./atomic.mjs";
import { readCsvFile, serializeCsv } from "./csv.mjs";
import { ConflictError, ValidationError } from "./errors.mjs";
import {
  decodeReviewerNotes,
  encodeReviewerNotes,
  normalizeReasons,
  REJECTION_REASONS,
} from "./review-notes.mjs";
import { buildProgress, validateReviewDataset } from "./validator.mjs";

function clean(value) {
  return String(value ?? "").trim();
}

function normalizedPath(value) {
  return path.resolve(clean(value)).toLowerCase();
}

function isPathInside(candidate, parent) {
  const relative = path.relative(path.resolve(parent), path.resolve(candidate));
  return relative === "" || (!relative.startsWith("..") && !path.isAbsolute(relative));
}

function safeTimestamp(date) {
  return date.toISOString().replace(/[-:]/g, "").replace("T", "_").replace("Z", "Z");
}

async function readJsonOptional(filePath) {
  try {
    return JSON.parse(await fs.readFile(filePath, "utf8"));
  } catch (error) {
    if (error?.code === "ENOENT" || error instanceof SyntaxError) {
      return null;
    }
    throw error;
  }
}

function duplicateIndex(rows) {
  const index = new Map();
  const pathFields = ["canonical_path", "duplicate_path", "left_path", "right_path"];
  for (const row of rows) {
    for (const field of pathFields) {
      if (!clean(row[field])) {
        continue;
      }
      const key = normalizedPath(row[field]);
      if (!index.has(key)) {
        index.set(key, []);
      }
      index.get(key).push(row);
    }
  }
  return index;
}

export class ReviewStore {
  constructor({ paths, requiredTotal = null, now = () => new Date() }) {
    this.paths = paths;
    this.requiredTotal = requiredTotal;
    this.now = now;
    this.backupCreated = false;
    this.mutationQueue = Promise.resolve();
  }

  async initialize() {
    await fs.mkdir(this.paths.backupsDirectory, { recursive: true });
    const loaded = await this.#load();
    await this.#writeProgress(
      loaded.validation,
      loaded.lastReviewedFile,
      loaded.progress?.review_status === "complete" && loaded.validation.can_finalize
        ? "complete"
        : undefined,
    );
    return this.#stateFromLoaded(loaded);
  }

  async getState() {
    return this.#stateFromLoaded(await this.#load());
  }

  async validate() {
    const loaded = await this.#load();
    return loaded.validation;
  }

  async getProgress() {
    const loaded = await this.#load();
    return buildProgress(loaded.validation, {
      lastReviewedFile: loaded.lastReviewedFile,
      updatedAt: loaded.progress?.updated_at || this.now().toISOString(),
      reviewStatus:
        loaded.progress?.review_status === "complete" && loaded.validation.can_finalize
          ? "complete"
          : undefined,
    });
  }

  async updateReview(curatedFileName, payload) {
    return this.#exclusive(async () => {
      const loaded = await this.#load();
      const name = clean(curatedFileName);
      const row = loaded.rows.find((candidate) => clean(candidate.curated_file_name) === name);
      if (!row) {
        throw new ValidationError("Kandidat tidak ditemukan", "CANDIDATE_NOT_FOUND", { name });
      }

      const currentNotes = decodeReviewerNotes(row.reviewer_notes);
      const accepted = clean(payload?.accepted ?? row.accepted).toLowerCase();
      if (!["", "yes", "no", "unsure"].includes(accepted)) {
        throw new ValidationError(
          "Nilai accepted harus yes, no, unsure, atau kosong",
          "INVALID_ACCEPTED",
        );
      }
      const note = clean(payload?.note ?? currentNotes.note);
      if (note.length > 2000) {
        throw new ValidationError("Catatan maksimal 2000 karakter", "NOTE_TOO_LONG");
      }
      let rejectionReasons;
      try {
        rejectionReasons =
          payload?.rejection_reasons === undefined
            ? currentNotes.rejection_reasons
            : normalizeReasons(payload.rejection_reasons);
      } catch (error) {
        throw new ValidationError(
          error instanceof Error ? error.message : "Alasan penolakan tidak valid",
          "INVALID_REJECTION_REASON",
        );
      }

      row.accepted = accepted;
      row.reviewer_notes = encodeReviewerNotes({ accepted, rejectionReasons, note });
      await this.createBackup();

      const csvContent = serializeCsv(loaded.headers, loaded.rows);
      await atomicWriteFile(this.paths.manualReviewCsv, csvContent, {
        validate: async (tempPath) => {
          const parsed = await readCsvFile(tempPath);
          const result = validateReviewDataset({
            rows: parsed.rows,
            expectedRows: loaded.expectedRows,
            imagePaths: loaded.imagePaths,
            requiredTotal: this.requiredTotal,
          });
          if (!result.valid) {
            throw new ValidationError(
              "CSV hasil autosave gagal divalidasi",
              "AUTOSAVE_VALIDATION_FAILED",
              result.errors,
            );
          }
        },
      });

      const refreshed = await this.#load({ lastReviewedFile: name });
      const progress = await this.#writeProgress(refreshed.validation, name);
      const candidate = refreshed.candidates.find(
        (item) => item.curated_file_name === name,
      );
      return { candidate, progress, validation: refreshed.validation };
    });
  }

  async createBackup({ force = false, label = "" } = {}) {
    if (this.backupCreated && !force) {
      return null;
    }
    const original = await fs.readFile(this.paths.manualReviewCsv);
    const timestamp = safeTimestamp(this.now());
    const suffix = label ? `_${clean(label).replace(/[^a-z0-9_-]/gi, "_")}` : "";
    let backupPath = path.join(
      this.paths.backupsDirectory,
      `manual_review_template_${timestamp}${suffix}.csv`,
    );
    let counter = 1;
    while (true) {
      try {
        await fs.access(backupPath);
        backupPath = path.join(
          this.paths.backupsDirectory,
          `manual_review_template_${timestamp}${suffix}_${counter}.csv`,
        );
        counter += 1;
      } catch (error) {
        if (error?.code === "ENOENT") {
          break;
        }
        throw error;
      }
    }
    await atomicWriteFile(backupPath, original, {
      validate: async (tempPath) => readCsvFile(tempPath),
    });
    this.backupCreated = true;
    return backupPath;
  }

  async markReviewComplete() {
    return this.#exclusive(async () => {
      const loaded = await this.#load();
      if (!loaded.validation.can_finalize) {
        throw new ConflictError(
          "Review belum memenuhi syarat finalisasi",
          "FINALIZATION_GATE_BLOCKED",
          loaded.validation,
        );
      }
      return this.#writeProgress(
        loaded.validation,
        loaded.lastReviewedFile,
        "complete",
      );
    });
  }

  async getCsvContent() {
    return fs.readFile(this.paths.manualReviewCsv, "utf8");
  }

  async getImagePath(curatedFileName) {
    const loaded = await this.#load();
    const imagePath = loaded.imagePaths.get(clean(curatedFileName));
    if (!imagePath || !isPathInside(imagePath, this.paths.candidatesDirectory)) {
      return null;
    }
    return imagePath;
  }

  async #load({ lastReviewedFile } = {}) {
    const [manual, mapping, semantic, inventory, exact, near, crossClass, progress] =
      await Promise.all([
        readCsvFile(this.paths.manualReviewCsv),
        readCsvFile(this.paths.mappingCsv),
        readCsvFile(this.paths.semanticCsv, { optional: true }),
        readCsvFile(this.paths.inventoryCsv, { optional: true }),
        readCsvFile(this.paths.exactDuplicatesCsv, { optional: true }),
        readCsvFile(this.paths.nearDuplicatesCsv, { optional: true }),
        readCsvFile(this.paths.crossClassDuplicatesCsv, { optional: true }),
        readJsonOptional(this.paths.progressJson),
      ]);

    const expectedRows = mapping.rows;
    const mappingByName = new Map(
      expectedRows.map((row) => [clean(row.curated_file_name || row.new_file_name), row]),
    );
    const semanticByName = new Map(
      semantic.rows.map((row) => [clean(row.curated_file_name), row]),
    );
    const inventoryByPath = new Map(
      inventory.rows
        .filter((row) => clean(row.original_path))
        .map((row) => [normalizedPath(row.original_path), row]),
    );
    const inventoryBySha = new Map(
      inventory.rows.filter((row) => clean(row.sha256)).map((row) => [clean(row.sha256), row]),
    );
    const exactByPath = duplicateIndex(exact.rows);
    const nearByPath = duplicateIndex(near.rows);
    const crossClassByPath = duplicateIndex(crossClass.rows);
    const imagePaths = new Map();

    for (const [name, expected] of mappingByName) {
      const imagePath = path.join(this.paths.candidatesDirectory, clean(expected.class_id), name);
      if (path.basename(imagePath) === name && isPathInside(imagePath, this.paths.candidatesDirectory)) {
        imagePaths.set(name, imagePath);
      }
    }

    const validation = validateReviewDataset({
      rows: manual.rows,
      expectedRows,
      imagePaths,
      requiredTotal: this.requiredTotal,
    });
    const candidates = manual.rows.map((row, index) => {
      const name = clean(row.curated_file_name);
      const expected = mappingByName.get(name) || {};
      const semanticRow = semanticByName.get(name) || {};
      const originalPath = clean(row.original_path || expected.original_path);
      const inventoryRow =
        inventoryByPath.get(normalizedPath(originalPath)) ||
        inventoryBySha.get(clean(row.sha256 || expected.sha256)) ||
        {};
      const decodedNotes = decodeReviewerNotes(row.reviewer_notes);
      const classId = clean(row.class_id);
      const sourceType = clean(row.source_type);
      const reviewBatch = clean(row.review_batch || expected.review_batch) || "original_350";
      return {
        sequence: index + 1,
        curated_file_name: name,
        original_file_name: clean(row.original_file_name),
        class_id: classId,
        review_batch: reviewBatch,
        source_type: sourceType,
        source_label:
          classId === "padi" && sourceType === "local_aikmel" ? "LOCAL AIKMEL" : "PUBLIC",
        width: Number(row.width || expected.width || inventoryRow.width || 0),
        height: Number(row.height || expected.height || inventoryRow.height || 0),
        source_name: clean(expected.source_name || inventoryRow.source_name),
        source_identifier: clean(expected.source_identifier || inventoryRow.source_identifier),
        source_url: clean(expected.source_url || inventoryRow.source_url),
        license: clean(expected.license || inventoryRow.license),
        file_size: Number(expected.file_size || inventoryRow.file_size || 0),
        technical_status: clean(expected.technical_status || inventoryRow.technical_status),
        accepted: clean(row.accepted).toLowerCase(),
        reviewer_notes: decodedNotes.note,
        rejection_reasons: decodedNotes.rejection_reasons,
        duplicate_group: clean(row.duplicate_group || expected.duplicate_group),
        duplicate_warning: clean(row.duplicate_warning || expected.duplicate_warning),
        duplicate_checks: {
          exact: exactByPath.get(normalizedPath(originalPath)) || [],
          near: nearByPath.get(normalizedPath(originalPath)) || [],
          cross_class: crossClassByPath.get(normalizedPath(originalPath)) || [],
        },
        semantic: {
          screening_status: clean(semanticRow.screening_status) || "not_available",
          confidence: clean(semanticRow.semantic_class_confidence),
          proxy_flags: clean(semanticRow.proxy_flags),
          plant_visible_proxy: clean(semanticRow.plant_visible_proxy),
          growing_environment_proxy: clean(semanticRow.growing_environment_proxy),
          too_close_up_proxy: clean(semanticRow.too_close_up_proxy),
          blur_proxy: clean(semanticRow.blur_proxy),
          watermark_proxy: clean(semanticRow.watermark_proxy),
          method: clean(semanticRow.method),
        },
        image_url: `/api/images/${encodeURIComponent(name)}`,
      };
    });

    return {
      headers: manual.headers,
      rows: manual.rows,
      expectedRows,
      imagePaths,
      validation,
      candidates,
      progress,
      lastReviewedFile:
        lastReviewedFile ||
        (candidates.some((item) => item.curated_file_name === progress?.last_reviewed_file)
          ? progress.last_reviewed_file
          : null),
    };
  }

  #stateFromLoaded(loaded) {
    return {
      candidates: loaded.candidates,
      progress: buildProgress(loaded.validation, {
        lastReviewedFile: loaded.lastReviewedFile,
        updatedAt: loaded.progress?.updated_at || this.now().toISOString(),
        reviewStatus:
          loaded.progress?.review_status === "complete" && loaded.validation.can_finalize
            ? "complete"
            : undefined,
      }),
      validation: loaded.validation,
      options: { rejection_reasons: REJECTION_REASONS },
    };
  }

  async #writeProgress(validation, lastReviewedFile, reviewStatus) {
    const progress = buildProgress(validation, {
      lastReviewedFile,
      updatedAt: this.now().toISOString(),
      reviewStatus,
    });
    await atomicWriteJson(this.paths.progressJson, progress);
    return progress;
  }

  #exclusive(operation) {
    const result = this.mutationQueue.then(operation, operation);
    this.mutationQueue = result.catch(() => undefined);
    return result;
  }
}

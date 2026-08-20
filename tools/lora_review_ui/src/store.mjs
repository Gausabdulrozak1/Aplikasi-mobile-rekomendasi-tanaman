import fs from "node:fs/promises";
import path from "node:path";

import { atomicWriteFile, atomicWriteJson } from "../../dataset_review_ui/src/atomic.mjs";
import { parseCsv, serializeCsv } from "../../dataset_review_ui/src/csv.mjs";
import {
  ConflictError,
  ReviewUiError,
  ValidationError,
} from "../../dataset_review_ui/src/errors.mjs";

export const REVIEW_HEADERS = [
  "condition_id",
  "variant",
  "class_id",
  "prompt",
  "seed",
  "expected_image_path",
  "crop_correct",
  "field_context_quality",
  "visual_realism_score",
  "class_confusion",
  "reviewer_role",
  "reviewer_notes",
];

const CLASS_IDS = ["padi", "jagung", "cabai", "kacang_tanah"];
const VARIANTS = ["base", "lora"];
const CONFUSION_VALUES = new Set(["none", ...CLASS_IDS, "mixed", "unclear"]);
const REQUIRED_ASSESSMENT_FIELDS = [
  "crop_correct",
  "field_context_quality",
  "visual_realism_score",
  "class_confusion",
  "reviewer_role",
];
const ASSESSMENT_FIELDS = [...REQUIRED_ASSESSMENT_FIELDS, "reviewer_notes"];

function rowKey(conditionId, variant) {
  return `${conditionId}\u0000${variant}`;
}

function isComplete(row) {
  return REQUIRED_ASSESSMENT_FIELDS.every((field) => String(row[field] || "").trim());
}

function isStarted(row) {
  return ASSESSMENT_FIELDS.some((field) => String(row[field] || "").trim());
}

function median(values) {
  const ordered = [...values].sort((left, right) => left - right);
  const middle = Math.floor(ordered.length / 2);
  return ordered.length % 2
    ? ordered[middle]
    : (ordered[middle - 1] + ordered[middle]) / 2;
}

function validateScore(value, field) {
  const number = Number(value);
  if (!Number.isInteger(number) || number < 1 || number > 5) {
    throw new ValidationError(`${field} harus berupa angka 1 sampai 5`, "INVALID_SCORE");
  }
  return String(number);
}

function sanitizeAssessment(payload) {
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
    throw new ValidationError("Payload penilaian tidak valid", "INVALID_REVIEW_PAYLOAD");
  }
  const allowed = new Set(ASSESSMENT_FIELDS);
  const unknown = Object.keys(payload).filter((field) => !allowed.has(field));
  if (unknown.length) {
    throw new ValidationError("Kolom penilaian tidak dikenal", "UNKNOWN_REVIEW_FIELDS", unknown);
  }
  if (typeof payload.crop_correct !== "boolean") {
    throw new ValidationError("crop_correct harus dipilih", "CROP_CORRECT_REQUIRED");
  }
  const confusion = String(payload.class_confusion || "").trim().toLowerCase();
  if (!CONFUSION_VALUES.has(confusion)) {
    throw new ValidationError("Nilai class_confusion tidak valid", "INVALID_CONFUSION");
  }
  const reviewerRole = String(payload.reviewer_role || "").trim();
  if (reviewerRole.length < 2 || reviewerRole.length > 100) {
    throw new ValidationError("Peran reviewer harus terdiri dari 2-100 karakter", "INVALID_ROLE");
  }
  const notes = String(payload.reviewer_notes || "").trim();
  if (notes.length > 2000) {
    throw new ValidationError("Catatan reviewer melebihi 2000 karakter", "NOTES_TOO_LONG");
  }
  return {
    crop_correct: String(payload.crop_correct),
    field_context_quality: validateScore(
      payload.field_context_quality,
      "Kualitas konteks lahan",
    ),
    visual_realism_score: validateScore(payload.visual_realism_score, "Realisme visual"),
    class_confusion: confusion,
    reviewer_role: reviewerRole,
    reviewer_notes: notes,
  };
}

function assessmentForClient(row) {
  return {
    crop_correct:
      row.crop_correct === "true" ? true : row.crop_correct === "false" ? false : null,
    field_context_quality: row.field_context_quality
      ? Number(row.field_context_quality)
      : null,
    visual_realism_score: row.visual_realism_score
      ? Number(row.visual_realism_score)
      : null,
    class_confusion: row.class_confusion || "",
    reviewer_role: row.reviewer_role || "",
    reviewer_notes: row.reviewer_notes || "",
    complete: isComplete(row),
  };
}

export class LoraReviewStore {
  constructor({ paths, expectedRows = 72 } = {}) {
    this.paths = paths;
    this.expectedRows = expectedRows;
    this.headers = [];
    this.rows = [];
    this.writeQueue = Promise.resolve();
    this.backupSequence = 0;
  }

  async initialize() {
    await this.#reload();
    const validation = await this.validate();
    if (!validation.schema_valid) {
      throw new ReviewUiError(
        "CSV review LoRA tidak memenuhi kontrak",
        500,
        "INVALID_REVIEW_SOURCE",
        validation.errors,
      );
    }
    await this.#writeProgress(validation);
  }

  async #reload() {
    let source;
    try {
      source = await fs.readFile(this.paths.reviewCsv, "utf8");
    } catch (error) {
      if (error?.code === "ENOENT") {
        throw new ReviewUiError(
          `CSV review tidak ditemukan: ${this.paths.reviewCsv}`,
          500,
          "REVIEW_CSV_NOT_FOUND",
        );
      }
      throw error;
    }
    const parsed = parseCsv(source);
    this.headers = parsed.headers;
    this.rows = parsed.rows;
  }

  async #validateImagePath(rawPath) {
    const relative = path.normalize(String(rawPath || ""));
    if (!relative || path.isAbsolute(relative) || relative.split(path.sep).includes("..")) {
      return { valid: false, path: null };
    }
    const resolved = path.resolve(this.paths.runDirectory, relative);
    const relativeToRun = path.relative(this.paths.runDirectory, resolved);
    if (relativeToRun.startsWith("..") || path.isAbsolute(relativeToRun)) {
      return { valid: false, path: null };
    }
    try {
      const stat = await fs.stat(resolved);
      if (!stat.isFile() || stat.size <= 8 || path.extname(resolved).toLowerCase() !== ".png") {
        return { valid: false, path: resolved };
      }
      const handle = await fs.open(resolved, "r");
      try {
        const signature = Buffer.alloc(8);
        await handle.read(signature, 0, 8, 0);
        return {
          valid: signature.equals(Buffer.from([137, 80, 78, 71, 13, 10, 26, 10])),
          path: resolved,
        };
      } finally {
        await handle.close();
      }
    } catch {
      return { valid: false, path: resolved };
    }
  }

  async validate() {
    const errors = [];
    if (JSON.stringify(this.headers) !== JSON.stringify(REVIEW_HEADERS)) {
      errors.push("Header CSV review tidak cocok dengan kontrak final");
    }
    if (this.rows.length !== this.expectedRows) {
      errors.push(`Jumlah baris ${this.rows.length}; seharusnya ${this.expectedRows}`);
    }
    const keys = new Set();
    const conditions = new Map();
    let completedRows = 0;
    let partialRows = 0;
    let validImageRows = 0;

    for (const [index, row] of this.rows.entries()) {
      const rowNumber = index + 2;
      if (!row.condition_id || !VARIANTS.includes(row.variant) || !CLASS_IDS.includes(row.class_id)) {
        errors.push(`Baris ${rowNumber}: identitas kondisi, variant, atau kelas tidak valid`);
      }
      const key = rowKey(row.condition_id, row.variant);
      if (keys.has(key)) errors.push(`Baris ${rowNumber}: kondisi/variant duplikat`);
      keys.add(key);
      const variants = conditions.get(row.condition_id) || new Set();
      variants.add(row.variant);
      conditions.set(row.condition_id, variants);

      const image = await this.#validateImagePath(row.expected_image_path);
      if (image.valid) validImageRows += 1;
      else errors.push(`Baris ${rowNumber}: path atau PNG evaluasi tidak valid`);

      if (isComplete(row)) {
        completedRows += 1;
        try {
          sanitizeAssessment({
            crop_correct: row.crop_correct === "true" ? true : row.crop_correct === "false" ? false : null,
            field_context_quality: row.field_context_quality,
            visual_realism_score: row.visual_realism_score,
            class_confusion: row.class_confusion,
            reviewer_role: row.reviewer_role,
            reviewer_notes: row.reviewer_notes,
          });
        } catch (error) {
          errors.push(`Baris ${rowNumber}: ${error.message}`);
        }
      } else if (isStarted(row)) {
        partialRows += 1;
        errors.push(`Baris ${rowNumber}: penilaian terisi sebagian`);
      }
    }
    for (const [conditionId, variants] of conditions) {
      if (variants.size !== 2 || !VARIANTS.every((variant) => variants.has(variant))) {
        errors.push(`Kondisi ${conditionId} tidak memiliki pasangan base dan LoRA lengkap`);
      }
    }
    const completedConditions = [...conditions].filter(([conditionId]) =>
      VARIANTS.every((variant) => {
        const row = this.rows.find(
          (candidate) => candidate.condition_id === conditionId && candidate.variant === variant,
        );
        return row && isComplete(row);
      }),
    ).length;
    const schemaValid = errors.length === 0 || errors.every((error) => error.includes("terisi sebagian"));
    const complete =
      errors.length === 0 && completedRows === this.expectedRows && partialRows === 0;
    return {
      valid: errors.length === 0,
      schema_valid: schemaValid,
      complete,
      errors,
      total_rows: this.rows.length,
      completed_rows: completedRows,
      pending_rows: this.rows.length - completedRows,
      partial_rows: partialRows,
      valid_image_rows: validImageRows,
      total_conditions: conditions.size,
      completed_conditions: completedConditions,
    };
  }

  #buildSummary() {
    const completed = this.rows.filter(isComplete);
    const groups = new Map();
    for (const row of completed) {
      for (const classId of [row.class_id, "all"]) {
        const key = `${row.variant}:${classId}`;
        const group = groups.get(key) || [];
        group.push(row);
        groups.set(key, group);
      }
    }
    return [...groups]
      .sort(([left], [right]) => left.localeCompare(right))
      .map(([key, rows]) => {
        const [variant, classId] = key.split(":");
        const correct = rows.filter((row) => row.crop_correct === "true").length;
        return {
          variant,
          class_id: classId,
          reviewed: rows.length,
          crop_correct_count: correct,
          crop_correct_percent: Number(((100 * correct) / rows.length).toFixed(2)),
          field_context_quality_median: median(
            rows.map((row) => Number(row.field_context_quality)),
          ),
          visual_realism_score_median: median(
            rows.map((row) => Number(row.visual_realism_score)),
          ),
          confusion_count: rows.filter(
            (row) => !["none", row.class_id].includes(row.class_confusion),
          ).length,
          target_confirmation_count: rows.filter(
            (row) => row.class_confusion === row.class_id,
          ).length,
        };
      });
  }

  async getState() {
    const validation = await this.validate();
    const grouped = new Map();
    for (const row of this.rows) {
      const condition = grouped.get(row.condition_id) || {
        condition_id: row.condition_id,
        class_id: row.class_id,
        prompt: row.prompt,
        seed: Number(row.seed),
        prompt_index: Number(row.condition_id.match(/_p(\d+)_/)?.[1] || 0),
        variants: {},
      };
      condition.variants[row.variant] = {
        variant: row.variant,
        image_url: `/api/images/${row.variant}/${encodeURIComponent(
          path.basename(row.expected_image_path),
        )}`,
        assessment: assessmentForClient(row),
      };
      grouped.set(row.condition_id, condition);
    }
    const conditions = [...grouped.values()]
      .sort(
        (left, right) =>
          CLASS_IDS.indexOf(left.class_id) - CLASS_IDS.indexOf(right.class_id) ||
          left.prompt_index - right.prompt_index ||
          left.seed - right.seed,
      )
      .map((condition, index) => ({
        ...condition,
        sequence: index + 1,
        complete: VARIANTS.every(
          (variant) => condition.variants[variant]?.assessment.complete,
        ),
      }));
    return {
      run_id: this.paths.runId,
      conditions,
      validation,
      summary: this.#buildSummary(),
    };
  }

  async getCsvContent() {
    return serializeCsv(this.headers, this.rows);
  }

  async getImagePath(variant, fileName) {
    if (!VARIANTS.includes(variant) || fileName !== path.basename(fileName)) return null;
    const row = this.rows.find(
      (candidate) =>
        candidate.variant === variant && path.basename(candidate.expected_image_path) === fileName,
    );
    if (!row) return null;
    const image = await this.#validateImagePath(row.expected_image_path);
    return image.valid ? image.path : null;
  }

  async #backupCurrent() {
    await fs.mkdir(this.paths.backupsDirectory, { recursive: true });
    this.backupSequence += 1;
    const timestamp = new Date().toISOString().replaceAll(":", "-").replaceAll(".", "-");
    const target = path.join(
      this.paths.backupsDirectory,
      `human_review_${timestamp}_${String(this.backupSequence).padStart(3, "0")}.csv`,
    );
    await fs.copyFile(this.paths.reviewCsv, target);
    return target;
  }

  async #writeRows(rows) {
    const content = serializeCsv(this.headers, rows);
    await atomicWriteFile(this.paths.reviewCsv, content, {
      validate: async (temporary) => {
        const parsed = parseCsv(await fs.readFile(temporary, "utf8"));
        if (parsed.rows.length !== this.expectedRows) {
          throw new Error("Atomic CSV validation failed");
        }
      },
    });
    this.rows = rows;
    await Promise.all([
      fs.rm(this.paths.completionJson, { force: true }),
      fs.rm(this.paths.completionMarkdown, { force: true }),
      fs.rm(this.paths.analysisJson, { force: true }),
      fs.rm(this.paths.analysisCsv, { force: true }),
      fs.rm(this.paths.analysisMarkdown, { force: true }),
    ]);
    const validation = await this.validate();
    await this.#writeProgress(validation);
    return validation;
  }

  async #writeProgress(validation) {
    await atomicWriteJson(this.paths.progressJson, {
      schema_version: 1,
      run_id: this.paths.runId,
      updated_at: new Date().toISOString(),
      ...validation,
    });
  }

  #enqueue(operation) {
    const result = this.writeQueue.then(operation, operation);
    this.writeQueue = result.catch(() => undefined);
    return result;
  }

  async updateReview(conditionId, variant, payload) {
    return this.#enqueue(async () => {
      const index = this.rows.findIndex(
        (row) => row.condition_id === conditionId && row.variant === variant,
      );
      if (index < 0) {
        throw new ReviewUiError("Baris review tidak ditemukan", 404, "REVIEW_NOT_FOUND");
      }
      const assessment = sanitizeAssessment(payload);
      const nextRows = this.rows.map((row, rowIndex) =>
        rowIndex === index ? { ...row, ...assessment } : row,
      );
      const backupPath = await this.#backupCurrent();
      const validation = await this.#writeRows(nextRows);
      return {
        row: {
          condition_id: conditionId,
          variant,
          assessment: assessmentForClient(nextRows[index]),
        },
        validation,
        backup: path.basename(backupPath),
      };
    });
  }

  async clearReview(conditionId, variant) {
    return this.#enqueue(async () => {
      const index = this.rows.findIndex(
        (row) => row.condition_id === conditionId && row.variant === variant,
      );
      if (index < 0) {
        throw new ReviewUiError("Baris review tidak ditemukan", 404, "REVIEW_NOT_FOUND");
      }
      const nextRows = this.rows.map((row, rowIndex) => {
        if (rowIndex !== index) return row;
        return {
          ...row,
          ...Object.fromEntries(ASSESSMENT_FIELDS.map((field) => [field, ""])),
        };
      });
      const backupPath = await this.#backupCurrent();
      const validation = await this.#writeRows(nextRows);
      return { validation, backup: path.basename(backupPath) };
    });
  }

  async finalize() {
    return this.#enqueue(async () => {
      const validation = await this.validate();
      if (!validation.complete) {
        throw new ConflictError(
          "Review belum lengkap atau masih mengandung nilai tidak valid",
          "HUMAN_REVIEW_INCOMPLETE",
          validation,
        );
      }
      const summary = this.#buildSummary();
      const reviewerRoles = [
        ...new Set(this.rows.map((row) => row.reviewer_role.trim()).filter(Boolean)),
      ].sort();
      const report = {
        schema_version: 1,
        run_id: this.paths.runId,
        status: "complete",
        completed_at: new Date().toISOString(),
        validation,
        summary,
        automated_metrics_are_proxy: true,
        automated_scores_inserted: false,
        human_review_source: "reviewer_entered_local_ui",
        reviewer_roles: reviewerRoles,
      };
      await atomicWriteJson(this.paths.completionJson, report);
      const lines = [
        `# Human LoRA Review - ${this.paths.runId}`,
        "",
        `- Status: \`${report.status}\``,
        `- Completed rows: ${validation.completed_rows}/${validation.total_rows}`,
        `- Completed at: ${report.completed_at}`,
        `- Review source: \`${report.human_review_source}\``,
        `- Reviewer roles: ${reviewerRoles.join(", ")}`,
        "",
        "| Variant | Class | Reviewed | Crop correct | Context median | Realism median | Confusion |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
        ...summary.map(
          (row) =>
            `| ${row.variant} | ${row.class_id} | ${row.reviewed} | ` +
            `${row.crop_correct_percent}% | ${row.field_context_quality_median} | ` +
            `${row.visual_realism_score_median} | ${row.confusion_count} |`,
        ),
        "",
        "This report contains human-entered rubric results. Automated proxy metrics remain separate.",
      ];
      await atomicWriteFile(this.paths.completionMarkdown, `${lines.join("\n")}\n`);
      return report;
    });
  }
}

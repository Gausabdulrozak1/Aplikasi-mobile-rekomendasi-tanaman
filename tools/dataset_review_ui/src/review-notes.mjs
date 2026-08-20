export const REJECTION_REASONS = Object.freeze([
  "wrong_crop",
  "no_plant_visible",
  "harvested_product_only",
  "food_image",
  "market_image",
  "too_close_up",
  "blurry",
  "watermark",
  "severe_occlusion",
  "excessive_near_duplicate",
  "suspected_ai_generated",
  "low_resolution",
  "unrelated_image",
  "other",
]);

const REJECTION_REASON_SET = new Set(REJECTION_REASONS);

export function normalizeReasons(values) {
  if (!Array.isArray(values)) {
    return [];
  }
  const unique = [];
  for (const value of values) {
    const normalized = String(value).trim().toLowerCase();
    if (!REJECTION_REASON_SET.has(normalized)) {
      throw new Error(`Unsupported rejection reason: ${normalized || "(empty)"}`);
    }
    if (!unique.includes(normalized)) {
      unique.push(normalized);
    }
  }
  return unique;
}

export function encodeReviewerNotes({ accepted, rejectionReasons = [], note = "" }) {
  const cleanNote = String(note).trim();
  if (accepted !== "no") {
    return cleanNote;
  }
  return JSON.stringify({
    rejection_reasons: normalizeReasons(rejectionReasons),
    note: cleanNote,
  });
}

export function decodeReviewerNotes(value) {
  const text = String(value || "").trim();
  if (!text.startsWith("{")) {
    return { rejection_reasons: [], note: text };
  }
  try {
    const parsed = JSON.parse(text);
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
      return { rejection_reasons: [], note: text };
    }
    return {
      rejection_reasons: normalizeReasons(parsed.rejection_reasons || []),
      note: String(parsed.note || ""),
    };
  } catch {
    return { rejection_reasons: [], note: text };
  }
}

export function hasRecordedRejectionReason(row) {
  if (String(row.rejection_reason || "").trim()) {
    return true;
  }
  const decoded = decodeReviewerNotes(row.reviewer_notes);
  return decoded.rejection_reasons.length > 0 || decoded.note.trim().length > 0;
}

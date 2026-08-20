const elements = Object.fromEntries(
  [
    "reviewed-count",
    "progress-label",
    "progress-bar",
    "finalize-button",
    "batch-filter",
    "class-filter",
    "source-filter",
    "proxy-filter",
    "status-filter",
    "jump-form",
    "jump-input",
    "filtered-count",
    "batch-summary",
    "reset-filter-button",
    "candidate-list",
    "loading-state",
    "empty-state",
    "review-content",
    "sequence-label",
    "curated-name",
    "candidate-badges",
    "candidate-image",
    "image-error",
    "previous-button",
    "next-button",
    "save-state",
    "metadata-grid",
    "rejection-reasons",
    "reviewer-notes",
    "reject-button",
    "unsure-button",
    "accept-button",
    "save-button",
    "finalization-panel",
    "finalization-title",
    "finalization-message",
    "finalization-state",
    "toast",
  ].map((id) => [id, document.getElementById(id)]),
);

const reasonLabels = {
  wrong_crop: "Komoditas salah",
  no_plant_visible: "Tanaman tidak terlihat",
  harvested_product_only: "Hanya hasil panen",
  food_image: "Gambar makanan",
  market_image: "Gambar pasar",
  too_close_up: "Terlalu close-up",
  blurry: "Buram",
  watermark: "Watermark",
  severe_occlusion: "Tertutup berat",
  excessive_near_duplicate: "Near duplicate berlebih",
  suspected_ai_generated: "Diduga buatan AI",
  low_resolution: "Resolusi rendah",
  unrelated_image: "Tidak berkaitan",
  other: "Lainnya",
};

let reviewState = null;
let filteredCandidates = [];
let currentName = null;
let draft = { note: "", rejectionReasons: [] };
let saving = false;
let dirty = false;
let toastTimer = null;
let finalizationTimer = null;

function statusLabel(value) {
  return { yes: "Diterima", no: "Ditolak", unsure: "Ragu", "": "Belum diperiksa" }[
    value || ""
  ];
}

function classLabel(value) {
  return {
    padi: "Padi",
    jagung: "Jagung",
    cabai: "Cabai",
    kacang_tanah: "Kacang tanah",
  }[value] || value;
}

function proxyLabel(value) {
  return {
    proxy_pass: "Proxy pass",
    proxy_review: "Proxy review",
    not_available: "Tidak tersedia",
  }[value] || value;
}

function batchLabel(value) {
  if (value === "original_350") return "Original 350";
  const match = /^additional_batch_v([0-9]+)$/.exec(value || "");
  return match ? `Additional batch v${match[1]}` : value;
}

function formatBytes(value) {
  const bytes = Number(value || 0);
  if (!bytes) return "Tidak tersedia";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 ** 2) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 ** 2).toFixed(2)} MB`;
}

function currentCandidate() {
  return reviewState?.candidates.find((candidate) => candidate.curated_file_name === currentName);
}

function showToast(message, isError = false) {
  clearTimeout(toastTimer);
  elements.toast.textContent = message;
  elements.toast.classList.toggle("error", isError);
  elements.toast.hidden = false;
  toastTimer = setTimeout(() => {
    elements.toast.hidden = true;
  }, 3200);
}

async function apiRequest(url, options = {}) {
  const response = await fetch(url, options);
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error(data?.error?.message || `Request gagal (${response.status})`);
  }
  return data;
}

function createBadge(text, classes = []) {
  const badge = document.createElement("span");
  badge.className = ["badge", ...classes].join(" ");
  badge.textContent = text;
  return badge;
}

function createMetadataItem(label, value) {
  const wrapper = document.createElement("div");
  wrapper.className = "metadata-item";
  const term = document.createElement("dt");
  const description = document.createElement("dd");
  term.textContent = label;
  description.textContent = value || "Tidak tersedia";
  wrapper.append(term, description);
  return wrapper;
}

function buildReasonControls(reasons) {
  elements["rejection-reasons"].replaceChildren();
  for (const reason of reasons) {
    const label = document.createElement("label");
    label.className = "reason-option";
    const input = document.createElement("input");
    input.type = "checkbox";
    input.value = reason;
    input.addEventListener("change", () => {
      draft.rejectionReasons = [...elements["rejection-reasons"].querySelectorAll("input:checked")].map(
        (item) => item.value,
      );
      setDirty(true);
    });
    const text = document.createElement("span");
    text.textContent = reasonLabels[reason] || reason;
    label.append(input, text);
    elements["rejection-reasons"].append(label);
  }
}

function setDirty(value) {
  dirty = value;
  elements["save-state"].textContent = value ? "Perubahan belum disimpan" : "Tersimpan";
  elements["save-state"].classList.toggle("dirty", value);
}

function hydrateDraft(candidate) {
  draft = {
    note: candidate?.reviewer_notes || "",
    rejectionReasons: [...(candidate?.rejection_reasons || [])],
  };
  elements["reviewer-notes"].value = draft.note;
  for (const input of elements["rejection-reasons"].querySelectorAll("input")) {
    input.checked = draft.rejectionReasons.includes(input.value);
  }
  setDirty(false);
}

function matchesFilters(candidate) {
  const batchFilter = elements["batch-filter"].value;
  const classFilter = elements["class-filter"].value;
  const sourceFilter = elements["source-filter"].value;
  const proxyFilter = elements["proxy-filter"].value;
  const statusFilter = elements["status-filter"].value;
  return (
    (batchFilter === "all" || candidate.review_batch === batchFilter) &&
    (classFilter === "all" || candidate.class_id === classFilter) &&
    (sourceFilter === "all" || candidate.source_type === sourceFilter) &&
    (proxyFilter === "all" || candidate.semantic.screening_status === proxyFilter) &&
    (statusFilter === "all" ||
      (statusFilter === "pending" ? !candidate.accepted : candidate.accepted === statusFilter))
  );
}

function applyFilters({ preserveCurrent = true } = {}) {
  filteredCandidates = reviewState.candidates.filter(matchesFilters);
  if (!preserveCurrent || !filteredCandidates.some((item) => item.curated_file_name === currentName)) {
    currentName = filteredCandidates[0]?.curated_file_name || null;
  }
  elements["filtered-count"].textContent = `${filteredCandidates.length} kandidat`;
  renderCandidateList();
  renderCurrent();
}

function renderCandidateList() {
  elements["candidate-list"].replaceChildren();
  const fragment = document.createDocumentFragment();
  for (const candidate of filteredCandidates) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `candidate-row${candidate.curated_file_name === currentName ? " active" : ""}`;
    button.dataset.name = candidate.curated_file_name;
    button.addEventListener("click", () => selectCandidate(candidate.curated_file_name));

    const number = document.createElement("span");
    number.className = "candidate-number";
    number.textContent = candidate.sequence;
    const copy = document.createElement("span");
    copy.className = "candidate-copy";
    const name = document.createElement("strong");
    name.textContent = candidate.curated_file_name;
    const detail = document.createElement("span");
    detail.textContent = `${classLabel(candidate.class_id)} | ${candidate.source_label}`;
    copy.append(name, detail);
    const dot = document.createElement("span");
    dot.className = `decision-dot ${candidate.accepted || "pending"}`;
    dot.title = statusLabel(candidate.accepted);
    button.append(number, copy, dot);
    fragment.append(button);
  }
  elements["candidate-list"].append(fragment);
}

function renderProgress() {
  const progress = reviewState.progress;
  const completed = progress.accepted_yes + progress.accepted_no;
  const percentage = progress.total_candidates
    ? (completed / progress.total_candidates) * 100
    : 0;
  elements["reviewed-count"].textContent = `${completed} / ${progress.total_candidates}`;
  const original = progress.counts_per_batch?.original_350 || { reviewed: 0, total: 0 };
  const additional = Object.entries(progress.counts_per_batch || {})
    .filter(([batch]) => batch !== "original_350")
    .reduce(
      (total, [, count]) => ({ reviewed: total.reviewed + count.reviewed, total: total.total + count.total }),
      { reviewed: 0, total: 0 },
    );
  elements["progress-label"].textContent = `Original ${original.reviewed}/${original.total} | Additional ${additional.reviewed}/${additional.total}`;
  const additionalCandidates = reviewState.candidates.filter(
    (candidate) => candidate.review_batch !== "original_350",
  );
  const counts = Object.fromEntries(
    ["jagung", "cabai", "kacang_tanah"].map((classId) => [
      classId,
      additionalCandidates.filter((candidate) => candidate.class_id === classId).length,
    ]),
  );
  elements["batch-summary"].textContent = additionalCandidates.length
    ? `Additional ${additionalCandidates.length} | Jagung ${counts.jagung} | Cabai ${counts.cabai} | Kacang tanah ${counts.kacang_tanah}`
    : "";
  elements["progress-bar"].style.width = `${percentage}%`;
  elements["finalize-button"].disabled =
    !reviewState.validation.can_finalize || reviewState.finalization?.state === "running";
}

function renderCurrent() {
  const candidate = currentCandidate();
  elements["loading-state"].hidden = true;
  elements["empty-state"].hidden = Boolean(candidate);
  elements["review-content"].hidden = !candidate;
  if (!candidate) return;

  elements["sequence-label"].textContent = `${candidate.sequence} dari ${reviewState.candidates.length}`;
  elements["curated-name"].textContent = candidate.curated_file_name;
  elements["candidate-badges"].replaceChildren(
    createBadge(classLabel(candidate.class_id)),
    createBadge(batchLabel(candidate.review_batch)),
    createBadge(candidate.source_label, [
      candidate.source_label === "LOCAL AIKMEL" ? "source-local" : "source-public",
    ]),
    createBadge(proxyLabel(candidate.semantic.screening_status)),
    createBadge(statusLabel(candidate.accepted), [`status-${candidate.accepted || "pending"}`]),
  );

  elements["image-error"].hidden = true;
  elements["candidate-image"].src = candidate.image_url;
  elements["candidate-image"].alt = `${classLabel(candidate.class_id)}: ${candidate.curated_file_name}`;

  const duplicate = candidate.duplicate_checks;
  const exactWarning = duplicate.exact.length
    ? `${duplicate.exact.length} peringatan`
    : candidate.duplicate_warning || "Tidak ada";
  const metadata = [
    ["Nama asli", candidate.original_file_name],
    ["Kelas", classLabel(candidate.class_id)],
    ["Sumber", candidate.source_label],
    ["Dataset sumber", candidate.source_name],
    ["Identifier sumber", candidate.source_identifier],
    ["Lisensi", candidate.license],
    ["URL sumber", candidate.source_url],
    ["Batch review", batchLabel(candidate.review_batch)],
    ["Resolusi", `${candidate.width} x ${candidate.height} px`],
    ["Ukuran file", formatBytes(candidate.file_size)],
    ["Screening otomatis", proxyLabel(candidate.semantic.screening_status)],
    ["Confidence proxy", candidate.semantic.confidence || "Tidak tersedia"],
    ["Proxy flags", candidate.semantic.proxy_flags || "Tidak ada"],
    ["Exact duplicate", exactWarning],
    ["Near duplicate", duplicate.near.length ? `${duplicate.near.length} peringatan` : "Tidak ada"],
    [
      "Cross-class duplicate",
      duplicate.cross_class.length ? `${duplicate.cross_class.length} peringatan` : "Tidak ada",
    ],
    ["Validasi teknis", candidate.technical_status || "Tidak tersedia"],
  ];
  elements["metadata-grid"].replaceChildren(
    ...metadata.map(([label, value]) => createMetadataItem(label, value)),
  );
  hydrateDraft(candidate);

  const position = filteredCandidates.findIndex(
    (item) => item.curated_file_name === candidate.curated_file_name,
  );
  elements["previous-button"].disabled = position <= 0;
  elements["next-button"].disabled = position < 0 || position >= filteredCandidates.length - 1;
  requestAnimationFrame(() => {
    document
      .querySelector(`.candidate-row[data-name="${CSS.escape(candidate.curated_file_name)}"]`)
      ?.scrollIntoView({ block: "nearest", inline: "nearest" });
  });
}

function selectCandidate(name) {
  currentName = name;
  renderCandidateList();
  renderCurrent();
}

function navigate(offset) {
  const index = filteredCandidates.findIndex((item) => item.curated_file_name === currentName);
  const target = filteredCandidates[index + offset];
  if (target) selectCandidate(target.curated_file_name);
}

async function saveCurrent(accepted, advance) {
  const candidate = currentCandidate();
  if (!candidate || saving) return;
  const previousSequence = candidate.sequence;
  saving = true;
  setControlsDisabled(true);
  elements["save-state"].textContent = "Menyimpan...";
  try {
    const result = await apiRequest(`/api/reviews/${encodeURIComponent(candidate.curated_file_name)}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json", "X-Review-UI": "1" },
      body: JSON.stringify({
        accepted: accepted ?? candidate.accepted,
        note: elements["reviewer-notes"].value,
        rejection_reasons: draft.rejectionReasons,
      }),
    });
    const index = reviewState.candidates.findIndex(
      (item) => item.curated_file_name === result.candidate.curated_file_name,
    );
    reviewState.candidates[index] = result.candidate;
    reviewState.progress = result.progress;
    reviewState.validation = result.validation;
    renderProgress();
    filteredCandidates = reviewState.candidates.filter(matchesFilters);
    if (advance) {
      const next = filteredCandidates.find((item) => item.sequence > previousSequence);
      currentName = next?.curated_file_name || filteredCandidates.at(-1)?.curated_file_name || currentName;
    }
    renderCandidateList();
    renderCurrent();
    showToast(`${result.candidate.curated_file_name}: ${statusLabel(result.candidate.accepted)}`);
  } catch (error) {
    elements["save-state"].textContent = "Gagal menyimpan";
    elements["save-state"].classList.add("dirty");
    showToast(error.message, true);
  } finally {
    saving = false;
    setControlsDisabled(false);
  }
}

function setControlsDisabled(value) {
  for (const element of [
    elements["reject-button"],
    elements["unsure-button"],
    elements["accept-button"],
    elements["save-button"],
  ]) {
    element.disabled = value;
  }
}

function renderFinalization(status) {
  reviewState.finalization = status;
  const visible = status && status.state !== "idle";
  elements["finalization-panel"].hidden = !visible;
  if (!visible) return;
  elements["finalization-title"].textContent =
    status.state === "completed" ? "Finalisasi selesai" : "Finalisasi dataset";
  elements["finalization-message"].textContent = status.message || status.step;
  elements["finalization-state"].textContent = status.state;
  renderProgress();
  if (status.state === "running" && !finalizationTimer) {
    finalizationTimer = setInterval(refreshFinalization, 2000);
  } else if (status.state !== "running" && finalizationTimer) {
    clearInterval(finalizationTimer);
    finalizationTimer = null;
  }
}

async function refreshFinalization() {
  try {
    renderFinalization(await apiRequest("/api/finalization"));
  } catch (error) {
    showToast(error.message, true);
  }
}

async function finalizeReview() {
  if (!reviewState.validation.can_finalize) return;
  const confirmed = window.confirm(
    "Finalisasi akan memvalidasi ulang review, membuat backup, lalu menjalankan pipeline dataset. Lanjutkan?",
  );
  if (!confirmed) return;
  elements["finalize-button"].disabled = true;
  try {
    const status = await apiRequest("/api/finalize", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Review-UI": "1" },
      body: "{}",
    });
    renderFinalization(status);
    showToast("Finalisasi dimulai. Halaman ini dapat tetap terbuka.");
  } catch (error) {
    showToast(error.message, true);
    renderProgress();
  }
}

function resetFilters() {
  elements["batch-filter"].value = "all";
  elements["class-filter"].value = "all";
  elements["source-filter"].value = "all";
  elements["proxy-filter"].value = "all";
  elements["status-filter"].value = "all";
  applyFilters();
}

function bindEvents() {
  for (const id of [
    "batch-filter",
    "class-filter",
    "source-filter",
    "proxy-filter",
    "status-filter",
  ]) {
    elements[id].addEventListener("change", () => applyFilters());
  }
  elements["reset-filter-button"].addEventListener("click", resetFilters);
  elements["previous-button"].addEventListener("click", () => navigate(-1));
  elements["next-button"].addEventListener("click", () => navigate(1));
  elements["accept-button"].addEventListener("click", () => saveCurrent("yes", true));
  elements["reject-button"].addEventListener("click", () => saveCurrent("no", true));
  elements["unsure-button"].addEventListener("click", () => saveCurrent("unsure", true));
  elements["save-button"].addEventListener("click", () => saveCurrent(undefined, false));
  elements["finalize-button"].addEventListener("click", finalizeReview);
  elements["reviewer-notes"].addEventListener("input", () => {
    draft.note = elements["reviewer-notes"].value;
    setDirty(true);
  });
  elements["candidate-image"].addEventListener("error", () => {
    elements["image-error"].hidden = false;
  });
  elements["candidate-image"].addEventListener("load", () => {
    elements["image-error"].hidden = true;
  });
  elements["jump-form"].addEventListener("submit", (event) => {
    event.preventDefault();
    const sequence = Number(elements["jump-input"].value);
    const target = reviewState.candidates.find((candidate) => candidate.sequence === sequence);
    if (!target) {
      showToast("Nomor kandidat tidak ditemukan", true);
      return;
    }
    resetFilters();
    selectCandidate(target.curated_file_name);
  });
  document.addEventListener("keydown", (event) => {
    const tag = event.target?.tagName?.toLowerCase();
    if (["input", "textarea", "select"].includes(tag) || event.ctrlKey || event.metaKey || event.altKey) {
      return;
    }
    const key = event.key.toLowerCase();
    if (key === "y") saveCurrent("yes", true);
    else if (key === "n") saveCurrent("no", true);
    else if (key === "u") saveCurrent("unsure", true);
    else if (key === "arrowright" || key === "j") navigate(1);
    else if (key === "arrowleft" || key === "k") navigate(-1);
    else if (key === "s") saveCurrent(undefined, false);
    else return;
    event.preventDefault();
  });
}

async function initialize() {
  bindEvents();
  try {
    reviewState = await apiRequest("/api/state");
    buildReasonControls(reviewState.options.rejection_reasons);
    const availableAdditionalBatches = reviewState.candidates
      .map((candidate) => candidate.review_batch)
      .filter((batch) => /^additional_batch_v[1-9][0-9]*$/.test(batch));
    const defaultAdditionalBatch = availableAdditionalBatches.sort().at(-1) || null;
    const hasAdditionalBatch = Boolean(defaultAdditionalBatch);
    if (hasAdditionalBatch) {
      elements["batch-filter"].value = defaultAdditionalBatch;
    }
    const resume = reviewState.progress.last_reviewed_file;
    const firstPending = reviewState.candidates.find(
      (candidate) =>
        !candidate.accepted &&
        (!hasAdditionalBatch || candidate.review_batch === defaultAdditionalBatch),
    );
    currentName =
      reviewState.candidates.find(
        (candidate) =>
          candidate.curated_file_name === resume &&
          (!hasAdditionalBatch || candidate.review_batch === defaultAdditionalBatch),
      )
        ?.curated_file_name ||
      firstPending?.curated_file_name ||
      reviewState.candidates[0]?.curated_file_name ||
      null;
    elements["jump-input"].max = reviewState.candidates.length;
    renderProgress();
    applyFilters();
    renderFinalization(reviewState.finalization);
  } catch (error) {
    elements["loading-state"].textContent = `Gagal memuat review: ${error.message}`;
    showToast(error.message, true);
  }
}

initialize();

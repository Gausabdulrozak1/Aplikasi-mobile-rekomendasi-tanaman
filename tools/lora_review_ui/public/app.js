const elements = Object.fromEntries(
  [
    "row-progress",
    "condition-progress",
    "progress-bar",
    "reviewer-role",
    "finalize-button",
    "class-filter",
    "status-filter",
    "filter-count",
    "condition-list",
    "run-id",
    "loading-state",
    "empty-state",
    "review-content",
    "sequence-label",
    "condition-title",
    "prompt-index",
    "seed-label",
    "prompt-text",
    "variant-grid",
    "previous-button",
    "next-button",
    "save-state",
    "variant-template",
    "toast",
  ].map((id) => [id, document.getElementById(id)]),
);

const classLabels = {
  padi: "Padi",
  jagung: "Jagung",
  cabai: "Cabai",
  kacang_tanah: "Kacang tanah",
};

let state = null;
let filteredConditions = [];
let currentConditionId = null;
let classFilter = "all";
let saving = false;
let toastTimer = null;

async function apiRequest(url, options = {}) {
  const response = await fetch(url, options);
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.error?.message || `Permintaan gagal (${response.status})`);
  }
  return payload;
}

function showToast(message, error = false) {
  clearTimeout(toastTimer);
  elements.toast.textContent = message;
  elements.toast.classList.toggle("error", error);
  elements.toast.hidden = false;
  toastTimer = setTimeout(() => {
    elements.toast.hidden = true;
  }, 3200);
}

function selectedStatus() {
  return elements["status-filter"].value;
}

function matchesFilters(condition) {
  if (classFilter !== "all" && condition.class_id !== classFilter) return false;
  const status = selectedStatus();
  if (status === "complete" && !condition.complete) return false;
  if (status === "pending" && condition.complete) return false;
  return true;
}

function currentCondition() {
  return state?.conditions.find((condition) => condition.condition_id === currentConditionId);
}

function renderProgress() {
  const validation = state.validation;
  elements["row-progress"].textContent =
    `${validation.completed_rows} / ${validation.total_rows}`;
  elements["condition-progress"].textContent =
    `${validation.completed_conditions} / ${validation.total_conditions} pasangan`;
  elements["progress-bar"].style.width =
    `${(100 * validation.completed_rows) / validation.total_rows}%`;
  elements["finalize-button"].disabled = !validation.complete || saving;
}

function renderConditionList() {
  elements["condition-list"].replaceChildren(
    ...filteredConditions.map((condition) => {
      const completedVariants = ["base", "lora"].filter(
        (variant) => condition.variants[variant].assessment.complete,
      ).length;
      const button = document.createElement("button");
      button.type = "button";
      button.className = `condition-row${condition.condition_id === currentConditionId ? " active" : ""}`;
      button.dataset.conditionId = condition.condition_id;
      const number = document.createElement("span");
      number.className = "condition-number";
      number.textContent = String(condition.sequence).padStart(2, "0");
      const copy = document.createElement("span");
      copy.className = "condition-copy";
      const title = document.createElement("strong");
      title.textContent = classLabels[condition.class_id];
      const meta = document.createElement("span");
      meta.textContent = `Prompt ${condition.prompt_index} | Seed ${condition.seed}`;
      copy.append(title, meta);
      const status = document.createElement("span");
      status.className = `row-status${completedVariants === 2 ? " complete" : ""}`;
      status.textContent = `${completedVariants}/2`;
      button.append(number, copy, status);
      button.addEventListener("click", () => selectCondition(condition.condition_id));
      return button;
    }),
  );
  elements["filter-count"].textContent = `${filteredConditions.length} pasangan`;
}

function activateButtonGroup(container, value, attribute) {
  for (const button of container.querySelectorAll(`button[${attribute}]`)) {
    button.classList.toggle("active", button.getAttribute(attribute) === String(value));
  }
}

function bindSelectableButtons(container, selector, attribute) {
  for (const button of container.querySelectorAll(selector)) {
    button.addEventListener("click", () => {
      activateButtonGroup(container, button.getAttribute(attribute), attribute);
    });
  }
}

function collectAssessment(panel) {
  const crop = panel.querySelector(".binary-control button.active")?.dataset.value;
  const context = panel.querySelector(
    '[data-field="field_context_quality"] button.active',
  )?.dataset.score;
  const realism = panel.querySelector(
    '[data-field="visual_realism_score"] button.active',
  )?.dataset.score;
  const confusion = panel.querySelector(".confusion-select").value;
  const reviewerRole = elements["reviewer-role"].value.trim();
  if (!crop || !context || !realism || !confusion || reviewerRole.length < 2) {
    throw new Error("Lengkapi komoditas, dua skor, confusion, dan peran reviewer");
  }
  return {
    crop_correct: crop === "true",
    field_context_quality: Number(context),
    visual_realism_score: Number(realism),
    class_confusion: confusion,
    reviewer_role: reviewerRole,
    reviewer_notes: panel.querySelector(".notes-input").value,
  };
}

async function saveVariant(panel, variant) {
  if (saving) return;
  const condition = currentCondition();
  let payload;
  try {
    payload = collectAssessment(panel);
  } catch (error) {
    showToast(error.message, true);
    return;
  }
  saving = true;
  setBusy(true, "Menyimpan...");
  try {
    await apiRequest(
      `/api/reviews/${encodeURIComponent(condition.condition_id)}/${variant}`,
      {
        method: "PATCH",
        headers: { "Content-Type": "application/json", "X-Review-UI": "1" },
        body: JSON.stringify(payload),
      },
    );
    localStorage.setItem("taniadaptif-lora-reviewer-role", payload.reviewer_role);
    await reloadState(condition.condition_id);
    showToast(`${variant === "base" ? "Base" : "LoRA"} tersimpan`);
  } catch (error) {
    showToast(error.message, true);
  } finally {
    saving = false;
    setBusy(false, "Tersimpan");
  }
}

async function clearVariant(variant) {
  if (saving || !window.confirm(`Hapus penilaian ${variant === "base" ? "Base" : "LoRA"}?`)) {
    return;
  }
  const condition = currentCondition();
  saving = true;
  setBusy(true, "Menghapus...");
  try {
    await apiRequest(
      `/api/reviews/${encodeURIComponent(condition.condition_id)}/${variant}`,
      { method: "DELETE", headers: { "X-Review-UI": "1" } },
    );
    await reloadState(condition.condition_id);
    showToast("Penilaian dihapus");
  } catch (error) {
    showToast(error.message, true);
  } finally {
    saving = false;
    setBusy(false, "Siap");
  }
}

function renderVariant(variant, value) {
  const fragment = elements["variant-template"].content.cloneNode(true);
  const panel = fragment.querySelector(".variant-panel");
  panel.dataset.variant = variant;
  panel.querySelector(".variant-label").textContent = variant;
  panel.querySelector(".variant-title").textContent = variant === "base" ? "Base SD 1.5" : "LoRA Multicrop";
  const status = panel.querySelector(".variant-status");
  status.textContent = value.assessment.complete ? "Sudah dinilai" : "Belum dinilai";
  status.classList.toggle("complete", value.assessment.complete);
  const link = panel.querySelector(".image-frame");
  link.href = value.image_url;
  const image = panel.querySelector("img");
  image.src = value.image_url;
  image.alt = `${variant === "base" ? "Base" : "LoRA"} untuk ${classLabels[currentCondition().class_id]}`;
  image.addEventListener("error", () => {
    panel.querySelector(".image-error").hidden = false;
  });
  image.addEventListener("load", () => {
    panel.querySelector(".image-error").hidden = true;
  });

  const assessment = value.assessment;
  if (assessment.crop_correct !== null) {
    activateButtonGroup(panel.querySelector(".binary-control"), assessment.crop_correct, "data-value");
  }
  for (const field of ["field_context_quality", "visual_realism_score"]) {
    if (assessment[field] !== null) {
      activateButtonGroup(
        panel.querySelector(`[data-field="${field}"] .score-control`),
        assessment[field],
        "data-score",
      );
    }
  }
  panel.querySelector(".confusion-select").value = assessment.class_confusion;
  panel.querySelector(".notes-input").value = assessment.reviewer_notes;
  if (!elements["reviewer-role"].value && assessment.reviewer_role) {
    elements["reviewer-role"].value = assessment.reviewer_role;
  }
  bindSelectableButtons(panel, ".binary-control button", "data-value");
  bindSelectableButtons(panel, ".score-control button", "data-score");
  panel.querySelector(".save-button").addEventListener("click", () => saveVariant(panel, variant));
  panel.querySelector(".clear-button").addEventListener("click", () => clearVariant(variant));
  return fragment;
}

function renderCurrent() {
  const condition = currentCondition();
  elements["loading-state"].hidden = true;
  elements["empty-state"].hidden = Boolean(condition);
  elements["review-content"].hidden = !condition;
  if (!condition) return;
  const position = filteredConditions.findIndex(
    (candidate) => candidate.condition_id === condition.condition_id,
  );
  elements["sequence-label"].textContent =
    `${position + 1} dari ${filteredConditions.length}`;
  elements["condition-title"].textContent = classLabels[condition.class_id];
  elements["prompt-index"].textContent = `Prompt ${condition.prompt_index}`;
  elements["seed-label"].textContent = `Seed ${condition.seed}`;
  elements["prompt-text"].textContent = condition.prompt;
  elements["variant-grid"].replaceChildren(
    renderVariant("base", condition.variants.base),
    renderVariant("lora", condition.variants.lora),
  );
  elements["previous-button"].disabled = position <= 0;
  elements["next-button"].disabled = position < 0 || position >= filteredConditions.length - 1;
  requestAnimationFrame(() => {
    document
      .querySelector(
        `.condition-row[data-condition-id="${CSS.escape(condition.condition_id)}"]`,
      )
      ?.scrollIntoView({ block: "nearest", inline: "nearest" });
  });
}

function selectCondition(conditionId) {
  currentConditionId = conditionId;
  renderConditionList();
  renderCurrent();
}

function applyFilters() {
  filteredConditions = state.conditions.filter(matchesFilters);
  if (!filteredConditions.some((condition) => condition.condition_id === currentConditionId)) {
    currentConditionId = filteredConditions[0]?.condition_id || null;
  }
  renderConditionList();
  renderCurrent();
}

function navigate(offset) {
  const index = filteredConditions.findIndex(
    (condition) => condition.condition_id === currentConditionId,
  );
  const target = filteredConditions[index + offset];
  if (target) selectCondition(target.condition_id);
}

function setBusy(value, label) {
  elements["save-state"].textContent = label;
  for (const button of document.querySelectorAll(".save-button, .clear-button")) {
    button.disabled = value;
  }
  renderProgress();
}

async function reloadState(preferredConditionId = currentConditionId) {
  state = await apiRequest("/api/state");
  elements["run-id"].textContent = state.run_id;
  currentConditionId = preferredConditionId;
  renderProgress();
  applyFilters();
}

async function finalizeReview() {
  if (!state.validation.complete || saving) return;
  if (!window.confirm("Validasi dan buat ringkasan 72 penilaian sekarang?")) return;
  saving = true;
  setBusy(true, "Memvalidasi...");
  try {
    const report = await apiRequest("/api/finalize", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Review-UI": "1" },
      body: "{}",
    });
    showToast(`Review ${report.status}: ${report.validation.completed_rows}/72`);
  } catch (error) {
    showToast(error.message, true);
  } finally {
    saving = false;
    setBusy(false, "Siap");
  }
}

function bindEvents() {
  for (const button of elements["class-filter"].querySelectorAll("button[data-class]")) {
    button.addEventListener("click", () => {
      classFilter = button.dataset.class;
      for (const peer of elements["class-filter"].querySelectorAll("button")) {
        peer.classList.toggle("active", peer === button);
      }
      applyFilters();
    });
  }
  elements["status-filter"].addEventListener("change", applyFilters);
  elements["previous-button"].addEventListener("click", () => navigate(-1));
  elements["next-button"].addEventListener("click", () => navigate(1));
  elements["finalize-button"].addEventListener("click", finalizeReview);
  elements["reviewer-role"].addEventListener("change", () => {
    const value = elements["reviewer-role"].value.trim();
    if (value) localStorage.setItem("taniadaptif-lora-reviewer-role", value);
  });
}

async function initialize() {
  bindEvents();
  elements["reviewer-role"].value =
    localStorage.getItem("taniadaptif-lora-reviewer-role") || "";
  try {
    await reloadState();
  } catch (error) {
    elements["loading-state"].textContent = error.message;
    showToast(error.message, true);
  }
}

initialize();

let submissionsGrid;
let editFormInstance;
let activeSubmission = null;

const config = window.submissionsPageConfig || {};
const tableContainer = document.getElementById("submissions-table-data");
const refreshBtn = document.getElementById("refreshSubmissionGridBtn");
const freshnessPanel = document.getElementById("submissionFreshnessPanel");
const editModalNode = document.getElementById("submissionEditModal");
const editSubtitle = document.getElementById("submissionEditSubtitle");
const editAlert = document.getElementById("submissionEditAlert");
const saveBtn = document.getElementById("submissionEditSaveBtn");
const schemaFields = Array.isArray(config.fields) ? config.fields : [];

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function formatDateTime(value, fallback = "-") {
  if (!value) return fallback;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return fallback;
  return new Intl.DateTimeFormat("id-ID", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(date);
}

function formatPayloadValue(value) {
  if (value === null || value === undefined || value === "") return "-";
  if (typeof value === "boolean") return value ? "Ya" : "Tidak";
  if (Array.isArray(value)) return value.join(", ");
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function showEditAlert(message, category = "info") {
  if (!editAlert) return;
  const className = category === "success" ? "alert-success" : category === "danger" ? "alert-danger" : "alert-info";
  editAlert.className = `alert ${className}`;
  editAlert.textContent = message;
}

function hideEditAlert() {
  if (!editAlert) return;
  editAlert.className = "alert d-none";
  editAlert.textContent = "";
}

function detailUrl(submissionId) {
  return String(config.detailUrlTemplate || "").replace("0", submissionId);
}

function updateUrl(submissionId) {
  return String(config.updateUrlTemplate || "").replace("0", submissionId);
}

function buildListUrl() {
  const url = new URL(config.listUrl, window.location.origin);
  if (config.formId) url.searchParams.set("form_id", config.formId);
  return url.toString();
}

function buildFreshnessUrl() {
  const url = new URL(config.freshnessUrl, window.location.origin);
  if (config.formId) url.searchParams.set("form_id", config.formId);
  return url.toString();
}

function renderStatusBadge(status) {
  const normalized = String(status || "submitted").toLowerCase();
  const badgeClass = normalized === "submitted" ? "bg-success-subtle text-success" : "bg-secondary-subtle text-secondary";
  return `<span class="badge ${badgeClass}">${escapeHtml(normalized)}</span>`;
}

function buildRows(data) {
  return (data || []).map((submission) => [
    submission.submission_number,
    submission.status,
    submission.reporting_year,
    submission.submitted_at,
    submission.updated_at,
    ...schemaFields.map((field) => formatPayloadValue((submission.payload || {})[field.key])),
    submission,
  ]);
}

function buildGridColumns() {
  const submissionIndex = 5 + schemaFields.length;
  return [
    { name: "Nomor", width: "170px", formatter: (cell) => gridjs.html(`<code>${escapeHtml(cell)}</code>`) },
    { name: "Status", width: "120px", formatter: (cell) => gridjs.html(renderStatusBadge(cell)) },
    { name: "Tahun", width: "90px" },
    { name: "Submitted At", width: "160px", formatter: (cell) => formatDateTime(cell) },
    { name: "Updated At", width: "160px", formatter: (cell) => formatDateTime(cell) },
    ...schemaFields.map((field) => ({
      name: field.label || field.key,
      formatter: (cell) => gridjs.html(`<span title="${escapeHtml(cell)}">${escapeHtml(cell)}</span>`),
    })),
    {
      name: "Aksi",
      width: "130px",
      sort: false,
      formatter: (_, row) => {
        const submission = row.cells[submissionIndex].data;
        const canEdit = Boolean(submission.permissions && submission.permissions.can_edit);
        return gridjs.html(`
          <button type="button" class="btn btn-soft-primary btn-sm js-edit-submission" data-submission-id="${escapeHtml(submission.id)}" ${canEdit ? "" : "disabled"}>
            <i class="ri-edit-line me-1"></i>Edit
          </button>
        `);
      },
    },
  ];
}

async function loadFreshness() {
  if (!freshnessPanel || !config.formId) return;
  try {
    const response = await fetch(buildFreshnessUrl(), { headers: { Accept: "application/json" } });
    const payload = await response.json();
    const freshness = payload.data || {};
    freshnessPanel.innerHTML = `
      <div class="fw-semibold">${escapeHtml(formatDateTime(freshness.data_last_updated_at, "Belum ada submission"))}</div>
      <div class="text-muted fs-12 mt-1">Source: ${escapeHtml(freshness.source || "submissions.submitted_at")}</div>
    `;
  } catch (error) {
    freshnessPanel.innerHTML = '<div class="text-danger fs-13">Gagal memuat freshness.</div>';
  }
}

function gridServerConfig() {
  return { url: buildListUrl(), then: (result) => buildRows(result.data || result) };
}

function initGrid() {
  if (!tableContainer || !window.gridjs || !config.formId) return;
  submissionsGrid = new gridjs.Grid({
    columns: buildGridColumns(),
    pagination: { limit: 20 },
    sort: true,
    search: true,
    className: { table: "table table-nowrap align-middle" },
    server: gridServerConfig(),
  });
  submissionsGrid.render(tableContainer);
}

async function openEditModal(submissionId) {
  hideEditAlert();
  const response = await fetch(detailUrl(submissionId), { headers: { Accept: "application/json" } });
  const envelope = await response.json();
  if (!response.ok || !envelope.success) {
    showEditAlert(envelope.message || "Gagal memuat submission.", "danger");
    return;
  }

  activeSubmission = envelope.data.submission;
  if (editSubtitle) {
    editSubtitle.textContent = `${activeSubmission.submission_number} · submitted ${formatDateTime(activeSubmission.submitted_at)}`;
  }

  const container = document.getElementById("submissionEditFormio");
  container.innerHTML = "";
  editFormInstance = await Formio.createForm(container, config.schema || { display: "form", components: [] }, {
    readOnly: !(activeSubmission.permissions && activeSubmission.permissions.can_edit),
  });
  editFormInstance.submission = { data: activeSubmission.payload || {} };

  const modal = bootstrap.Modal.getOrCreateInstance(editModalNode);
  modal.show();
}

async function saveActiveSubmission() {
  if (!activeSubmission || !editFormInstance || !saveBtn) return;
  hideEditAlert();
  saveBtn.disabled = true;
  saveBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Menyimpan...';
  try {
    const response = await fetch(updateUrl(activeSubmission.id), {
      method: "PUT",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({ payload: editFormInstance.submission.data || {}, refresh_submitted_at: true }),
    });
    const envelope = await response.json();
    if (!response.ok || !envelope.success) throw new Error(envelope.message || "Gagal menyimpan submission.");
    activeSubmission = envelope.data.submission;
    showEditAlert("Data berhasil diupdate. Freshness submissions.submitted_at sudah bergeser ke waktu update.", "success");
    loadFreshness();
    if (submissionsGrid) submissionsGrid.updateConfig({ server: gridServerConfig() }).forceRender();
  } catch (error) {
    showEditAlert(error.message || "Gagal menyimpan submission.", "danger");
  } finally {
    saveBtn.disabled = !(config.permissions && config.permissions.can_submit);
    saveBtn.innerHTML = "Simpan Perubahan";
  }
}

if (refreshBtn) {
  refreshBtn.addEventListener("click", () => {
    if (submissionsGrid) submissionsGrid.updateConfig({ server: gridServerConfig() }).forceRender();
    loadFreshness();
  });
}

if (tableContainer) {
  tableContainer.addEventListener("click", (event) => {
    const button = event.target.closest(".js-edit-submission");
    if (!button) return;
    openEditModal(button.dataset.submissionId);
  });
}

if (saveBtn) saveBtn.addEventListener("click", saveActiveSubmission);

initGrid();
loadFreshness();

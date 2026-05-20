let formsGrid;

const formsTableContainer = document.getElementById("forms-table-data");

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

function renderStatusBadge(status) {
  const normalized = String(status || "draft").toLowerCase();
  const badgeClass = normalized === "published"
    ? "bg-success-subtle text-success"
    : normalized === "archived"
      ? "bg-secondary-subtle text-secondary"
      : "bg-warning-subtle text-warning";

  return `<span class="badge ${badgeClass}">${escapeHtml(normalized)}</span>`;
}

function renderVisibilityBadge(visibility) {
  const normalized = String(visibility || "internal").toLowerCase();
  const badgeClass = normalized === "public" ? "bg-info-subtle text-info" : "bg-primary-subtle text-primary";
  return `<span class="badge ${badgeClass}">${escapeHtml(normalized)}</span>`;
}

function renderPermissionBadge(label, className) {
  return `<span class="badge ${className}">${escapeHtml(label)}</span>`;
}

function renderPermissionSummary(permissions = {}) {
  const badges = [];

  if (permissions.can_manage) {
    badges.push(renderPermissionBadge("manage", "bg-warning-subtle text-warning"));
  } else if (permissions.can_view) {
    badges.push(renderPermissionBadge("read-only", "bg-secondary-subtle text-secondary"));
  }

  if (permissions.can_submit) {
    badges.push(renderPermissionBadge("submit", "bg-info-subtle text-info"));
  }

  return badges.length
    ? `<div class="d-flex flex-wrap gap-1 mt-2">${badges.join("")}</div>`
    : '<div class="text-muted fs-12 mt-2">Tanpa capability aktif</div>';
}

function builderUrl(formId) {
  return builderUrlTemplate.replace("0", formId);
}

function previewUrl(formId) {
  return previewUrlTemplate.replace("0", formId);
}

function templateUrl(formId) {
  return templateUrlTemplate.replace("0", formId);
}

function importMappingUrl(formId) {
  return importMappingUrlTemplate.replace("0", formId);
}

function buildRows(data) {
  return data.map((form) => [
    form.id,
    form.code,
    form.name,
    form.status,
    form.visibility,
    form.draft_version_number,
    form.published_version_number,
    form.component_count,
    form.updated_at,
    form,
  ]);
}

function initFormsGrid() {
  if (!formsTableContainer) return;

  formsGrid = new gridjs.Grid({
    columns: [
      {
        name: "ID",
        width: "70px",
        formatter: (cell) => gridjs.html(`<span class="fw-semibold">${escapeHtml(cell)}</span>`),
      },
      {
        name: "Kode",
        width: "150px",
        formatter: (cell) => gridjs.html(`<code>${escapeHtml(cell)}</code>`),
      },
      {
        name: "Nama Form",
        formatter: (cell, row) => {
          const form = row.cells[9].data;
          return gridjs.html(`
            <div>
              <div class="fw-semibold">${escapeHtml(cell)}</div>
              <div class="text-muted fs-12">${escapeHtml(form.slug || "-")}</div>
              ${renderPermissionSummary(form.permissions || {})}
            </div>
          `);
        },
      },
      {
        name: "Status",
        width: "120px",
        formatter: (cell) => gridjs.html(renderStatusBadge(cell)),
      },
      {
        name: "Visibility",
        width: "120px",
        formatter: (cell) => gridjs.html(renderVisibilityBadge(cell)),
      },
      {
        name: "Draft",
        width: "90px",
        formatter: (cell) => gridjs.html(cell ? `<span class="badge bg-warning-subtle text-warning">v${escapeHtml(cell)}</span>` : '<span class="text-muted">-</span>'),
      },
      {
        name: "Published",
        width: "110px",
        formatter: (cell) => gridjs.html(cell ? `<span class="badge bg-success-subtle text-success">v${escapeHtml(cell)}</span>` : '<span class="text-muted">-</span>'),
      },
      {
        name: "Komponen",
        width: "110px",
        formatter: (cell) => gridjs.html(`<span class="badge bg-light text-body">${escapeHtml(cell || 0)}</span>`),
      },
      {
        name: "Update",
        width: "150px",
        formatter: (cell) => formatDateTime(cell),
      },
      {
        name: "Aksi",
        width: "230px",
        sort: false,
        formatter: (_, row) => {
          const form = row.cells[9].data;
          const permissions = form.permissions || {};
          const canManage = Boolean(permissions.can_manage);
          const canView = Boolean(permissions.can_view || permissions.can_manage);
          const canSubmit = Boolean(permissions.can_submit);
          const hasPublishedVersion = Boolean(form.published_version_number);
          const previewEnabled = hasPublishedVersion && canView;
          const templateEnabled = hasPublishedVersion && canView;
          const importEnabled = hasPublishedVersion && canView;
          const previewDisabled = previewEnabled ? "" : "disabled";
          const templateDisabled = templateEnabled ? "" : "disabled";
          const importDisabled = importEnabled ? "" : "disabled";
          const builderTitle = canManage ? "Builder / Edit Draft" : "Builder Read-only";
          const importTitle = canSubmit ? "Upload & Mapping Excel" : "Review Mapping Excel (read-only)";
          const previewHref = previewEnabled ? previewUrl(form.id) : "javascript:void(0);";
          const templateHref = templateEnabled ? templateUrl(form.id) : "javascript:void(0);";
          const importHref = importEnabled ? importMappingUrl(form.id) : "javascript:void(0);";

          return gridjs.html(`
            <div class="d-flex gap-2">
              <a class="btn ${canManage ? "btn-soft-warning" : "btn-soft-secondary"} btn-icon btn-sm" href="${builderUrl(form.id)}" title="${builderTitle}">
                <i class="ri-edit-line"></i>
              </a>
              <a class="btn btn-soft-success btn-icon btn-sm ${previewDisabled}" href="${previewHref}" title="Preview / Isi Form" aria-disabled="${previewDisabled ? "true" : "false"}">
                <i class="ri-eye-line"></i>
              </a>
              <a class="btn btn-soft-primary btn-icon btn-sm ${templateDisabled}" href="${templateHref}" title="Download Template Excel" aria-disabled="${templateDisabled ? "true" : "false"}">
                <i class="ri-file-excel-2-line"></i>
              </a>
              <a class="btn btn-soft-info btn-icon btn-sm ${importDisabled}" href="${importHref}" title="${importTitle}" aria-disabled="${importDisabled ? "true" : "false"}">
                <i class="ri-upload-cloud-2-line"></i>
              </a>
            </div>
          `);
        },
      },
    ],
    pagination: {
      limit: 20,
    },
    sort: true,
    search: true,
    className: {
      table: "table table-nowrap align-middle",
    },
    server: {
      url: formsDataUrl,
      then: buildRows,
    },
  });

  formsGrid.render(formsTableContainer);
}

initFormsGrid();

(function () {
  const config = window.submissionCatalogConfig || {};
  const container = document.getElementById("submission-forms-table-data");

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

  function urlFromTemplate(template, id) {
    return String(template || "#").replace("0", id);
  }

  function renderPermissionSummary(permissions = {}) {
    const badges = [];
    if (permissions.can_view) badges.push('<span class="badge bg-secondary-subtle text-secondary me-1">view</span>');
    if (permissions.can_submit) badges.push('<span class="badge bg-info-subtle text-info me-1">submit/edit</span>');
    if (permissions.can_manage) badges.push('<span class="badge bg-warning-subtle text-warning me-1">manage</span>');
    return badges.length ? badges.join("") : '<span class="text-muted fs-12">Tidak ada capability</span>';
  }

  function buildRows(forms) {
    return (forms || []).map((form) => [
      form.code,
      form.name,
      form.published_version_number,
      form.component_count,
      form.updated_at,
      form,
    ]);
  }

  if (!container || !window.gridjs) return;

  new gridjs.Grid({
    columns: [
      { name: "Kode", width: "150px", formatter: (cell) => gridjs.html(`<code>${escapeHtml(cell)}</code>`) },
      {
        name: "Nama Form",
        formatter: (cell, row) => {
          const form = row.cells[5].data;
          return gridjs.html(`
            <div>
              <div class="fw-semibold">${escapeHtml(cell)}</div>
              <div class="text-muted fs-12">${escapeHtml(form.slug || "-")}</div>
              <div class="mt-2">${renderPermissionSummary(form.permissions || {})}</div>
            </div>
          `);
        },
      },
      {
        name: "Published",
        width: "110px",
        formatter: (cell) => gridjs.html(cell ? `<span class="badge bg-success-subtle text-success">v${escapeHtml(cell)}</span>` : '<span class="badge bg-warning-subtle text-warning">Belum</span>'),
      },
      { name: "Field", width: "90px", formatter: (cell) => gridjs.html(`<span class="badge bg-light text-body">${escapeHtml(cell || 0)}</span>`) },
      { name: "Update", width: "160px", formatter: (cell) => formatDateTime(cell) },
      {
        name: "Aksi",
        width: "260px",
        sort: false,
        formatter: (_, row) => {
          const form = row.cells[5].data;
          const hasPublished = Boolean(form.published_version_number);
          const detailHref = urlFromTemplate(config.detailUrlTemplate, form.id);
          const newHref = urlFromTemplate(config.newUrlTemplate, form.id);
          const importHref = urlFromTemplate(config.importUrlTemplate, form.id);
          return gridjs.html(`
            <div class="d-flex flex-wrap gap-2">
              <a class="btn btn-soft-primary btn-sm" href="${detailHref}"><i class="ri-eye-line me-1"></i>Lihat/Detail</a>
              <a class="btn btn-success btn-sm ${hasPublished ? "" : "disabled"}" href="${hasPublished ? newHref : "javascript:void(0);"}" aria-disabled="${hasPublished ? "false" : "true"}"><i class="ri-add-line me-1"></i>+Tambah</a>
              <a class="btn btn-soft-info btn-sm ${hasPublished ? "" : "disabled"}" href="${hasPublished ? importHref : "javascript:void(0);"}" aria-disabled="${hasPublished ? "false" : "true"}"><i class="ri-upload-cloud-2-line me-1"></i>Import</a>
            </div>
          `);
        },
      },
    ],
    data: buildRows(config.forms || []),
    pagination: { limit: 20 },
    sort: true,
    search: true,
    className: { table: "table table-nowrap align-middle" },
  }).render(container);
})();

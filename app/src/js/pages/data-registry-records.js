(function () {
  const rows = Array.isArray(window.recordRowsData) ? window.recordRowsData : [];
  const columns = Array.isArray(window.recordColumnsData) ? window.recordColumnsData : [];
  const editFields = Array.isArray(window.recordEditFieldsData) ? window.recordEditFieldsData : [];
  const meta = window.recordRegistryMeta || {};
  const gridContainer = document.getElementById("registry-records-grid");

  if (!gridContainer || !window.gridjs) {
    return;
  }

  const searchInput = document.getElementById("recordSearchInput");
  const statusFilter = document.getElementById("recordStatusFilter");
  const levelFilter = document.getElementById("recordLevelFilter");
  const resetButton = document.getElementById("recordFilterReset");
  const editModalElement = document.getElementById("recordEditModal");
  const editForm = document.getElementById("recordEditForm");
  const editKeyInput = document.getElementById("recordEditKey");
  const payloadPreview = document.getElementById("recordPayloadPreview");
  const toggleForm = document.getElementById("recordToggleForm");
  const toggleActiveInput = document.getElementById("recordToggleActiveInput");

  const editModal = editModalElement ? new bootstrap.Modal(editModalElement) : null;
  let currentRows = rows.slice();
  let gridInstance = null;

  function normalizeText(value) {
    return String(value == null ? "" : value).toLowerCase();
  }

  function buildSearchBlob(row) {
    const payloadValues = Object.values(row.column_values || {}).join(" ");
    return normalizeText([
      row.record_key,
      row.record_code,
      row.label,
      row.admin_level,
      payloadValues,
      JSON.stringify(row.payload || {}),
    ].join(" "));
  }

  function filterRows() {
    const search = normalizeText(searchInput ? searchInput.value : "");
    const status = statusFilter ? statusFilter.value : "all";
    const level = levelFilter ? levelFilter.value : "all";

    return rows.filter((row) => {
      if (status === "active" && !row.is_active) return false;
      if (status === "inactive" && row.is_active) return false;
      if (level !== "all" && String(row.admin_level || "") !== level) return false;
      if (search && !buildSearchBlob(row).includes(search)) return false;
      return true;
    });
  }

  function badgeHtml(active) {
    return active
      ? '<span class="badge bg-success-subtle text-success">aktif</span>'
      : '<span class="badge bg-secondary-subtle text-secondary">nonaktif</span>';
  }

  function escapeHtml(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/\"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function openEditModal(rowId) {
    const row = rows.find((item) => Number(item.id) === Number(rowId));
    if (!row || !editForm || !editModal) {
      return;
    }

    editForm.action = String(meta.updateUrlTemplate || "").replace("/0/update", `/${row.id}/update`);
    if (editKeyInput) {
      editKeyInput.value = row.record_key || "";
    }
    editFields.forEach((field) => {
      const input = editForm.querySelector(`[name="${field.key}"]`);
      if (!input) return;
      const value = (row.column_values || {})[field.key] ?? (row.payload || {})[field.key] ?? row[field.key] ?? "";
      input.value = value == null ? "" : value;
    });
    if (payloadPreview) {
      payloadPreview.textContent = JSON.stringify(row.payload || {}, null, 2);
    }
    editModal.show();
  }

  function submitToggle(rowId, nextActive) {
    if (!toggleForm || !toggleActiveInput) {
      return;
    }
    toggleForm.action = String(meta.toggleActiveUrlTemplate || "").replace("/0/toggle-active", `/${rowId}/toggle-active`);
    toggleActiveInput.value = nextActive ? "true" : "false";
    toggleForm.submit();
  }

  function buildGridData(dataRows) {
    return dataRows.map((row) => {
      const payloadCells = columns.map((column) => escapeHtml((row.column_values || {})[column.key] || "-"));
      const actionButtons = `
        <div class="d-flex gap-2 justify-content-end">
          <button type="button" class="btn btn-sm btn-soft-primary" data-record-action="edit" data-record-id="${row.id}">Edit</button>
          <button type="button" class="btn btn-sm ${row.is_active ? "btn-soft-warning" : "btn-soft-success"}" data-record-action="toggle" data-record-id="${row.id}" data-next-active="${row.is_active ? "false" : "true"}">
            ${row.is_active ? "Nonaktifkan" : "Aktifkan"}
          </button>
        </div>
      `;

      return [
        gridjs.html(`<code>${escapeHtml(row.record_key || "-")}</code>`),
        ...payloadCells.map((cell) => gridjs.html(cell)),
        gridjs.html(escapeHtml(row.admin_level || "-")),
        gridjs.html(badgeHtml(row.is_active)),
        gridjs.html(escapeHtml(row.updated_at || "-")),
        gridjs.html(actionButtons),
      ];
    });
  }

  function buildGridColumns() {
    return [
      { name: "Record Key" },
      ...columns.map((column) => ({ name: column.label })),
      { name: "Level" },
      { name: "Status" },
      { name: "Updated At" },
      { name: "Aksi", sort: false },
    ];
  }

  function renderGrid() {
    currentRows = filterRows();
    if (gridInstance) {
      gridInstance.destroy();
    }
    gridContainer.innerHTML = "";
    gridInstance = new gridjs.Grid({
      columns: buildGridColumns(),
      data: buildGridData(currentRows),
      sort: true,
      search: false,
      pagination: { enabled: true, limit: 10, summary: true },
      language: {
        search: { placeholder: "Search dalam tabel..." },
        pagination: {
          previous: "Sebelumnya",
          next: "Berikutnya",
          showing: "Menampilkan",
          results: () => "record",
        },
        noRecordsFound: "Tidak ada record yang cocok.",
      },
      className: {
        table: "table table-hover align-middle",
      },
    }).render(gridContainer);
  }

  gridContainer.addEventListener("click", function (event) {
    const trigger = event.target.closest("[data-record-action]");
    if (!trigger) return;

    const action = trigger.getAttribute("data-record-action");
    const recordId = trigger.getAttribute("data-record-id");
    if (action === "edit") {
      openEditModal(recordId);
      return;
    }
    if (action === "toggle") {
      const nextActive = trigger.getAttribute("data-next-active") === "true";
      submitToggle(recordId, nextActive);
    }
  });

  [searchInput, statusFilter, levelFilter].forEach((element) => {
    if (!element) return;
    element.addEventListener("input", renderGrid);
    element.addEventListener("change", renderGrid);
  });

  if (resetButton) {
    resetButton.addEventListener("click", function () {
      if (searchInput) searchInput.value = "";
      if (statusFilter) statusFilter.value = "all";
      if (levelFilter) levelFilter.value = "all";
      renderGrid();
    });
  }

  renderGrid();
})();

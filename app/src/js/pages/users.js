let grid;

const tableContainer = document.getElementById("table-data");
const userForm = document.getElementById("userForm");
const userModalElement = document.getElementById("userModal");
const viewModalElement = document.getElementById("viewModal");
const userModal = userModalElement ? new bootstrap.Modal(userModalElement) : null;
const viewModal = viewModalElement ? new bootstrap.Modal(viewModalElement) : null;
const submitUserBtn = document.getElementById("submitUserBtn");
const submitUserLabel = submitUserBtn?.querySelector(".label");
const addRecordBtn = document.getElementById("addRecordBtn");

const formState = {
  mode: "create",
  userId: null,
};

function getCsrfToken() {
  return document.querySelector('input[name="csrf_token"]')?.value || "";
}

function showToast(message, type = "success") {
  Toastify({
    text: message,
    duration: 5000,
    close: true,
    gravity: "top",
    position: "right",
    stopOnFocus: true,
    className: type === "success" ? "bg-success" : "bg-danger",
    style: {
      background: type === "success" ? "#34c38f" : "#f46a6a",
    },
  }).showToast();
}

function parseJsonList(value) {
  if (!value) return [];
  if (Array.isArray(value)) return value.filter(Boolean);

  try {
    const parsed = JSON.parse(value);
    return Array.isArray(parsed) ? parsed.filter(Boolean) : [];
  } catch (error) {
    return String(value)
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean);
  }
}

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

function renderBadgeList(items, badgeClass = "bg-primary-subtle text-primary") {
  if (!items.length) {
    return '<span class="text-muted">-</span>';
  }

  return items
    .map(
      (item) =>
        `<span class="badge ${badgeClass} me-1 mb-1">${escapeHtml(item)}</span>`
    )
    .join("");
}

function setButtonLoading(isLoading) {
  if (!submitUserBtn || !submitUserLabel) return;

  submitUserBtn.disabled = isLoading;
  submitUserLabel.textContent = isLoading
    ? "Menyimpan..."
    : formState.mode === "create"
      ? "Simpan"
      : "Update";
}

function getTagEditor(fieldId) {
  return document.querySelector(`[data-tag-editor][data-target="${fieldId}"]`);
}

function clearFieldError(fieldId) {
  const field = document.getElementById(fieldId);
  if (!field) return;

  field.classList.remove("is-invalid");
  const tagEditor = getTagEditor(fieldId);
  tagEditor?.classList.remove("border-danger");
}

function markFieldError(fieldId) {
  const field = document.getElementById(fieldId);
  if (!field) return;

  field.classList.add("is-invalid");
  const tagEditor = getTagEditor(fieldId);
  if (tagEditor) {
    tagEditor.classList.add("border-danger");
  }
}

function clearFormErrors() {
  ["username", "email", "password", "confirm_password", "roles", "permissions"].forEach(clearFieldError);
}

function inferFieldFromMessage(message) {
  const normalized = String(message || "").toLowerCase();

  if (normalized.includes("nip") || normalized.includes("username")) return "username";
  if (normalized.includes("email")) return "email";
  if (normalized.includes("konfirmasi password")) return "confirm_password";
  if (normalized.includes("password")) return "password";
  if (normalized.includes("role")) return "roles";
  if (normalized.includes("permission")) return "permissions";
  return null;
}

function refreshGrid() {
  if (!grid) return;
  grid.forceRender();
}

function buildRows(data) {
  return data.map((user) => [
    user.id,
    user.username,
    user.email,
    user.active,
    user.roles || [],
    user.permissions || [],
    null,
  ]);
}

function setupTagEditors() {
  document.querySelectorAll("[data-tag-editor]").forEach((editor) => {
    const targetId = editor.dataset.target;
    const hiddenInput = document.getElementById(targetId);
    const visualList = editor.querySelector(".tag-editor-list");
    const textInput = editor.querySelector(".tag-editor-input");

    if (!hiddenInput || !visualList || !textInput) return;

    const normalize = (items) => {
      const result = [];
      const seen = new Set();

      items
        .map((item) => String(item || "").trim())
        .filter(Boolean)
        .forEach((item) => {
          const key = item.toLowerCase();
          if (seen.has(key)) return;
          seen.add(key);
          result.push(item);
        });

      return result;
    };

    const getValues = () => normalize(parseJsonList(hiddenInput.value));

    const syncValue = (items) => {
      hiddenInput.value = normalize(items).join(", ");
      hiddenInput.dispatchEvent(new Event("change", { bubbles: true }));
    };

    const render = () => {
      const items = getValues();
      visualList.innerHTML = items
        .map(
          (item) => `
            <span class="tag-editor-pill">
              <span>${escapeHtml(item)}</span>
              <button type="button" data-tag-remove="${escapeHtml(item)}" aria-label="Hapus ${escapeHtml(item)}">
                <i class="ri-close-line"></i>
              </button>
            </span>
          `
        )
        .join("");
    };

    const addTags = (rawValue) => {
      const incoming = String(rawValue || "")
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean);

      if (!incoming.length) return;

      syncValue([...getValues(), ...incoming]);
      textInput.value = "";
      clearFieldError(targetId);
      render();
    };

    textInput.addEventListener("keydown", (event) => {
      if (["Enter", ","].includes(event.key)) {
        event.preventDefault();
        addTags(textInput.value);
      }

      if (event.key === "Backspace" && !textInput.value) {
        const values = getValues();
        values.pop();
        syncValue(values);
        render();
      }
    });

    textInput.addEventListener("blur", () => {
      if (textInput.value.trim()) {
        addTags(textInput.value);
      }
    });

    visualList.addEventListener("click", (event) => {
      const button = event.target.closest("[data-tag-remove]");
      if (!button) return;

      const tagToRemove = button.dataset.tagRemove?.toLowerCase();
      const filtered = getValues().filter((item) => item.toLowerCase() !== tagToRemove);
      syncValue(filtered);
      render();
    });

    hiddenInput.addEventListener("change", render);
    render();
  });
}

function resetUserForm() {
  userForm.reset();
  clearFormErrors();

  document.getElementById("userId").value = "";
  document.getElementById("username").readOnly = false;
  document.getElementById("username").classList.remove("bg-light");
  document.getElementById("active").checked = true;
  document.getElementById("roles").value = "";
  document.getElementById("permissions").value = "";
  document.getElementById("roles").dispatchEvent(new Event("change", { bubbles: true }));
  document.getElementById("permissions").dispatchEvent(new Event("change", { bubbles: true }));
}

function configureModal(mode, user = null) {
  const isEdit = mode === "edit";
  formState.mode = mode;
  formState.userId = user?.id || null;

  document.getElementById("userModalLabel").textContent = isEdit
    ? `Edit User: ${user.username}`
    : "Tambah User";
  document.getElementById("userModalDescription").textContent = isEdit
    ? "Ubah informasi user pada form di bawah ini. Password boleh dikosongkan jika tidak ingin diubah."
    : "Lengkapi form untuk membuat user baru.";
  document.getElementById("passwordHelp").textContent = isEdit
    ? "Kosongkan jika password tidak diubah. Jika diisi, aturan kompleksitas tetap berlaku."
    : "Minimal 8 karakter, mengandung huruf besar, huruf kecil, angka, dan karakter khusus.";
  document.getElementById("confirmPasswordHelp").textContent = isEdit
    ? "Isi hanya jika Anda juga mengisi password baru."
    : "Wajib diisi saat membuat user baru.";

  document.getElementById("password").value = "";
  document.getElementById("confirm_password").value = "";

  const usernameField = document.getElementById("username");
  if (isEdit && user) {
    document.getElementById("userId").value = user.id;
    usernameField.value = user.username || "";
    document.getElementById("email").value = user.email || "";
    document.getElementById("active").checked = Boolean(user.active);
    document.getElementById("roles").value = parseJsonList(user.roles).join(", ");
    document.getElementById("permissions").value = parseJsonList(user.permissions).join(", ");

    usernameField.readOnly = true;
    usernameField.classList.add("bg-light");
  } else {
    resetUserForm();
  }

  document.getElementById("roles").dispatchEvent(new Event("change", { bubbles: true }));
  document.getElementById("permissions").dispatchEvent(new Event("change", { bubbles: true }));
  setButtonLoading(false);
}

async function fetchJson(url, options = {}) {
  const response = await fetch(url, options);
  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    const error = new Error(data.message || data.error || "Terjadi kesalahan.");
    error.status = response.status;
    error.payload = data;
    throw error;
  }

  return data;
}

async function openCreateModal() {
  resetUserForm();
  configureModal("create");
  userModal.show();
}

async function openEditModal(id) {
  try {
    const user = await fetchJson(apiDetailUrl.replace("0", id));
    configureModal("edit", user);
    userModal.show();
  } catch (error) {
    showToast(error.message || "Gagal mengambil data user.", "error");
  }
}

async function viewData(id) {
  try {
    const data = await fetchJson(apiDetailUrl.replace("0", id));
    const roles = parseJsonList(data.roles);
    const permissions = parseJsonList(data.permissions);

    document.getElementById("viewModalBody").innerHTML = `
      <div class="table-responsive">
        <table class="table table-bordered align-middle mb-0">
          <tbody>
            <tr><th width="28%">ID</th><td>${escapeHtml(data.id)}</td></tr>
            <tr><th>UUID</th><td><code>${escapeHtml(data.uuid || "-")}</code></td></tr>
            <tr><th>NIP / Username</th><td>${escapeHtml(data.username || "-")}</td></tr>
            <tr><th>Email</th><td>${escapeHtml(data.email || "-")}</td></tr>
            <tr><th>Status</th><td>${data.active ? '<span class="badge bg-success-subtle text-success">Aktif</span>' : '<span class="badge bg-danger-subtle text-danger">Nonaktif</span>'}</td></tr>
            <tr><th>Email Verified</th><td>${formatDateTime(data.email_verified_at, "Belum verifikasi")}</td></tr>
            <tr><th>Last Login</th><td>${formatDateTime(data.last_login, "Belum pernah login")}</td></tr>
            <tr><th>Roles</th><td>${renderBadgeList(roles)}</td></tr>
            <tr><th>Permissions</th><td>${renderBadgeList(permissions, "bg-info-subtle text-info")}</td></tr>
            <tr><th>Dibuat</th><td>${formatDateTime(data.created_at)}</td></tr>
            <tr><th>Diupdate</th><td>${formatDateTime(data.updated_at)}</td></tr>
          </tbody>
        </table>
      </div>
    `;

    viewModal.show();
  } catch (error) {
    showToast(error.message || "Gagal mengambil detail user.", "error");
  }
}

async function deleteData(id) {
  const result = await Swal.fire({
    title: "Apakah Anda yakin?",
    text: "Data user akan dihapus secara soft delete.",
    icon: "warning",
    showCancelButton: true,
    confirmButtonColor: "#405189",
    cancelButtonColor: "#f06548",
    confirmButtonText: "Ya, hapus",
    cancelButtonText: "Batal",
  });

  if (!result.isConfirmed) return;

  try {
    const response = await fetchJson(deleteUrl.replace("0", id), {
      method: "DELETE",
      headers: {
        "X-CSRFToken": getCsrfToken(),
      },
    });

    showToast(response.message || "User berhasil dihapus.", "success");
    refreshGrid();
  } catch (error) {
    showToast(error.message || "Gagal menghapus user.", "error");
  }
}

function initGrid() {
  if (!tableContainer) return;

  grid = new gridjs.Grid({
    columns: [
      {
        name: "ID",
        width: "70px",
        formatter: (cell) => gridjs.html(`<span class="fw-semibold">${escapeHtml(cell)}</span>`),
      },
      {
        name: "NIP",
        width: "180px",
      },
      {
        name: "Email",
      },
      {
        name: "Status",
        width: "120px",
        formatter: (cell) =>
          gridjs.html(
            cell
              ? '<span class="badge bg-success-subtle text-success">Aktif</span>'
              : '<span class="badge bg-danger-subtle text-danger">Nonaktif</span>'
          ),
      },
      {
        name: "Roles",
        formatter: (cell) => gridjs.html(renderBadgeList(parseJsonList(cell))),
      },
      {
        name: "Permissions",
        formatter: (cell) =>
          gridjs.html(renderBadgeList(parseJsonList(cell), "bg-info-subtle text-info")),
      },
      {
        name: "Aksi",
        width: "160px",
        sort: false,
        formatter: (_, row) => {
          const id = row.cells[0].data;
          return gridjs.html(`
            <div class="d-flex gap-2">
              <button type="button" class="btn btn-soft-info btn-icon btn-sm" onclick="viewData(${id})" title="Lihat detail">
                <i class="ri-eye-line"></i>
              </button>
              <button type="button" class="btn btn-soft-warning btn-icon btn-sm" onclick="openEditModal(${id})" title="Edit user">
                <i class="ri-edit-line"></i>
              </button>
              <button type="button" class="btn btn-soft-danger btn-icon btn-sm" onclick="deleteData(${id})" title="Hapus user">
                <i class="ri-delete-bin-5-line"></i>
              </button>
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
      url: apiListUrl,
      then: buildRows,
    },
  });

  grid.render(tableContainer);
}

function setupPasswordToggles() {
  document.querySelectorAll("[data-password-toggle]").forEach((button) => {
    button.addEventListener("click", () => {
      const inputId = button.dataset.passwordToggle;
      const input = document.getElementById(inputId);
      const icon = button.querySelector("i");
      if (!input || !icon) return;

      const isPassword = input.type === "password";
      input.type = isPassword ? "text" : "password";
      icon.className = isPassword ? "ri-eye-off-fill align-middle" : "ri-eye-fill align-middle";
    });
  });
}

userForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearFormErrors();
  setButtonLoading(true);

  const url = formState.mode === "create"
    ? addUrl
    : editUrl.replace("0", formState.userId);

  const method = formState.mode === "create" ? "POST" : "PUT";
  const formData = new FormData(userForm);

  try {
    const response = await fetchJson(url, {
      method,
      body: formData,
      headers: {
        "X-CSRFToken": getCsrfToken(),
      },
    });

    showToast(response.message || (formState.mode === "create" ? "User berhasil dibuat." : "User berhasil diupdate."), "success");
    userModal.hide();
    refreshGrid();
  } catch (error) {
    const fieldId = inferFieldFromMessage(error.message);
    if (fieldId) {
      markFieldError(fieldId);
    }
    showToast(error.message || "Gagal menyimpan data user.", "error");
  } finally {
    setButtonLoading(false);
  }
});

userModalElement?.addEventListener("hidden.bs.modal", () => {
  resetUserForm();
  formState.mode = "create";
  formState.userId = null;
});

addRecordBtn?.addEventListener("click", openCreateModal);

setupTagEditors();
setupPasswordToggles();
initGrid();

window.viewData = viewData;
window.openEditModal = openEditModal;
window.deleteData = deleteData;

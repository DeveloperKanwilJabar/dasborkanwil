(function () {
  "use strict";

  const config = window.formBuilderConfig || {};
  const builderElement = document.getElementById("formioBuilder");
  const createForm = document.getElementById("formBuilderCreateForm");
  const createFormBtn = document.getElementById("formBuilderCreateFormBtn");
  const formNameInput = document.getElementById("formBuilderName");
  const formCodeInput = document.getElementById("formBuilderCode");
  const formSlugInput = document.getElementById("formBuilderSlug");
  const formDescriptionInput = document.getElementById("formBuilderDescription");
  const formVisibilityInput = document.getElementById("formBuilderVisibility");
  const ownerScopeInput = document.getElementById("formBuilderOwnerScopeCode");
  const targetScopeInput = document.getElementById("formBuilderTargetScopeCode");
  const accessPolicyInput = document.getElementById("formBuilderAccessPolicyKey");
  const ownerScopeHelp = document.getElementById("formBuilderOwnerScopeHelp");
  const targetScopeHelp = document.getElementById("formBuilderTargetScopeHelp");
  const accessPolicyHelp = document.getElementById("formBuilderAccessPolicyHelp");
  const manualSaveBtn = document.getElementById("formBuilderManualSaveBtn");
  const publishBtn = document.getElementById("formBuilderPublishBtn");
  const previewFormBtn = document.getElementById("formBuilderPreviewFormBtn");
  const previewSchemaBtn = document.getElementById("formBuilderPreviewSchemaBtn");
  const insertWilayahCascadeBtn = document.getElementById("formBuilderInsertWilayahCascadeBtn");
  const previewCode = document.getElementById("schemaPreviewCode");
  const previewModalElement = document.getElementById("schemaPreviewModal");
  const autosaveDot = document.getElementById("formBuilderAutosaveDot");
  const autosaveLabel = document.getElementById("formBuilderAutosaveLabel");
  const autosaveDetail = document.getElementById("formBuilderAutosaveDetail");
  const formIdLabel = document.getElementById("formBuilderFormId");
  const draftVersionLabel = document.getElementById("formBuilderDraftVersionId");
  const permissions = config.permissions || {};

  const bootstrapScopes = Array.isArray(config.bootstrapScopes) ? config.bootstrapScopes : [];
  const scopeMap = bootstrapScopes.reduce((accumulator, scope) => {
    if (scope?.code) {
      accumulator[scope.code] = scope;
    }
    return accumulator;
  }, {});
  const formAccessPolicies = Array.isArray(config.formAccessPolicies) ? config.formAccessPolicies : [];
  const policyMap = formAccessPolicies.reduce((accumulator, policy) => {
    if (policy?.key) {
      accumulator[policy.key] = policy;
    }
    return accumulator;
  }, {});
  const registryConsumerPresets = Array.isArray(config.registryConsumerPresets) ? config.registryConsumerPresets : [];
  const registryPresetMap = registryConsumerPresets.reduce((accumulator, preset) => {
    if (preset?.key) {
      accumulator[preset.key] = preset;
    }
    return accumulator;
  }, {});

  const state = {
    builder: null,
    draftVersionId: config.draftVersionId || null,
    sourceVersionId: config.sourceVersionId || null,
    builderMode: config.builderMode || "new",
    formId: config.formId || null,
    autosaveTimer: null,
    isSaving: false,
    isCreatingForm: false,
    isPublishing: false,
    isPublished: false,
    pendingSave: false,
    slugTouched: Boolean(config.formId),
  };

  function canManageCurrentForm() {
    if (!state.formId) return true;
    return Boolean(permissions.can_manage);
  }

  function showToast(message, type = "info") {
    if (typeof window.Toastify !== "function") return;

    const colors = {
      success: "#34c38f",
      error: "#f46a6a",
      warning: "#f1b44c",
      info: "#50a5f1",
    };

    window.Toastify({
      text: message || "Terjadi notifikasi.",
      duration: 5000,
      close: true,
      gravity: "top",
      position: "right",
      style: {
        background: colors[type] || colors.info,
      },
    }).showToast();
  }

  function buildRequestErrorMessage(error, fallback) {
    if (error?.payload?.data?.error_type === "authorization_error") {
      return error?.message || "Akun Anda tidak memiliki izin untuk aksi ini.";
    }

    return error?.message || fallback;
  }

  function handleReadonlyManageAttempt(actionLabel) {
    const detail = "Policy backend mengizinkan lihat konteks form, tetapi aksi perubahan draft/publish ditolak untuk akun Anda.";
    setStatus("error", `${actionLabel} ditolak`, detail);
    showToast(detail, "warning");
  }

  function setStatus(type, label, detail) {
    autosaveDot?.classList.remove("is-saving", "is-saved", "is-error");

    if (type) {
      autosaveDot?.classList.add(`is-${type}`);
    }

    if (autosaveLabel) autosaveLabel.textContent = label;
    if (autosaveDetail) autosaveDetail.textContent = detail;
  }

  function setButtonHtml(button, html) {
    if (button) button.innerHTML = html;
  }

  function getScopeByCode(code) {
    if (!code) return null;
    return scopeMap[code] || null;
  }

  function buildScopePayload(code) {
    const scope = getScopeByCode(code);
    if (!scope) return null;

    return {
      type: scope.type || null,
      code: scope.code || null,
      name: scope.name || null,
      path: Array.isArray(scope.path) ? scope.path : null,
    };
  }

  function describeScope(scope) {
    if (!scope) return "Belum dipilih.";
    const pathLabel = Array.isArray(scope.path) && scope.path.length ? `Path: ${scope.path.join(" > ")}` : "Path belum tersedia.";
    return `${scope.name || scope.code} (${scope.type || "n/a"}). ${pathLabel}`;
  }

  function syncAbacHelpText() {
    const ownerScope = buildScopePayload(ownerScopeInput?.value);
    const targetScope = buildScopePayload(targetScopeInput?.value || ownerScopeInput?.value);
    const policy = policyMap[accessPolicyInput?.value] || null;

    if (ownerScopeHelp) {
      ownerScopeHelp.textContent = `Owner scope: ${describeScope(ownerScope)}`;
    }

    if (targetScopeHelp) {
      targetScopeHelp.textContent = `Target scope: ${describeScope(targetScope)}`;
    }

    if (accessPolicyHelp) {
      accessPolicyHelp.textContent = policy?.description || "Policy baseline untuk authoring/konsumsi form.";
    }
  }

  function refreshActionButtons() {
    if (createFormBtn) {
      createFormBtn.disabled = state.isCreatingForm || Boolean(state.formId);
      if (state.isCreatingForm) {
        setButtonHtml(
          createFormBtn,
          '<span class="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span> Membuat...'
        );
      } else if (state.formId) {
        setButtonHtml(createFormBtn, '<i class="ri-checkbox-circle-line align-bottom me-1"></i> Form Sudah Dibuat');
      } else {
        setButtonHtml(createFormBtn, '<i class="ri-send-plane-line align-bottom me-1"></i> Buat Form & Draft');
      }
    }

    if (manualSaveBtn) {
      manualSaveBtn.disabled = !canManageCurrentForm() || state.isSaving || state.isCreatingForm || state.isPublishing || (state.isPublished && state.builderMode !== "published_source");
      setButtonHtml(
        manualSaveBtn,
        state.isSaving
          ? '<span class="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span> Menyimpan...'
          : '<i class="ri-save-3-line align-bottom me-1"></i> Simpan Draft'
      );
    }

    if (publishBtn) {
      publishBtn.disabled = !canManageCurrentForm() || !state.draftVersionId || state.isSaving || state.isCreatingForm || state.isPublishing || state.isPublished || state.builderMode === "published_source";
      if (state.isPublishing) {
        setButtonHtml(
          publishBtn,
          '<span class="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span> Publishing...'
        );
      } else if (state.isPublished) {
        setButtonHtml(publishBtn, '<i class="ri-checkbox-circle-line align-bottom me-1"></i> Published');
      } else {
        setButtonHtml(publishBtn, '<i class="ri-rocket-line align-bottom me-1"></i> Publish Draft');
      }
    }

    if (previewFormBtn) {
      if (state.formId && state.builderMode === "published_source") {
        previewFormBtn.href = `/forms/${state.formId}/preview`;
        previewFormBtn.classList.remove("disabled");
        previewFormBtn.setAttribute("aria-disabled", "false");
      } else {
        previewFormBtn.href = state.formId ? `/forms/${state.formId}/preview` : "/forms/0/preview";
        previewFormBtn.classList.add("disabled");
        previewFormBtn.setAttribute("aria-disabled", "true");
      }
    }
  }

  function setIdentityFieldsDisabled(disabled) {
    [
      formNameInput,
      formCodeInput,
      formSlugInput,
      formDescriptionInput,
      formVisibilityInput,
      ownerScopeInput,
      targetScopeInput,
      accessPolicyInput,
    ].forEach((field) => {
      if (field) field.disabled = disabled;
    });
    refreshActionButtons();
  }

  function buildUrl(template, id) {
    return String(template || "").replace(/0(?!.*0)/, id);
  }

  function slugify(value) {
    return String(value || "")
      .toLowerCase()
      .trim()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "");
  }

  function normalizeCode(value) {
    return String(value || "")
      .trim()
      .toUpperCase()
      .replace(/\s+/g, "-");
  }

  function normalizeSchema(schema) {
    const nextSchema = schema && typeof schema === "object" ? schema : {};
    return {
      display: nextSchema.display || "form",
      components: Array.isArray(nextSchema.components) ? nextSchema.components : [],
      ...nextSchema,
    };
  }

  function ensureLocalFormioBaseUrl() {
    if (!window.Formio?.setBaseUrl) return;

    const resolvedBaseUrl = config.formioBaseUrl || window.location.origin;
    if (!resolvedBaseUrl) return;

    window.Formio.setBaseUrl(resolvedBaseUrl);
  }

  function currentSchema() {
    return normalizeSchema(state.builder?.form || config.initialSchema || { components: [] });
  }

  function updateBrowserUrl() {
    if (!window.history?.replaceState || !state.formId) return;

    const url = new URL(window.location.href);
    url.searchParams.set("form_id", state.formId);
    if (state.draftVersionId) {
      url.searchParams.set("draft_version_id", state.draftVersionId);
    }
    window.history.replaceState({}, "", url.toString());
  }

  async function requestJson(url, options = {}) {
    const response = await fetch(url, {
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
        ...(options.headers || {}),
      },
      ...options,
    });
    const payload = await response.json().catch(() => ({}));

    if (!response.ok) {
      const error = new Error(payload.message || "Request gagal.");
      error.status = response.status;
      error.payload = payload;
      throw error;
    }

    return payload;
  }

  async function createFormAndDraft(event) {
    event?.preventDefault();

    if (state.formId) {
      setIdentityFieldsDisabled(true);
      setStatus("saved", "Form sudah dibuat", "Form dan draft version sudah tersedia. Gunakan Simpan Draft untuk menyimpan perubahan schema.");
      return state.draftVersionId;
    }

    const name = formNameInput?.value.trim();
    const code = normalizeCode(formCodeInput?.value);
    const slug = slugify(formSlugInput?.value || name);
    const ownerScope = buildScopePayload(ownerScopeInput?.value);
    const targetScope = buildScopePayload(targetScopeInput?.value || ownerScopeInput?.value) || ownerScope;
    const accessPolicyKey = accessPolicyInput?.value || null;

    if (formCodeInput) formCodeInput.value = code;
    if (formSlugInput) formSlugInput.value = slug;

    if (!name || !code || !slug) {
      setStatus("error", "Data form belum lengkap", "Nama, kode, dan slug wajib diisi sebelum membuat draft.");
      return null;
    }

    state.isCreatingForm = true;
    refreshActionButtons();
    setStatus("saving", "Membuat form", "Mengirim request create form ke API v1...");

    try {
      const response = await requestJson(config.createFormUrl, {
        method: "POST",
        body: JSON.stringify({
          code,
          slug,
          name,
          description: formDescriptionInput?.value.trim() || null,
          visibility: formVisibilityInput?.value || "internal",
          schema: currentSchema(),
          owner_scope: ownerScope,
          target_scope: targetScope,
          access_policy_key: accessPolicyKey,
        }),
      });

      const form = response.data?.form;
      const draftVersion = response.data?.draft_version;

      if (!form?.id || !draftVersion?.id) {
        throw new Error("API tidak mengembalikan form.id atau draft_version.id.");
      }

      state.formId = form.id;
      state.draftVersionId = draftVersion.id;
      if (formIdLabel) formIdLabel.textContent = form.id;
      if (draftVersionLabel) draftVersionLabel.textContent = draftVersion.version_number || draftVersion.id;
      setIdentityFieldsDisabled(true);
      updateBrowserUrl();
      setStatus("saved", "Form & draft dibuat", "Form berhasil dibuat. Gunakan Simpan Draft atau ubah komponen untuk autosave.");
      return state.draftVersionId;
    } catch (error) {
      setStatus("error", "Create form gagal", error.message || "Gagal membuat form dan draft.");
      return null;
    } finally {
      state.isCreatingForm = false;
      refreshActionButtons();
    }
  }

  async function ensureDraftVersion({ allowCreate = true } = {}) {
    if (!canManageCurrentForm()) {
      throw new Error("Actor tidak memiliki izin mengelola draft form ini.");
    }

    if (state.draftVersionId) return state.draftVersionId;

    if (!state.formId && allowCreate) {
      await createFormAndDraft();
    }

    if (state.draftVersionId) return state.draftVersionId;

    if (!state.formId || !config.createDraftUrlTemplate) {
      throw new Error("Draft version ID belum tersedia. Buat form terlebih dahulu.");
    }

    setStatus(
      "saving",
      "Membuat draft",
      state.sourceVersionId
        ? "Membuat draft baru dari published version sebelum autosave..."
        : "Membuat draft version awal sebelum autosave..."
    );
    const response = await requestJson(buildUrl(config.createDraftUrlTemplate, state.formId), {
      method: "POST",
      body: JSON.stringify({
        schema: currentSchema(),
        source_version_id: state.sourceVersionId || undefined,
      }),
    });

    const draftVersion = response.data?.draft_version;
    if (!draftVersion?.id) {
      throw new Error("API tidak mengembalikan draft_version.id.");
    }

    state.draftVersionId = draftVersion.id;
    config.selectedVersionNumber = draftVersion.version_number || config.selectedVersionNumber;
    state.builderMode = "edit_draft";
    state.sourceVersionId = null;
    state.isPublished = false;
    if (draftVersionLabel) draftVersionLabel.textContent = draftVersion.version_number || draftVersion.id;
    updateBrowserUrl();
    refreshActionButtons();
    return state.draftVersionId;
  }

  async function saveDraft({ silent = false } = {}) {
    if (!canManageCurrentForm()) {
      handleReadonlyManageAttempt("Simpan draft");
      return null;
    }

    if (state.isSaving || state.isCreatingForm || state.isPublishing) {
      state.pendingSave = true;
      return null;
    }

    if (state.isPublished && state.builderMode !== "published_source") {
      state.pendingSave = true;
      return null;
    }

    if (state.builderMode === "published_source") {
      setStatus("saving", "Membuat draft baru", "Published version tidak diedit langsung. Membuat draft baru dari published version...");
      await ensureDraftVersion({ allowCreate: true });
    }

    state.isSaving = true;
    refreshActionButtons();

    if (!silent) {
      setStatus("saving", "Menyimpan", "Mengirim schema draft ke API...");
    }

    try {
      const draftVersionId = await ensureDraftVersion();
      const response = await requestJson(buildUrl(config.autosaveUrlTemplate, draftVersionId), {
        method: "PATCH",
        body: JSON.stringify({ schema: currentSchema() }),
      });
      const autosavedAt = response.data?.autosaved_at
        ? new Date(response.data.autosaved_at).toLocaleString("id-ID")
        : new Date().toLocaleString("id-ID");

      setStatus("saved", "Draft tersimpan", `Autosave terakhir: ${autosavedAt}`);
      return response;
    } catch (error) {
      const message = buildRequestErrorMessage(error, "Gagal menyimpan draft schema.");
      setStatus("error", "Autosave gagal", message);
      showToast(message, error?.payload?.data?.error_type === "authorization_error" ? "warning" : "error");
      return null;
    } finally {
      state.isSaving = false;
      refreshActionButtons();

      if (state.pendingSave && !state.isPublished) {
        state.pendingSave = false;
        scheduleAutosave(250);
      }
    }
  }

  async function publishDraft() {
    if (!canManageCurrentForm()) {
      handleReadonlyManageAttempt("Publish draft");
      return;
    }

    if (state.isPublished) return;

    window.clearTimeout(state.autosaveTimer);
    state.pendingSave = false;

    const draftVersionId = await ensureDraftVersion({ allowCreate: true }).catch((error) => {
      setStatus("error", "Publish gagal", error.message || "Draft version belum tersedia.");
      return null;
    });
    if (!draftVersionId) return;

    setStatus("saving", "Menyimpan sebelum publish", "Menyimpan schema draft terakhir sebelum publish...");

    const saveResponse = await saveDraft({ silent: true });
    if (!saveResponse) {
      refreshActionButtons();
      return;
    }

    state.isPublishing = true;
    refreshActionButtons();
    setStatus("saving", "Publishing", "Mengirim request publish ke API v1...");

    try {
      const response = await requestJson(buildUrl(config.publishUrlTemplate, draftVersionId), {
        method: "POST",
        body: JSON.stringify({}),
      });
      const publishedVersion = response.data?.published_version;
      state.isPublished = true;
      state.draftVersionId = null;
      state.sourceVersionId = publishedVersion?.id || draftVersionId;
      state.builderMode = "published_source";
      if (draftVersionLabel) draftVersionLabel.textContent = publishedVersion?.version_number || config.selectedVersionNumber || "-";
      setStatus("saved", "Draft published", "Form version berhasil dipublish. Klik Simpan Draft jika perlu membuat draft baru dari versi published ini.");
    } catch (error) {
      const message = buildRequestErrorMessage(error, "Gagal publish draft version.");
      setStatus("error", "Publish gagal", message);
      showToast(message, error?.payload?.data?.error_type === "authorization_error" ? "warning" : "error");
    } finally {
      state.isPublishing = false;
      refreshActionButtons();
    }
  }

  function scheduleAutosave(delay = 1200) {
    window.clearTimeout(state.autosaveTimer);

    if (state.isPublished) {
      setStatus("saved", "Form sudah published", "Draft ini sudah dipublish. Klik Simpan Draft untuk membuat draft baru dari versi published.");
      return;
    }

    if (state.builderMode === "published_source") {
      setStatus(
        null,
        "Published source",
        "Published version tidak diedit langsung. Klik Simpan Draft untuk membuat draft baru dari versi ini."
      );
      return;
    }

    if (!canManageCurrentForm()) {
      setStatus(
        null,
        "Mode read-only",
        "Perubahan schema tidak akan di-autosave karena akun Anda tidak memiliki izin mengelola form ini."
      );
      return;
    }

    if (!state.draftVersionId && !state.formId) {
      setStatus(
        null,
        "Menunggu create form",
        "Isi identitas form lalu klik Buat Form & Draft agar perubahan bisa autosave ke API."
      );
      return;
    }

    setStatus("saving", "Menunggu autosave", "Perubahan terdeteksi, autosave akan berjalan sebentar lagi...");
    state.autosaveTimer = window.setTimeout(() => saveDraft({ silent: false }), delay);
  }

  function openPreview() {
    if (previewCode) {
      previewCode.textContent = JSON.stringify(currentSchema(), null, 2);
    }

    if (previewModalElement && window.bootstrap?.Modal) {
      new window.bootstrap.Modal(previewModalElement).show();
    }
  }

  async function setBuilderSchema(nextSchema) {
    if (!state.builder) return;

    const normalizedSchema = normalizeSchema(nextSchema);
    if (typeof state.builder.setForm === "function") {
      await state.builder.setForm(normalizedSchema);
      return;
    }

    state.builder.form = normalizedSchema;
    if (typeof state.builder.redraw === "function") {
      await state.builder.redraw();
    }
  }

  async function insertPresetComponents(presetKey) {
    const preset = registryPresetMap[presetKey];
    if (!preset) {
      showToast("Preset registry tidak ditemukan.", "warning");
      return;
    }

    if (!state.builder) {
      showToast("Builder belum siap.", "warning");
      return;
    }

    const schema = currentSchema();
    const nextComponents = Array.isArray(schema.components) ? [...schema.components] : [];
    const presetComponents = Array.isArray(preset.components)
      ? preset.components.map((component) => JSON.parse(JSON.stringify(component)))
      : [];

    nextComponents.push(...presetComponents);
    await setBuilderSchema({
      ...schema,
      components: nextComponents,
    });
    scheduleAutosave(250);
    showToast(`${preset.label || "Preset registry"} berhasil ditambahkan ke builder.`, "success");
  }

  function setupIdentityHelpers() {
    formNameInput?.addEventListener("input", () => {
      if (!state.slugTouched && formSlugInput) {
        formSlugInput.value = slugify(formNameInput.value);
      }
    });

    formCodeInput?.addEventListener("blur", () => {
      if (formCodeInput) formCodeInput.value = normalizeCode(formCodeInput.value);
    });

    formSlugInput?.addEventListener("input", () => {
      state.slugTouched = true;
      formSlugInput.value = slugify(formSlugInput.value);
    });

    ownerScopeInput?.addEventListener("change", () => {
      if (targetScopeInput && !targetScopeInput.value) {
        targetScopeInput.value = ownerScopeInput.value;
      }
      syncAbacHelpText();
    });
    targetScopeInput?.addEventListener("change", syncAbacHelpText);
    accessPolicyInput?.addEventListener("change", syncAbacHelpText);
    syncAbacHelpText();
  }

  async function initBuilder() {
    if (!builderElement) return;

    if (!window.Formio?.builder) {
      setStatus("error", "Form.io tidak tersedia", "Pastikan asset @formio/js sudah ter-compile ke app/static/libs.");
      return;
    }

    ensureLocalFormioBaseUrl();
    const initialSchema = normalizeSchema(config.initialSchema || { components: [] });

    try {
      state.builder = await window.Formio.builder(builderElement, initialSchema, {
        noDefaultSubmitButton: true,
        alwaysConfirmComponentRemoval: true,
      });

      state.builder.on("change", () => scheduleAutosave());
      setIdentityFieldsDisabled(Boolean(state.formId));
      setStatus(
        state.formId && !canManageCurrentForm()
          ? null
          : state.draftVersionId || state.formId
            ? "saved"
            : null,
        state.formId && !canManageCurrentForm()
          ? "Mode read-only"
          : state.builderMode === "published_source"
            ? "Published source"
            : state.draftVersionId || state.formId
              ? "Builder siap"
              : "Menunggu create form",
        state.formId && !canManageCurrentForm()
          ? "Akun Anda hanya bisa melihat struktur form. Simpan draft dan publish dinonaktifkan agar sinkron dengan policy backend."
          : state.builderMode === "published_source"
            ? "Published version tidak diedit langsung. Klik Simpan Draft untuk membuat draft baru dari versi ini."
            : state.draftVersionId || state.formId
              ? "Ubah komponen form untuk memicu autosave draft, atau klik Simpan Draft secara manual."
              : "Isi identitas form lalu klik Buat Form & Draft untuk mulai mengirim request ke API."
      );
      refreshActionButtons();
    } catch (error) {
      setStatus("error", "Builder gagal dimuat", error.message || "Gagal inisialisasi Form.io Builder.");
    }
  }

  createForm?.addEventListener("submit", createFormAndDraft);
  manualSaveBtn?.addEventListener("click", () => saveDraft({ silent: false }));
  publishBtn?.addEventListener("click", publishDraft);
  previewSchemaBtn?.addEventListener("click", openPreview);
  insertWilayahCascadeBtn?.addEventListener("click", () => insertPresetComponents("wilayah_cascading_select"));

  setupIdentityHelpers();
  refreshActionButtons();
  initBuilder();
})();

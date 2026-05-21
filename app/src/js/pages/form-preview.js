(function () {
  "use strict";

  const config = window.formPreviewConfig || {};
  const previewElement = document.getElementById("formioPreview");
  const statusDot = document.getElementById("formPreviewSubmissionDot");
  const statusLabel = document.getElementById("formPreviewSubmissionLabel");
  const statusDetail = document.getElementById("formPreviewSubmissionDetail");
  const permissions = config.permissions || {};

  function setStatus(type, label, detail) {
    statusDot?.classList.remove("is-saving", "is-saved", "is-error");

    if (type) {
      statusDot?.classList.add(`is-${type}`);
    }

    if (statusLabel) statusLabel.textContent = label;
    if (statusDetail) statusDetail.textContent = detail;
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
      return error?.message || "Akun Anda tidak memiliki izin submit untuk form ini.";
    }

    return error?.message || fallback;
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

  async function submitForm(submission) {
    const data = submission?.data || {};
    const form = submission?.form;

    if (!permissions.can_submit) {
      const message = "Akun Anda tidak memiliki izin submit untuk form ini. Preview dibuka dalam mode review-only.";
      setStatus("error", "Submit ditolak", message);
      showToast(message, "warning");
      throw new Error(message);
    }

    setStatus("saving", "Mengirim submission", "Mengirim payload ke API v1 Submission...");

    try {
      const response = await requestJson(config.submitUrl, {
        method: "POST",
        body: JSON.stringify({
          payload: data,
          meta: {
            source: "web-preview",
            form_version_id: config.publishedVersionId,
          },
        }),
      });

      const submissionNumber = response.data?.submission_number || response.data?.submission?.submission_number || "-";
      setStatus("saved", "Submission terkirim", `Nomor submission: ${submissionNumber}. Form sudah dikosongkan.`);

      if (form) {
        form.submission = { data: {} };
        await form.redraw();
      }

      return response;
    } catch (error) {
      const message = buildRequestErrorMessage(error, "Gagal mengirim submission.");
      setStatus("error", "Submission gagal", message);
      showToast(message, error?.payload?.data?.error_type === "authorization_error" ? "warning" : "error");
      throw error;
    } finally {
      if (form) {
        form.setPristine(false);
        form.emit("submitDone", submission);
      }
    }
  }

  function ensureLocalFormioBaseUrl() {
    if (!window.Formio?.setBaseUrl) return;

    const resolvedBaseUrl = config.formioBaseUrl || window.location.origin;
    if (!resolvedBaseUrl) return;

    window.Formio.setBaseUrl(resolvedBaseUrl);
  }

  async function initPreview() {
    if (!previewElement) return;

    if (!config.publishedVersionId) {
      setStatus("error", "Belum published", "Form belum memiliki published version.");
      return;
    }

    if (!window.Formio?.createForm) {
      setStatus("error", "Form.io tidak tersedia", "Pastikan asset @formio/js sudah ter-compile ke app/static/libs.");
      return;
    }

    ensureLocalFormioBaseUrl();

    try {
      const form = await window.Formio.createForm(previewElement, config.schema || { components: [] }, {
        noAlerts: true,
        readOnly: !permissions.can_submit,
      });

      form.on("submit", (submission) => {
        submission.form = form;
        return submitForm(submission);
      });
      setStatus(
        permissions.can_submit ? "saved" : null,
        permissions.can_submit ? "Preview siap" : "Preview read-only",
        permissions.can_submit
          ? "Isi form lalu klik Submit untuk mengirim response."
          : "Policy backend menolak submit untuk akun ini, jadi form dirender khusus review schema published."
      );
    } catch (error) {
      setStatus("error", "Preview gagal dimuat", error.message || "Gagal render published form.");
    }
  }

  initPreview();
})();

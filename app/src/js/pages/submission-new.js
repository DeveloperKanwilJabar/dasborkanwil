(function () {
  "use strict";

  const config = window.submissionNewConfig || {};
  const formElement = document.getElementById("submissionNewFormio");
  const statusDot = document.getElementById("submissionNewDot");
  const statusLabel = document.getElementById("submissionNewLabel");
  const statusDetail = document.getElementById("submissionNewDetail");

  function setStatus(type, label, detail) {
    statusDot?.classList.remove("is-saving", "is-saved", "is-error");
    if (type) statusDot?.classList.add(`is-${type}`);
    if (statusLabel) statusLabel.textContent = label;
    if (statusDetail) statusDetail.textContent = detail;
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

  function ensureLocalFormioBaseUrl() {
    if (!window.Formio?.setBaseUrl) return;
    window.Formio.setBaseUrl(config.formioBaseUrl || window.location.origin);
  }

  async function submitForm(submission) {
    const data = submission?.data || {};
    const form = submission?.form;
    setStatus("saving", "Mengirim data", "Mengirim payload ke API v1 Submission...");
    try {
      const response = await requestJson(config.submitUrl, {
        method: "POST",
        body: JSON.stringify({
          payload: data,
          meta: {
            source: "submission-crud-form",
            form_version_id: config.publishedVersionId,
          },
        }),
      });
      const submissionNumber = response.data?.submission_number || response.data?.submission?.submission_number || "-";
      setStatus("saved", "Data tersimpan", `Nomor submission: ${submissionNumber}. Form sudah dikosongkan.`);
      if (form) {
        form.submission = { data: {} };
        await form.redraw();
      }
      return response;
    } catch (error) {
      setStatus("error", "Submit gagal", error.message || "Gagal mengirim submission.");
      throw error;
    } finally {
      if (form) {
        form.setPristine(false);
        form.emit("submitDone", submission);
      }
    }
  }

  async function init() {
    if (!formElement) return;
    if (!config.publishedVersionId) {
      setStatus("error", "Belum published", "Form belum memiliki published version.");
      return;
    }
    if (!window.Formio?.createForm) {
      setStatus("error", "Form.io tidak tersedia", "Pastikan asset @formio/js sudah tersedia.");
      return;
    }
    ensureLocalFormioBaseUrl();
    try {
      const form = await window.Formio.createForm(formElement, config.schema || { components: [] }, { noAlerts: true });
      form.on("submit", (submission) => {
        submission.form = form;
        return submitForm(submission);
      });
      setStatus("saved", "Form siap", "Isi data lalu klik Submit/Kirim untuk menyimpan data baru.");
    } catch (error) {
      setStatus("error", "Form gagal dimuat", error.message || "Gagal render form.");
    }
  }

  init();
})();

document.addEventListener("DOMContentLoaded", function () {
    const form = document.querySelector('#loginForm');
    if (!form) return; // Guard clause jika form tidak ditemukan

    form.addEventListener('submit', function (event) {
        event.preventDefault(); // Stop reload halaman
        event.stopPropagation();

        // 1. Validasi Client-side (HTML5 & password.init.js)
        if (!form.checkValidity()) {
            form.classList.add('was-validated');
            // Tampilkan toast pemberitahuan umum
            showToast("Harap lengkapi semua bidang", "error");
            return;
        }

        // 2. Persiapan Data & UI
        const formData = new FormData(form);
        const submitBtn = form.querySelector('[type="submit"]');
        const originalBtnText = submitBtn.innerText;

        if (submitBtn) {
            const originalBtnText = submitBtn.innerText || submitBtn.value;

            // Cek apakah ini BUTTON atau INPUT
            if (submitBtn.tagName === 'BUTTON') {
                submitBtn.innerHTML = '<i class="ri-loader-2-line label-icon align-middle fs-16 me-2 animate-spin"></i> Memproses...';
            } else {
                // Kalau terpaksa pakai INPUT, cuma bisa ganti teksnya aja, nggak bisa kasih ikon
                submitBtn.value = 'Memproses...';
            }
        }

        // Ubah tombol jadi loading
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="ri-loader-2-line label-icon align-middle fs-16 me-2 animate-spin"></i> Memproses...';

        // 3. Eksekusi Fetch (AJAX)
        fetch(form.action, {
            method: 'POST',
            body: formData,
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
            }
        })
        .then(async (response) => {
            const data = await response.json();

            // Cek jika response status 200-299
            if (response.ok && data.success) {
                showToast(data.message, "success");

                form.reset(); // Kosongkan form
                form.classList.remove('was-validated'); // Reset tampilan validasi

                // Tunggu sebentar agar user sempat baca toast, lalu pindah halaman
                setTimeout(() => {
                    window.location.href = data.data.redirect_url;
                }, 2000);
            } else {
                // Tangkap pesan error dari json_response (status 4xx atau 5xx)
                showToast(data.message || "Gagal mendaftar", "error");
                submitBtn.disabled = false;
                submitBtn.innerText = originalBtnText;
            }
        })
        .catch((error) => {
            // Error koneksi  atau yang tidak terduga
            console.error("Fetch Error:", error);
            showToast("Koneksi ke server bermasalah. Cek koneksi Anda.", "error");
            submitBtn.disabled = false;
            submitBtn.innerText = originalBtnText;
        })
        .finally(() => {
            // Kembalikan tombol ke keadaan semula
            submitBtn.disabled = false;
            submitBtn.innerText = originalBtnText;
        });
    });

    /**
     * Helper Toastify
     */
    function showToast(message, type) {
        Toastify({
            text: message,
            duration: 10000,
            close: true,
            gravity: "top", // `top` atau `bottom`
            position: "right", // `left`, `center` atau `right`
            stopOnFocus: true,
            className: type === "success" ? "bg-success" : "bg-danger",
            style: {
                background: type === "success" ? "#34c38f" : "#f46a6a",
            }
        }).showToast();
    }
});

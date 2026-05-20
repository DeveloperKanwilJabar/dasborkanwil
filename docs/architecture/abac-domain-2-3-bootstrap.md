# ABAC Domain 2-3 Bootstrap Design

Dokumen kerja lokal untuk merapikan domain 2-3 sebelum domain 4 matang.

## 1. Pertanyaan inti: apakah unit kerja harus menunggu domain 4?

Jawaban pendek: tidak harus.

Strategi yang lebih sehat adalah dua fase:

1. Fase bootstrap sekarang
- scope organisasi disediakan lewat registry ringan terlebih dahulu
- sumbernya bisa file Python/YAML/seed table kecil
- tujuannya hanya untuk menstabilkan `scope_type`, `scope_code`, `scope_name`, dan `scope_path`
- domain 2-3 bisa langsung memakai atribut resource yang konsisten tanpa menunggu master data penuh

2. Fase migrasi ke domain 4 nanti
- registry ringan tersebut dipindah menjadi master data resmi / org registry resmi
- `scope_code` tetap dipertahankan sebagai identifier stabil
- resource lama tidak perlu dirombak, karena yang disimpan di form/submission adalah snapshot atribut penting

Analogi praktisnya:
- domain 4 nanti menjadi source of truth organisasi
- domain 2-3 dari sekarang hanya perlu kontrak identitas scope yang stabil

Jadi ini bukan telur-ayam. Yang dibutuhkan sekarang bukan seluruh domain master data, tapi kontrak scope minimal yang stabil.

## 2. Kontrak scope bootstrap yang dipakai sekarang

Field minimum:
- `scope_type`
  - `global`
  - `kanwil`
  - `division`
  - `unit`
  - `upt`
- `scope_code`
  - identifier stabil, slug-like, unik
- `scope_name`
  - nama tampilan manusia
- `scope_path`
  - jalur hirarki penuh, mis. `['kanwil-jabar', 'divisi-pelayanan-hukum', 'ki']`

Prinsip:
- policy engine nanti membandingkan `actor.scope_path` vs `resource.owner_scope_path` / `resource.target_scope_path`
- `scope_code` wajib stabil walau nama tampilan bisa berubah
- `scope_path` dipakai untuk evaluasi ancestor/descendant

## 3. Struktur organisasi bootstrap awal

### Scope level kanwil
- `kanwil-jabar`

### Scope level division
- `divisi-pelayanan-hukum`
- `divisi-p3h`
- `bagian-umum-tata-usaha`

### Scope level unit
- `ki`
- `ahu`
- `perancang-ppu`
- `jdih`
- `penyuluh-hukum`
- `bsk`
- `kepegawaian`
- `keuangan`
- `program-pelaporan`
- `humas`
- `teknologi-informasi`
- `rumah-tangga`

### Scope level upt
- belum dirinci satu per satu, tetapi sudah disiapkan sebagai tipe scope tersendiri

## 4. Kamus `access_policy_key` awal

### Policy authoring form

1. `form.admin_only_authoring`
- dipakai untuk lifecycle authoring
- siapa yang boleh:
  - admin lintas bagian
  - superadmin
- aksi utama:
  - `form:create`
  - `form:update`
  - `form:publish`
  - `form:archive`

### Policy distribusi form

2. `form.unit_internal`
- form hanya untuk unit yang sama
- contoh:
  - form milik KI untuk KI saja

3. `form.division_broadcast`
- form dikonsumsi seluruh unit dalam satu divisi
- contoh:
  - form target `divisi-pelayanan-hukum`, maka KI dan AHU bisa lihat dan isi

4. `form.kanwil_broadcast`
- form dikonsumsi seluruh unit dalam satu kanwil
- contoh:
  - form laporan tahunan untuk semua unit kerja di kanwil

5. `form.upt_network`
- form dikonsumsi jaringan UPT tertentu
- berguna saat domain UPT mulai diaktifkan

### Policy pembacaan submission

6. `submission.unit_owned`
- submission terlihat oleh unit pemilik data
- baseline untuk pegawai unit

7. `submission.division_audit`
- submission dapat dibaca kepala divisi untuk seluruh unit di bawah divisinya

8. `submission.kanwil_audit`
- submission dapat dibaca auditor / program dan pelaporan / kakanwil untuk seluruh kanwil

9. `submission.superadmin_full`
- full access untuk superadmin

## 5. Policy matrix awal

| Aktor | Scope Aktor | Lihat Form | Isi Form | Lihat Submission | Export Submission | Create/Update/Publish Form |
|---|---|---:|---:|---:|---:|---:|
| Superadmin | global | Ya | Ya | Ya | Ya | Ya |
| Admin lintas bagian | kanwil | Ya | Opsional | Ya | Ya | Ya |
| Auditor / Program & Pelaporan | kanwil | Ya | Tidak | Ya | Ya | Tidak |
| Kakanwil | kanwil | Ya | Tidak | Ya | Ya | Tidak |
| Kepala Divisi | division | Ya | Tidak | Ya | Ya | Tidak |
| Pegawai unit | unit | Ya | Ya | Ya, scope unit | Tidak default | Tidak |
| Operator UPT | upt | Ya | Ya | Ya, scope UPT | Tidak default | Tidak |

## 6. Aturan evaluasi scope awal

### Pegawai unit
Boleh:
- lihat form jika `target_scope_path` resource mencakup unitnya
- submit jika unit actor berada di bawah `target_scope_path`
- lihat submission jika `submission.owner_scope_code == actor.scope_code`

### Kepala divisi
Boleh:
- lihat semua submission jika `submission.owner_scope_path` berada di bawah divisinya
- tidak boleh create/publish form pada baseline awal

### Auditor / program dan pelaporan
Boleh:
- lihat semua submission pada `kanwil-jabar`
- export untuk kebutuhan laporan
- tidak boleh mengubah payload submission

### Admin lintas bagian
Boleh:
- create/update/publish form
- menentukan `target_scope_*`
- lihat seluruh submission di kanwil

### Kakanwil
Boleh:
- read-only lintas kanwil
- setara auditor lintas scope, tapi tanpa authoring form

### Superadmin
Boleh semua

## 7. Pemetaan resource attribute

### `forms`
- `owner_scope_*`
  - siapa pemilik form secara organisasi
- `target_scope_*`
  - siapa konsumen form
- `access_policy_key`
  - cara form dievaluasi oleh policy

### `form_versions`
- `scope_snapshot`
  - snapshot owner/target scope ketika draft/publish
- `access_policy_snapshot`
  - snapshot policy key ketika draft/publish

### `submissions`
- `owner_scope_*`
  - data ini milik/wakil scope mana
- `subject_*`
  - siapa subjek data yang diwakili submission
- `access_policy_key`
  - hook evaluasi policy submission

## 8. Saran implementasi bertahap berikutnya

### Tahap A — sekarang
- pakai bootstrap scope registry ringan
- policy key disimpan eksplisit di resource
- actor scope bisa disimpan dulu di `users.settings` / atribut actor context

### Tahap B — domain 1
- buat evaluator authorization nyata
- buat helper seperti:
  - `can_view_form(actor, form)`
  - `can_submit_form(actor, form)`
  - `can_view_submission(actor, submission)`
  - `can_publish_form(actor, form)`

### Tahap C — domain 4
- bentuk master data / org registry resmi
- migrasikan bootstrap scope registry menjadi registry database
- pertahankan `scope_code` sebagai identifier stabil

## 9. Keputusan desain yang direkomendasikan

1. Jangan tunggu domain 4 untuk menstabilkan ABAC resource attributes.
2. Gunakan bootstrap scope registry ringan sekarang.
3. Perlakukan `scope_code` sebagai contract utama yang nanti akan survive ke domain 4.
4. Simpan scope penting sebagai kolom eksplisit terindex di resource.
5. Gunakan JSONB hanya untuk snapshot/path/context, bukan satu-satunya sumber evaluasi.

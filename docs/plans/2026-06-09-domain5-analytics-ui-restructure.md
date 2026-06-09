# Domain 5 Analytics UI Restructure Plan

> For Hermes: gunakan pendekatan implementasi bertahap berbasis contract-first, lalu eksekusi UI/route/API secara incremental.

Goal: merapikan Domain 5 agar user tidak salah paham antara Data Registry, Analytics Dataset, Dataset Run, dan Detail Report.

Architecture: pisahkan entry point bisnis menjadi 4 layar yang masing-masing punya boundary jelas: registry browser, dataset catalog, dataset workspace, dan report viewer. Registry bukan lagi dianggap langsung punya detail report; report adalah turunan dari dataset analytics yang mungkin memakai source form submission, data registry, atau gabungan keduanya.

Tech Stack: Flask, Jinja/Velzon, Grid.js atau tabel Bootstrap, service layer analytics/data registry, Plotly, Flasgger docstring.

---

## Masalah UI saat ini

1. Halaman `/analytics` saat ini menampilkan daftar registry publish sebagai entry point utama.
2. Tombol `Buka Detail Report` ada di baris registry, sehingga secara mental model user terasa seperti report tersebut milik registry itu.
3. Padahal layar detail report saat ini sebenarnya bekerja pada dataset analytics yang bisa bersumber dari form submission.
4. Akibatnya terjadi mismatch:
   - list page berbicara tentang registry,
   - detail page berbicara tentang dataset analytics.
5. Ini membuat user mudah mengira `wilayah` punya report sendiri, padahal yang dibuka adalah workspace dataset umum.

## Rekomendasi Information Architecture Baru

### 1. Data Registries
Tujuan:
- browser untuk registry publish/draft,
- fokus ke metadata, source, versi, record, publish lifecycle,
- bukan pintu langsung ke detail report analytics.

Aksi utama:
- Workspace Registry
- Metadata
- Lihat Dataset Terkait

Tidak perlu aksi langsung `Detail Report` di row registry.

### 2. Analytics Datasets
Tujuan:
- menjadi katalog resmi semua dataset analytics,
- ini yang menjadi entry point utama ke report.

Tabel utama minimal berisi:
- Nama dataset
- Dataset key
- Source domain (`data_registry`, `submission`, `hybrid`)
- Source type
- Sumber utama (registry/form)
- Status publish dataset version
- Last run status
- Last run row count
- Aksi

Aksi row:
- Buka Workspace Dataset
- Buka Report
- Lihat Runs
- Edit Dataset
- Metadata/Contract

CTA global:
- Buat Dataset Baru

### 3. Dataset Workspace
Tujuan:
- halaman kerja teknis/operasional untuk satu dataset.

Blok UI:
- header dataset
- source summary
- versi aktif
- field mapping / dimensi / metric contract
- run panel
- run history
- quick preview row/schema

Di sinilah tombol berada:
- Jalankan Dataset
- Refresh Run
- Edit Contract
- Publish Version

Halaman ini adalah jembatan eksplisit dari source operasional ke materialized analytics dataset.

### 4. Report Viewer
Tujuan:
- halaman konsumsi insight untuk manusia.

Isi:
- preset waktu
- filter
- KPI cards
- chart Plotly
- peta
- preview tabel insight

Tidak perlu dibebani metadata registry yang panjang.

Deep link kecil:
- ke Metadata Dataset
- ke Workspace Dataset
- ke Run History

## Flow User yang Disarankan

### Flow A: user sedang mengelola referensi data
`Data Registries -> pilih registry -> metadata/workspace registry -> lihat dataset terkait`

### Flow B: user sedang membangun analytics
`Analytics Datasets -> buat/edit dataset -> tentukan source -> mapping field -> publish dataset version -> jalankan run`

### Flow C: user sedang membaca insight
`Analytics Datasets -> buka report`

## Rekomendasi Route Baru

1. `/analytics`
- ubah menjadi halaman katalog dataset analytics, bukan daftar registry publish.

2. `/analytics/datasets/create`
- form wizard/stepper membuat dataset baru.

3. `/analytics/datasets/<dataset_id>`
- workspace dataset.

4. `/analytics/datasets/<dataset_id>/report`
- report viewer.

5. `/analytics/datasets/<dataset_id>/runs`
- run history / observability ringan.

6. `/analytics/registries` atau tetap pakai halaman registry existing
- hanya untuk browser registry yang relevan ke analytics.

## Model Konseptual UI Pembuatan Dataset

### Step 1: Identitas dataset
- Nama dataset
- Dataset key
- Deskripsi
- Source domain
- Source type

### Step 2: Pilih sumber data
Jika source domain = data_registry:
- pilih registry publish
- pilih versi publish
- pilih field yang akan dipakai

Jika source domain = submission:
- pilih form publish
- pilih versi form atau published version target
- pilih field submission yang akan dipakai
- pilih date field
- pilih dimensi default

Jika hybrid:
- pilih primary source
- pilih join registry tambahan
- pilih key join

### Step 3: Bentuk contract dataset
- dimension definitions
- metric definitions
- grain
- default filter
- sort spec
- output schema preview

### Step 4: Publish dataset version
- draft -> published

### Step 5: Run dataset
- manual run
- preview result
- link ke report

## Perubahan UI Konkret yang Paling Penting

### A. Hapus tombol `Buka Detail Report` dari row registry
Ganti dengan:
- `Lihat Dataset Terkait`
- atau `Buka Workspace Registry`
- atau `Analytics Linkage`

### B. Ubah `/analytics` menjadi katalog dataset
Ini akan menyelesaikan mismatch mental model.

### C. Tambah halaman katalog dataset khusus
Ini yang menjadi pusat analytics sebenarnya.

### D. Detail report hanya boleh dibuka dari dataset
Bukan dari registry secara langsung.

## Saran Implementasi Bertahap

### Phase 1 — Rapikan IA tanpa ubah engine terlalu banyak
- `/analytics` diubah jadi daftar dataset
- aksi detail report dipindahkan ke dataset row
- registry page hanya menampilkan dataset linkage
- workspace dataset memakai service dan API yang sudah ada sejauh mungkin

### Phase 2 — Tambah create/edit dataset UI
- tambah form CRUD dataset
- source picker registry/submission/hybrid
- publish dataset version

### Phase 3 — Tambah field mapping UX
- pilih dimensi/metric/date field dari source
- preview schema output

### Phase 4 — Sempurnakan report viewer
- report khusus konsumsi manusia
- workspace dataset tetap teknis

## Saran Produk / UX

Menurutku arah terbaik adalah ini:

1. Registry = sumber/master/reference
2. Dataset = produk analytics yang bisa dibangun dari registry, submission, atau gabungan
3. Run = proses materialisasi dataset
4. Report = tampilan insight dari hasil dataset run

Kalau boundary ini dijaga, user akan jauh lebih paham.

## Dampak ke Backend

Perlu penyesuaian ringan-menengah:
- web routes analytics perlu dipisah antara dataset browser dan report viewer,
- serializer dataset list perlu memuat last run summary,
- create/edit dataset form perlu contract source picker,
- API create run yang sekarang sudah ada bisa dipakai ulang,
- docstring Flasgger perlu ditambah untuk CRUD dataset dan dataset workspace jika route baru dibuat.

## Usulan File yang Nanti Akan Disentuh

- `app/modules/analytics/routes_web.py`
- `app/api/v1/analytics/routes.py`
- `app/modules/analytics/services.py`
- `app/templates/pages/analytics/index.html`
- `app/templates/pages/analytics/datasets/index.html` (baru)
- `app/templates/pages/analytics/datasets/form.html` (baru)
- `app/templates/pages/analytics/datasets/workspace.html` (baru)
- `app/templates/pages/analytics/datasets/report.html` (baru atau refactor dari detail_report)
- `app/src/js/pages/analytics-workspace.js`
- `app/src/js/pages/analytics-dataset-form.js` (baru)

## Keputusan Rekomendasi

Rekomendasi final:
- setop menjadikan registry row sebagai pintu langsung ke detail report,
- jadikan dataset analytics sebagai entitas utama di Domain 5 UI,
- letakkan report di bawah dataset, bukan di bawah registry,
- pertahankan registry hanya sebagai source browser + metadata source.

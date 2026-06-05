# Domain 5 — Dataset Execution & Refresh Workflow Implementation Plan v1

> For Hermes: lanjutkan secara TDD per task kecil. Jangan lompat ke dashboard final.

**Goal:** menghidupkan workflow operasional `analytics_dataset_runs` agar foundation Slice A-C bisa benar-benar mengeksekusi dataset run, menyimpan preview/summary, dan menjadi source nyata untuk indikator `dataset_driven`.

**Architecture:** tambahkan service/repository khusus dataset run di atas foundation `analytics_datasets`, `analytics_dataset_versions`, `analytics_dataset_runs`. Fase ini tetap tipis: belum ada async worker, belum ada formula engine bebas, belum ada dashboard final. Fokus hanya pada lifecycle run sinkron + payload observasi dasar.

**Tech Stack:** Flask, SQLAlchemy, Flask test client, pytest, PostgreSQL-ready models, thin API v1.

---

## Scope v1 yang dikunci

### Masuk scope
- repository minimum untuk dataset, dataset version, dataset run
- service create/publish dataset version bila memang belum ada behavior layer operasionalnya
- service start dataset run
- service mark run success
- service mark run failure
- penyimpanan `result_schema_json`, `result_preview_json`, `summary_json`, `error_code`, `error_message`
- thin API untuk list/detail/create run
- test behavior dan API contract dasar

### Di luar scope
- async runner / queue / cron compute
- query engine bebas dari UI
- chart/dashboard final
- orchestration penuh dari submissions/registry ke query spec nyata
- RBAC/ABAC detail per endpoint analytics

---

## Task 1: Audit code foundation dataset saat ini

**Objective:** memastikan boundary file yang akan disentuh kecil dan tidak bocor ke layer indikator/result.

**Files:**
- Read: `app/modules/analytics/models.py`
- Read: `app/modules/analytics/repositories.py`
- Read: `app/modules/analytics/services.py`
- Read: `tests/test_analytics_foundation_models.py`

**Steps:**
1. identifikasi apakah repository dataset/version/run sudah ada atau belum
2. identifikasi apakah service dataset/run sudah ada atau belum
3. catat method minimal yang dibutuhkan fase ini:
   - `create_dataset(...)`
   - `create_dataset_version(...)`
   - `publish_dataset_version(...)`
   - `start_run(...)`
   - `complete_run(...)`
   - `fail_run(...)`
4. verifikasi tidak ada overlap liar dengan `AnalyticsIndicatorService`

**Verification:**
- boundary method tertulis jelas sebelum coding

---

## Task 2: Tulis failing repository/service behavior tests untuk dataset run lifecycle

**Objective:** mengunci lifecycle run sebelum implementasi.

**Files:**
- Create: `tests/test_analytics_dataset_run_service_behaviors.py`

**Step 1: Write failing test — create and publish dataset version**
- scenario minimum:
  1. create dataset draft
  2. create dataset version draft
  3. publish dataset version
  4. publish kedua mengarsipkan published lama bila ada

**Step 2: Write failing test — start and complete run**
- scenario minimum:
  1. start run untuk dataset version published
  2. status awal `running`
  3. complete run dengan:
     - `result_row_count`
     - `result_schema_json`
     - `result_preview_json`
     - `summary_json`
     - `materialization_ref`
  4. assert status jadi `success`
  5. assert `finished_at` terisi

**Step 3: Write failing test — fail run**
- scenario minimum:
  1. start run
  2. fail run dengan `error_code`, `error_message`, `error_detail_json`
  3. assert status jadi `failed`
  4. assert payload hasil sukses tidak wajib terisi

**Step 4: Write failing test — reject run for unpublished version**
- tidak boleh start run untuk dataset version yang belum published

**Verification command:**
```bash
docker exec -w /usr/src/app dasborkanwil_app sh -lc 'PYTHONPATH=/usr/src/app pytest tests/test_analytics_dataset_run_service_behaviors.py -q'
```
Expected awal: FAIL

---

## Task 3: Tambah repository minimum untuk dataset/version/run

**Objective:** menyediakan contract persistence kecil dan eksplisit.

**Files:**
- Modify: `app/modules/analytics/repositories.py`

**Method minimum yang dibutuhkan:**
- `AnalyticsDatasetRepository`
  - `create(...)`
  - `get_by_id(...)`
  - `list_paginated(...)`
- `AnalyticsDatasetVersionRepository`
  - `create(...)`
  - `get_by_id(...)`
  - `get_published_for_dataset(dataset_id)`
  - `archive_published_for_dataset(dataset_id)`
- `AnalyticsDatasetRunRepository`
  - `create(...)`
  - `get_by_id(...)`
  - `list_by_dataset(dataset_id, ...)`
  - `list_by_dataset_version(dataset_version_id, ...)`
  - `get_latest_for_dataset_version(dataset_version_id)`

**Verification:**
- import repository baru tidak merusak suite existing

---

## Task 4: Implement service dataset definition + run lifecycle sampai GREEN

**Objective:** menghidupkan orchestration minimal di service layer.

**Files:**
- Modify: `app/modules/analytics/services.py`

**Service minimum:**
- `AnalyticsDatasetService`
- `AnalyticsDatasetRunService`

**Rules:**
1. dataset version published lama harus diarsipkan sebelum publish baru
2. `start_run()` hanya boleh untuk dataset version published
3. `start_run()` membuat `run_key` unik dan status `running`
4. `complete_run()` mengisi preview/schema/summary lalu set status `success`
5. `fail_run()` mengisi `error_code`, `error_message`, `error_detail_json`, lalu set status `failed`
6. `finished_at` wajib terisi pada success/failure
7. `started_at` diisi saat run dibuat

**Verification command:**
```bash
docker exec -w /usr/src/app dasborkanwil_app sh -lc 'PYTHONPATH=/usr/src/app pytest tests/test_analytics_dataset_run_service_behaviors.py -q'
```
Expected: PASS

---

## Task 5: Tambah thin API tests untuk dataset runs

**Objective:** mengunci contract observasi dasar dari web/API sebelum UI dibangun lebih jauh.

**Files:**
- Create: `tests/test_api_analytics_dataset_run_routes.py`

**Endpoints minimum:**
- `GET /api/v1/analytics/datasets`
- `GET /api/v1/analytics/datasets/<dataset_id>`
- `GET /api/v1/analytics/datasets/<dataset_id>/runs`
- `POST /api/v1/analytics/datasets/<dataset_id>/versions/<dataset_version_id>/runs`
- opsional tipis: `GET /api/v1/analytics/runs/<run_id>`

**Contract minimum:**
- list endpoint mengembalikan ringkasan dataset/version/run terbaru
- create run mengembalikan status `running`
- detail run mengembalikan `status`, `run_key`, `result_row_count`, `summary_json`, `error_code`, `error_message`

**Verification command:**
```bash
docker exec -w /usr/src/app dasborkanwil_app sh -lc 'PYTHONPATH=/usr/src/app pytest tests/test_api_analytics_dataset_run_routes.py -q'
```
Expected awal: FAIL

---

## Task 6: Implement thin API dataset run routes sampai GREEN

**Objective:** membuka jalur observasi dasar untuk foundation dataset runs.

**Files:**
- Modify: `app/api/v1/analytics/routes.py`
- Modify: `app/modules/analytics/services.py`
- Modify: `app/modules/analytics/repositories.py`

**Rules:**
1. route hanya menjadi orchestration tipis
2. business rule tetap di service
3. response shape konsisten dengan gaya API analytics yang sudah ada
4. jangan sekaligus membangun UI/dashboard besar

**Verification command:**
```bash
docker exec -w /usr/src/app dasborkanwil_app sh -lc 'PYTHONPATH=/usr/src/app pytest tests/test_api_analytics_dataset_run_routes.py tests/test_analytics_dataset_run_service_behaviors.py -q'
```
Expected: PASS

---

## Task 7: Tambah workspace observability tipis (opsional tapi direkomendasikan)

**Objective:** memberi hook UI kecil agar dataset run bisa dilihat sebelum dashboard final.

**Files:**
- Modify: `app/templates/pages/analytics/workspace.html`
- Modify: `app/src/js/pages/analytics-workspace.js`
- Test: `tests/test_analytics_web_routes.py`

**Scope kecil:**
- tab atau panel “Dataset Runs”
- hanya tampilkan list ringkas:
  - dataset
  - version
  - status
  - started_at
  - finished_at
  - result_row_count
- jangan masuk chart/detail designer dulu

**Verification:**
- web route smoke tetap hijau
- tidak merusak tab indikator yang sudah ada

---

## Task 8: Jalankan regression gabungan

**Objective:** memastikan target baru tidak merusak Slice A-C.

**Verification command:**
```bash
docker exec -w /usr/src/app dasborkanwil_app sh -lc 'PYTHONPATH=/usr/src/app pytest \
  tests/test_analytics_foundation_models.py \
  tests/test_analytics_indicator_models.py \
  tests/test_analytics_indicator_definition_migration.py \
  tests/test_analytics_indicator_result_migration.py \
  tests/test_analytics_indicator_service_contracts.py \
  tests/test_analytics_indicator_service_behaviors.py \
  tests/test_api_analytics_routes.py \
  tests/test_api_analytics_dataset_run_routes.py \
  tests/test_analytics_dataset_run_service_behaviors.py \
  tests/test_analytics_web_routes.py -q'
```

Expected:
- seluruh suite analytics hijau

---

## Task 9: Fresh DB migration smoke test ulang

**Objective:** membuktikan perubahan baru tetap aman di database kosong.

**Verification:**
1. buat temp DB PostgreSQL
2. jalankan `flask db upgrade`
3. cek `flask db current`
4. inspect tabel analytics
5. hapus temp DB setelah selesai

Catatan:
- gunakan override `DB_NAME`/`DB_*` dari dalam container app
- jangan mengandalkan `FLASK_ENV=testing` saja

---

## Acceptance criteria

Plan ini dianggap selesai bila:
- dataset/version/run punya service lifecycle yang nyata
- dataset run bisa `running -> success` dan `running -> failed`
- payload observasi hasil tersimpan di tabel run
- ada thin API untuk observasi dataset runs
- regression Slice A-C tetap hijau
- fresh DB migration smoke test tetap hijau

---

## Commit slicing yang direkomendasikan

1. `feat: add analytics dataset run service behaviors`
2. `feat: add analytics dataset run api contracts`
3. `feat: add analytics dataset run workspace observability`

---

## Handoff eksekusi

Urutan paling aman:
1. Task 2
2. Task 3
3. Task 4
4. Task 5
5. Task 6
6. Task 7
7. Task 8
8. Task 9

Jangan mulai dari UI dulu. Kunci nilainya ada di lifecycle `analytics_dataset_runs`, bukan di kosmetik workspace.

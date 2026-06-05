# Domain 5 — Commit Staging Plan v1

Dokumen ini adalah panduan praktis untuk men-stage working tree Domain 5 analytics menjadi tiga commit slice yang rapi.

Tujuan utamanya:
- memudahkan commit bertahap tanpa mencampur foundation, definition layer, dan vertical slice UI/API
- memberi perintah `git add` yang konkret
- menandai file yang aman di-stage penuh vs file yang perlu `git add -p`

Status asumsi saat dokumen ini ditulis:
- mayoritas file analytics masih `??` / untracked
- `app/__init__.py` adalah tracked file yang sedang berubah
- file lintas-slice utama adalah:
  - `app/modules/analytics/models.py`
  - `app/modules/analytics/services.py`
  - `tests/test_analytics_indicator_service_behaviors.py`

---

## 1. Prinsip staging yang dipakai

### 1.1. File yang aman di-stage penuh
Gunakan `git add <file>` biasa untuk file yang secara boundary memang milik satu slice penuh.

### 1.2. File baru yang harus dipecah per slice
Karena beberapa file masih untracked dan isinya mencakup beberapa slice, gunakan pola ini:

```bash
git add -N path/to/file
git add -p path/to/file
```

Makna:
- `git add -N` = tandai file sebagai intent-to-add supaya bisa dipatch per hunk
- `git add -p` = pilih hunk yang masuk commit slice saat ini

Kalau hunk terlalu besar dan perlu dipecah lagi:
- tekan `s` untuk split
- tekan `e` kalau perlu edit patch manual
- tekan `y` untuk stage hunk
- tekan `n` untuk skip hunk

### 1.3. Urutan commit yang direkomendasikan
Lakukan persis urutan ini:
1. commit Slice A
2. commit Slice B
3. commit Slice C

Jangan lompat ke Slice C dulu karena `app/__init__.py` dan workspace route/API mengasumsikan foundation + definition layer sudah ada.

---

## 2. Slice A — foundation dataset analytics

## 2.1. Boundary slice A
Fokus hanya pada:
- `analytics_datasets`
- `analytics_dataset_versions`
- `analytics_dataset_runs`
- migration foundation
- tests foundation
- docs foundation Domain 5

### Class boundary yang masuk Slice A
File: `app/modules/analytics/models.py`
- `AnalyticsDataset` (mulai sekitar line 11)
- `AnalyticsDatasetVersion` (mulai sekitar line 97)
- `AnalyticsDatasetRun` (mulai sekitar line 198)
- berhenti sebelum `AnalyticsReportDefinition` (mulai sekitar line 304)

---

## 2.2. Stage command Slice A

### A. Stage file penuh
```bash
git add \
  docs/architecture/domain-5-blueprint-v1.md \
  docs/architecture/domain-5-schema-contract-v1.md \
  docs/architecture/domain-5-migration-schema-plan-v1.md \
  docs/architecture/domain-5-transition-and-boundary-audit-v1.md \
  migrations/versions/a1b2c3d4e5f6_add_analytics_dataset_foundation_v1.py \
  tests/test_analytics_foundation_models.py
```

### B. Stage sebagian dari `models.py`
```bash
git add -N app/modules/analytics/models.py
git add -p app/modules/analytics/models.py
```

Pilih hanya hunk foundation dataset:
- import/utility yang dipakai foundation
- class `AnalyticsDataset`
- class `AnalyticsDatasetVersion`
- class `AnalyticsDatasetRun`

Jangan stage dulu hunk yang mulai memperkenalkan:
- `AnalyticsReportDefinition`
- `AnalyticsReportVersion`
- `AnalyticsIndicatorDefinition`
- `AnalyticsIndicatorVersion`
- `AnalyticsReportVersionIndicator`
- `AnalyticsIndicatorResult`
- `AnalyticsIndicatorProgressEntry`
- `AnalyticsIndicatorProgressItem`

### C. Verifikasi staging Slice A
```bash
git diff --cached --stat
git diff --cached -- app/modules/analytics/models.py
```

### D. Test minimum sebelum commit Slice A
```bash
docker exec -w /usr/src/app dasborkanwil_app sh -lc 'PYTHONPATH=/usr/src/app pytest tests/test_analytics_foundation_models.py -q'
```

### E. Commit Slice A
```bash
git commit -m "feat: add analytics dataset foundation v1"
```

---

## 3. Slice B — definition layer indikator/report + contract/service foundation

## 3.1. Boundary slice B
Fokus pada:
- `analytics_report_definitions`
- `analytics_report_versions`
- `analytics_indicator_definitions`
- `analytics_indicator_versions`
- `analytics_report_version_indicators`
- repository/service contracts
- behavior create/publish/attach di definition layer
- docs blueprint/schema/implementation plan indikator dinamis

### Class boundary yang masuk Slice B
File: `app/modules/analytics/models.py`
- `AnalyticsReportDefinition` (mulai sekitar line 304)
- `AnalyticsReportVersion` (sekitar line 356)
- `AnalyticsIndicatorDefinition` (sekitar line 428)
- `AnalyticsIndicatorVersion` (sekitar line 495)
- `AnalyticsReportVersionIndicator` (sekitar line 598)
- berhenti sebelum `AnalyticsIndicatorResult` (mulai sekitar line 645)

### Service boundary yang masuk Slice B
File: `app/modules/analytics/services.py`
- `AnalyticsReportService` (mulai line 28)
- `AnalyticsIndicatorService` (mulai line 108)
- berhenti sebelum `AnalyticsIndicatorResultService` (mulai line 249)

### Behavior test yang masuk Slice B
File: `tests/test_analytics_indicator_service_behaviors.py`
Masuk Slice B:
- `test_create_publish_indicator_and_report_flow_archives_previous_versions()`
- `test_attach_indicator_to_report_version_rejects_unpublished_indicator_version()`
- `test_create_indicator_version_rejects_dataset_manual_source_mode_mismatch()`

Belum masuk Slice B:
- `test_record_progress_entry_with_items_and_sync_result_updates_narrative_without_losing_dataset_trace()`
- `test_record_result_for_dataset_driven_indicator_builds_default_source_trace()`

---

## 3.2. Stage command Slice B

### A. Stage file penuh
```bash
git add \
  docs/architecture/domain-5-dynamic-performance-indicators-blueprint-v1.md \
  docs/architecture/domain-5-dynamic-performance-indicators-schema-contract-v1.md \
  docs/architecture/domain-5-dynamic-performance-indicators-migration-schema-plan-v1.md \
  docs/architecture/domain-5-analytics-indicators-implementation-plan-v1.md \
  migrations/versions/b7e1c2d3f4a5_add_analytics_indicator_definition_layer_v1.py \
  tests/test_analytics_indicator_models.py \
  tests/test_analytics_indicator_definition_migration.py \
  tests/test_analytics_indicator_service_contracts.py \
  app/modules/analytics/repositories.py
```

Catatan:
- `app/modules/analytics/repositories.py` boleh ikut utuh di Slice B agar kontrak repository sudah hidup sejak definition layer.
- `app/modules/analytics/__init__.py` saat ini cuma docstring tipis; tidak wajib tapi aman bila ikut di Slice B jika nanti ingin diberi status tracked.

### B. Stage sebagian dari `models.py`
```bash
git add -p app/modules/analytics/models.py
```

Pilih hunk yang menambahkan:
- `AnalyticsReportDefinition`
- `AnalyticsReportVersion`
- `AnalyticsIndicatorDefinition`
- `AnalyticsIndicatorVersion`
- `AnalyticsReportVersionIndicator`

Skip dulu hunk yang menambah:
- `AnalyticsIndicatorResult`
- `AnalyticsIndicatorProgressEntry`
- `AnalyticsIndicatorProgressItem`

### C. Stage sebagian dari `services.py`
```bash
git add -N app/modules/analytics/services.py
git add -p app/modules/analytics/services.py
```

Pilih hanya hunk untuk:
- import yang dibutuhkan definition layer
- `AnalyticsReportService`
- `AnalyticsIndicatorService`

Skip dulu hunk untuk:
- `AnalyticsIndicatorResultService`
- `AnalyticsQueryService`

### D. Stage sebagian dari behavior tests
```bash
git add -N tests/test_analytics_indicator_service_behaviors.py
git add -p tests/test_analytics_indicator_service_behaviors.py
```

Stage hanya test behavior definition layer:
- create/publish report + indicator
- attach unpublished indicator rejected
- source mode mismatch rejected

Skip dulu test yang menyentuh:
- progress entry
- result sync
- default source trace dataset-driven

### E. Verifikasi staging Slice B
```bash
git diff --cached --stat
git diff --cached -- app/modules/analytics/models.py
git diff --cached -- app/modules/analytics/services.py
git diff --cached -- tests/test_analytics_indicator_service_behaviors.py
```

### F. Test minimum sebelum commit Slice B
```bash
docker exec -w /usr/src/app dasborkanwil_app sh -lc 'PYTHONPATH=/usr/src/app pytest tests/test_analytics_indicator_models.py tests/test_analytics_indicator_definition_migration.py tests/test_analytics_indicator_service_contracts.py tests/test_analytics_indicator_service_behaviors.py -q'
```

Kalau mau lebih aman, jalankan targeted definition-only secara manual setelah patch staging selesai.

### G. Commit Slice B
```bash
git commit -m "feat: add analytics indicator definition layer and service contracts"
```

---

## 4. Slice C — result/progress execution layer + API workspace + web mockup

## 4.1. Boundary slice C
Fokus pada:
- `analytics_indicator_results`
- `analytics_indicator_progress_entries`
- `analytics_indicator_progress_items`
- service result/progress/query
- API analytics workspace
- web analytics workspace
- mockup UI tabs
- bootstrap registration di `app/__init__.py`

### Class boundary yang masuk Slice C
File: `app/modules/analytics/models.py`
- `AnalyticsIndicatorResult` (mulai sekitar line 645)
- `AnalyticsIndicatorProgressEntry` (sekitar line 701)
- `AnalyticsIndicatorProgressItem` (sekitar line 753)

### Service boundary yang masuk Slice C
File: `app/modules/analytics/services.py`
- `AnalyticsIndicatorResultService` (mulai line 249)
- `AnalyticsQueryService` (mulai line 375)

### Behavior test yang masuk Slice C
File: `tests/test_analytics_indicator_service_behaviors.py`
Masuk Slice C:
- `test_record_progress_entry_with_items_and_sync_result_updates_narrative_without_losing_dataset_trace()`
- `test_record_result_for_dataset_driven_indicator_builds_default_source_trace()`

---

## 4.2. Stage command Slice C

### A. Stage file penuh
```bash
git add \
  app/__init__.py \
  app/api/v1/analytics/__init__.py \
  app/api/v1/analytics/routes.py \
  app/modules/analytics/routes_web.py \
  app/templates/pages/analytics/workspace.html \
  app/src/js/pages/analytics-workspace.js \
  migrations/versions/c8f2d3e4a5b6_add_analytics_indicator_results_and_progress_v1.py \
  tests/test_analytics_indicator_result_migration.py \
  tests/test_api_analytics_routes.py \
  tests/test_analytics_web_routes.py
```

### B. Stage sisa hunk `models.py`
```bash
git add -p app/modules/analytics/models.py
```

Stage sisa hunk result/progress:
- `AnalyticsIndicatorResult`
- `AnalyticsIndicatorProgressEntry`
- `AnalyticsIndicatorProgressItem`

### C. Stage sisa hunk `services.py`
```bash
git add -p app/modules/analytics/services.py
```

Stage sisa hunk:
- `AnalyticsIndicatorResultService`
- `AnalyticsQueryService`

### D. Stage sisa hunk behavior tests
```bash
git add -p tests/test_analytics_indicator_service_behaviors.py
```

Stage sisa test:
- progress entry + sync result
- record result dataset-driven trace

### E. Verifikasi staging Slice C
```bash
git diff --cached --stat
git diff --cached -- app/__init__.py
```

### F. Test minimum sebelum commit Slice C
```bash
docker exec -w /usr/src/app dasborkanwil_app sh -lc 'PYTHONPATH=/usr/src/app pytest tests/test_analytics_indicator_result_migration.py tests/test_analytics_indicator_service_behaviors.py tests/test_api_analytics_routes.py tests/test_analytics_web_routes.py -q'
```

Kalau mau paling aman setelah itu lanjut:
```bash
docker exec -w /usr/src/app dasborkanwil_app sh -lc 'PYTHONPATH=/usr/src/app pytest tests/ -q'
```

### G. Commit Slice C
```bash
git commit -m "feat: add analytics workspace vertical slice for results and progress"
```

---

## 5. Checklist cepat sebelum menekan commit

Untuk setiap slice, cek:

```bash
git status --short
git diff --cached --stat
git diff --cached
```

Pastikan:
- Slice A tidak ikut report/indicator dynamic layer
- Slice B belum ikut API/web workspace/result-progress
- Slice C memang berisi vertical slice eksekusi + workspace

---

## 6. Rekomendasi praktis untuk sesi commit sekarang

Kalau mau paling pragmatis bro:
1. commit Slice A dulu persis sesuai plan ini
2. commit Slice B dengan `git add -p` pada `models.py`, `services.py`, `test_analytics_indicator_service_behaviors.py`
3. commit Slice C dengan sisa hunk yang belum staged

Kalau saat `git add -p` ternyata hunk `models.py` atau `services.py` terlalu menyatu dan sulit di-split otomatis:
- pakai `s` dulu
- kalau masih gagal, pakai `e` dan edit patch manual
- kalau tetap terlalu ribet, opsi fallback paling aman adalah pecah file tersebut di working tree pada sesi terpisah, tapi untuk saat ini plan ini masih feasible tanpa refactor tambahan

---

## 7. Commit order final

```bash
feat: add analytics dataset foundation v1
feat: add analytics indicator definition layer and service contracts
feat: add analytics workspace vertical slice for results and progress
```

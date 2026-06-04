# Domain 5 — Migration Schema Plan v1

Dokumen ini adalah Turn C untuk menurunkan `domain-5-schema-contract-v1.md` menjadi rencana migration schema yang siap diimplementasikan pelan-pelan.

Dokumen induk terkait:
- `docs/architecture/domain-5-transition-and-boundary-audit-v1.md`
- `docs/architecture/domain-5-blueprint-v1.md`
- `docs/architecture/domain-5-schema-contract-v1.md`

Fokus Turn C:
- mengunci strategi migration awal Domain 5,
- menerjemahkan kontrak tabel ke bentuk SQLAlchemy/Alembic yang realistis untuk repo ini,
- mengunci urutan implementasi migration + model + test,
- mengidentifikasi keputusan teknis yang sebaiknya dipastikan sebelum mulai coding.

Bukan fokus Turn C:
- service refresh penuh,
- executor query dataset,
- chart/dashboard,
- background worker.

---

## 1. Audit singkat kondisi repo saat ini

Dari audit codebase saat ini:
- belum ada modul `analytics` di `app/modules/`
- head migration aktif saat ini berada di:
  - `c4d7a9e2b1f0_backfill_data_registry_materialization_metadata.py`
- pola model domain 2-4 sudah cukup konsisten:
  - integer PK + `uuid` string 36
  - `created_at`, `updated_at`, `deleted_at`
  - audit actor `created_by/_uuid`, `updated_by/_uuid`, `deleted_by/_uuid`
  - enum masih diwujudkan sebagai `String(...)` + check constraint, bukan native PostgreSQL ENUM
  - JSON fleksibel menggunakan `JSONB`
- migration Domain 4 sudah menunjukkan pola penting yang bisa kita tiru:
  - `op.create_table(...)`
  - index biasa via `batch_op.create_index(...)`
  - check constraint via `batch_op.create_check_constraint(...)`
  - partial unique index PostgreSQL via `op.create_index(..., unique=True, postgresql_where=...)`

Kesimpulan audit:
- Domain 5 v1 enak dimulai dengan satu migration baru yang menambahkan tiga tabel fondasi sekaligus.
- Secara gaya implementasi, Domain 5 sebaiknya mengikuti pola Domain 3-4, bukan memperkenalkan gaya baru yang terlalu berbeda.

---

## 2. Keputusan teknis utama yang dikunci di Turn C

### 2.1. Satu migration foundation dulu
Untuk Domain 5 v1, paling sehat kita buat satu migration foundation yang langsung menambahkan:
1. `analytics_datasets`
2. `analytics_dataset_versions`
3. `analytics_dataset_runs`

Alasan:
- ketiga tabel ini satu paket kontrak inti
- belum ada data legacy Domain 5 yang perlu di-backfill
- lebih mudah diverifikasi sebagai satu foundation utuh

Nama migration yang direkomendasikan:
- `add_analytics_dataset_foundation_v1`

`down_revision` yang direkomendasikan:
- `c4d7a9e2b1f0`

### 2.2. Jangan pakai native PostgreSQL ENUM dulu
Rekomendasi: tetap pakai `String(...)` + check constraint.

Alasan:
- konsisten dengan pola repo sekarang
- lebih ramah untuk testing `sqlite:///:memory:`
- migration lebih sederhana dan lebih mudah diubah di fase greenfield ini

### 2.3. JSONB tetap dipakai strategis
JSONB dipakai untuk field kontrak yang bentuknya memang fleksibel:
- `settings_json`
- `tags_json`
- `source_contract_json`
- `query_spec_json`
- `transform_spec_json`
- `join_registry_spec_json`
- `output_schema_json`
- `dimension_definitions_json`
- `metric_definitions_json`
- `default_filters_json`
- `sort_spec_json`
- `freshness_policy_json`
- `requested_filters_json`
- `source_snapshot_json`
- `result_schema_json`
- `result_preview_json`
- `summary_json`
- `error_detail_json`

Field yang sering dipakai list/filter/index tetap relasional biasa.

### 2.4. Domain 5 v1 tidak butuh backfill data
Karena Domain 5 masih greenfield:
- migration awal cukup create table + constraint + index
- seed contoh dataset nanti lebih tepat dilakukan di layer service/seeder/test, bukan di migration foundation

---

## 3. Struktur modul kode yang direkomendasikan

Supaya metadata SQLAlchemy kebaca jelas dan nanti service mudah tumbuh, struktur awal yang direkomendasikan:

```text
app/modules/analytics/
├── __init__.py
├── models.py
├── repositories.py        # boleh tipis dulu / menyusul jika perlu
└── services.py            # boleh tipis dulu / menyusul jika perlu
```

Untuk slice coding pertama, minimal yang wajib ada:
- `app/modules/analytics/models.py`
- import model itu di `app/__init__.py`

Kalau belum mau membuat repository/service penuh, itu masih aman.
Yang penting migration autogenerate/manual bisa melihat metadata model-nya.

---

## 4. Rencana tabel 1 — `analytics_datasets`

### 4.1. Peran tabel
Tabel ini adalah identitas dataset.
Satu row = satu dataset analitik yang dikenali sistem.

Contoh:
- `submission_volume_by_form_year`

### 4.2. Kolom yang direkomendasikan

```text
id                           Integer PK
uuid                         String(36) unique not null
dataset_key                  String(150) unique not null
name                         String(255) not null
description                  Text nullable
source_domain                String(50) not null
source_type                  String(80) not null
primary_source_ref           String(255) nullable
status                       String(30) not null default 'draft'
is_active                    Boolean not null default true
is_year_scoped               Boolean not null default true
default_reporting_year_mode  String(30) not null default 'active_year'
owner_scope_type             String(50) nullable
owner_scope_code             String(100) nullable
owner_scope_name             String(255) nullable
owner_scope_path             JSONB not null default []
settings_json                JSONB not null default {}
tags_json                    JSONB not null default []
created_at                   DateTime(timezone=True) not null
updated_at                   DateTime(timezone=True) not null
deleted_at                   DateTime(timezone=True) nullable
created_by                   FK users.id nullable
created_by_uuid              String(36) nullable
updated_by                   FK users.id nullable
updated_by_uuid              String(36) nullable
deleted_by                   FK users.id nullable
deleted_by_uuid              String(36) nullable
```

### 4.3. Constraint yang direkomendasikan
- unique `uuid`
- unique `dataset_key`
- check `status in ('draft', 'active', 'archived')`
- check `source_domain in ('submission', 'data_registry', 'hybrid')`
- check `source_type in ('submission_fact', 'published_registry_dimension', 'aggregated_submission_fact', 'hybrid_fact_dimension')`
- check `default_reporting_year_mode in ('active_year', 'explicit', 'all_time')`

### 4.4. Index yang direkomendasikan
- index `status`
- index `is_active`
- index `source_domain`
- index `source_type`
- index `is_year_scoped`
- index `owner_scope_code`
- index `deleted_at`

### 4.5. Catatan implementasi
- `dataset_key` sebaiknya snake_case stabil
- `owner_scope_path`, `settings_json`, `tags_json` diberi server default JSON kosong agar row awal tidak null-heavy
- secara naming model, sebaiknya field JSON konsisten diberi suffix `_json` karena di domain lain nama JSONB masih campur; untuk Domain 5 mending rapi dari awal

---

## 5. Rencana tabel 2 — `analytics_dataset_versions`

### 5.1. Peran tabel
Tabel ini adalah resep versi dataset.
Satu row = satu versi kontrak analitik.

### 5.2. Kolom yang direkomendasikan

```text
id                           Integer PK
uuid                         String(36) unique not null
dataset_id                   FK analytics_datasets.id not null
version_number               Integer not null
status                       String(30) not null default 'draft'
is_current_draft             Boolean not null default true
is_current_published         Boolean not null default false
source_contract_json         JSONB not null default {}
query_spec_json              JSONB not null default {}
transform_spec_json          JSONB not null default {}
join_registry_spec_json      JSONB not null default []
grain_key                    String(60) not null
output_schema_json           JSONB not null default []
dimension_definitions_json   JSONB not null default []
metric_definitions_json      JSONB not null default []
default_filters_json         JSONB not null default {}
sort_spec_json               JSONB not null default []
freshness_source_type        String(80) not null
freshness_source_ref         String(255) nullable
freshness_strategy           String(50) not null
freshness_policy_json        JSONB not null default {}
publish_notes                Text nullable
published_at                 DateTime(timezone=True) nullable
created_at                   DateTime(timezone=True) not null
updated_at                   DateTime(timezone=True) not null
deleted_at                   DateTime(timezone=True) nullable
created_by                   FK users.id nullable
created_by_uuid              String(36) nullable
updated_by                   FK users.id nullable
updated_by_uuid              String(36) nullable
deleted_by                   FK users.id nullable
deleted_by_uuid              String(36) nullable
```

### 5.3. Constraint yang direkomendasikan
- unique `uuid`
- unique (`dataset_id`, `version_number`)
- check `status in ('draft', 'published', 'archived')`
- check `grain_key in ('per_submission', 'per_form_per_year', 'per_scope_per_year', 'per_registry_record_per_year')`
- check `freshness_source_type in ('submissions.submitted_at', 'data_registry_versions.materialized_at', 'hybrid_watermark')`
- check `freshness_strategy in ('max_timestamp', 'source_watermark_compare', 'manual_assertion')`
- check `NOT (is_current_draft AND is_current_published)`
- check `(is_current_published = false) OR (status = 'published')`
- check `(published_at IS NULL) OR (status IN ('published', 'archived'))`

### 5.4. Index yang direkomendasikan
- index (`dataset_id`, `status`)
- index `is_current_draft`
- index `is_current_published`
- index `grain_key`
- index `freshness_source_type`
- index `freshness_strategy`
- index `published_at`
- index `deleted_at`

### 5.5. Partial unique index yang direkomendasikan
Ini penting untuk rule current draft/current published tunggal.

1. satu current draft per dataset
- nama index yang direkomendasikan:
  - `ux_analytics_dataset_versions_one_current_draft_per_dataset`
- kondisi:
  - `is_current_draft = true AND deleted_at IS NULL`

2. satu current published per dataset
- nama index yang direkomendasikan:
  - `ux_analytics_dataset_versions_one_current_published_per_dataset`
- kondisi:
  - `is_current_published = true AND deleted_at IS NULL`

Catatan penting:
- di migration Alembic, minimal kita perlu `postgresql_where=...`
- di level model SQLAlchemy, kalau mau constraint ini ikut terwakili saat create_all/testing, bagus bila ditambah juga `sqlite_where=...` sejauh kompatibel
- kalau ternyata `sqlite_where` belum nyaman di stack saat ini, constraint final tetap dijaga oleh migration PostgreSQL + service layer test

### 5.6. Keputusan penting tentang integritas relasi ke run
Agar tabel `analytics_dataset_runs` bisa membuktikan bahwa `dataset_version_id` memang milik `dataset_id` yang sama, aku rekomendasikan tambahan ini pada `analytics_dataset_versions`:
- unique constraint (`id`, `dataset_id`)

Secara logika memang `id` sudah PK dan unik sendiri.
Tapi pasangan (`id`, `dataset_id`) tetap berguna sebagai target composite foreign key dari tabel run.

Ini keputusan kecil tapi sangat berharga karena:
- integritas `run.dataset_id` vs `run.dataset_version_id` bisa dijaga di level database,
- kita tidak hanya mengandalkan service layer.

---

## 6. Rencana tabel 3 — `analytics_dataset_runs`

### 6.1. Peran tabel
Tabel ini menyimpan histori eksekusi refresh dataset.
Satu row = satu run.

### 6.2. Kolom yang direkomendasikan

```text
id                           Integer PK
uuid                         String(36) unique not null
dataset_id                   Integer not null
dataset_version_id           Integer not null
run_key                      String(255) unique not null
trigger_type                 String(30) not null
trigger_ref                  String(255) nullable
requested_reporting_year     Integer nullable
requested_reporting_period_id FK reporting_periods.id nullable
requested_filters_json       JSONB not null default {}
status                       String(30) not null default 'queued'
started_at                   DateTime(timezone=True) nullable
finished_at                  DateTime(timezone=True) nullable
duration_ms                  BigInteger nullable
source_watermark             String(255) nullable
freshness_status             String(30) not null default 'unknown'
source_snapshot_json         JSONB not null default {}
freshness_evaluated_at       DateTime(timezone=True) nullable
result_row_count             BigInteger nullable
result_schema_json           JSONB not null default []
result_preview_json          JSONB not null default []
materialization_ref          String(255) nullable
summary_json                 JSONB not null default {}
error_code                   String(100) nullable
error_message                Text nullable
error_detail_json            JSONB not null default {}
created_at                   DateTime(timezone=True) not null
updated_at                   DateTime(timezone=True) not null
deleted_at                   DateTime(timezone=True) nullable
created_by                   FK users.id nullable
created_by_uuid              String(36) nullable
updated_by                   FK users.id nullable
updated_by_uuid              String(36) nullable
deleted_by                   FK users.id nullable
deleted_by_uuid              String(36) nullable
```

### 6.3. Foreign key yang direkomendasikan
Minimal:
- `dataset_id -> analytics_datasets.id`
- `requested_reporting_period_id -> reporting_periods.id`

Lalu untuk relasi versi, rekomendasi terbaiknya bukan hanya FK tunggal ke `analytics_dataset_versions.id`, tetapi:
- composite foreign key (`dataset_version_id`, `dataset_id`) -> `analytics_dataset_versions (id, dataset_id)`

Alasan:
- ini menjaga rule penting bahwa run harus menunjuk ke versi milik dataset yang sama
- lebih kuat daripada hanya validasi di service

Kalau implementasi composite FK ini terasa ribet saat autogenerate, tetap layak dibuat manual di migration.
Justru menurutku ini salah satu value utama Turn C.

### 6.4. Constraint yang direkomendasikan
- unique `uuid`
- unique `run_key`
- check `trigger_type in ('manual', 'preview', 'publish_hook', 'cron', 'system')`
- check `status in ('queued', 'running', 'succeeded', 'failed', 'cancelled')`
- check `freshness_status in ('unknown', 'fresh', 'stale', 'failed')`
- check `(duration_ms IS NULL) OR (duration_ms >= 0)`
- check `(started_at IS NULL OR finished_at IS NULL OR finished_at >= started_at)`
- check `(status != 'succeeded') OR (started_at IS NOT NULL)`
- check `(status != 'failed') OR (error_message IS NOT NULL)`

### 6.5. Index yang direkomendasikan
- index `dataset_id`
- index `dataset_version_id`
- index `trigger_type`
- index `status`
- index `started_at`
- index `finished_at`
- index `requested_reporting_year`
- index `requested_reporting_period_id`
- index `freshness_status`
- index `materialization_ref`
- index `deleted_at`

### 6.6. Catatan desain penting
Kenapa `dataset_id` tetap disimpan di tabel run, padahal sudah ada `dataset_version_id`?

Jawabannya:
- memudahkan query monitoring/list tanpa join dulu ke version,
- memudahkan partitioning/filtering logis nanti,
- mempermudah integrasi dashboard admin dataset,
- dan dengan composite FK tadi, kita tetap aman dari mismatch.

Jadi `dataset_id` di run bukan redundansi liar, tapi redundansi yang disengaja dan terjaga.

---

## 7. Naming constraint dan check string yang direkomendasikan

Agar migration rapi dan mudah dibaca, aku sarankan kita pakai konstanta string check seperti pola Domain 4.

Contoh nama konstanta di file migration:
- `ANALYTICS_DATASET_STATUS_CHECK`
- `ANALYTICS_SOURCE_DOMAIN_CHECK`
- `ANALYTICS_SOURCE_TYPE_CHECK`
- `ANALYTICS_DEFAULT_REPORTING_YEAR_MODE_CHECK`
- `ANALYTICS_DATASET_VERSION_STATUS_CHECK`
- `ANALYTICS_GRAIN_KEY_CHECK`
- `ANALYTICS_FRESHNESS_SOURCE_TYPE_CHECK`
- `ANALYTICS_FRESHNESS_STRATEGY_CHECK`
- `ANALYTICS_RUN_TRIGGER_TYPE_CHECK`
- `ANALYTICS_RUN_STATUS_CHECK`
- `ANALYTICS_FRESHNESS_STATUS_CHECK`

Contoh nama constraint yang direkomendasikan:
- `ck_analytics_datasets_status_valid`
- `ck_analytics_datasets_source_domain_valid`
- `ck_analytics_datasets_source_type_valid`
- `ck_analytics_datasets_default_reporting_year_mode_valid`
- `ck_analytics_dataset_versions_status_valid`
- `ck_analytics_dataset_versions_grain_key_valid`
- `ck_analytics_dataset_versions_freshness_source_type_valid`
- `ck_analytics_dataset_versions_freshness_strategy_valid`
- `ck_analytics_dataset_versions_publish_state_valid`
- `ck_analytics_dataset_runs_trigger_type_valid`
- `ck_analytics_dataset_runs_status_valid`
- `ck_analytics_dataset_runs_freshness_status_valid`
- `ck_analytics_dataset_runs_duration_non_negative`
- `ck_analytics_dataset_runs_finished_after_started`

---

## 8. Strategi implementasi Alembic yang direkomendasikan

### 8.1. Urutan create table
Urutan paling aman:
1. create `analytics_datasets`
2. create `analytics_dataset_versions`
3. create index/constraint tambahan versi
4. create `analytics_dataset_runs`
5. create index/constraint tambahan run

Alasan:
- `analytics_dataset_versions` butuh `analytics_datasets`
- `analytics_dataset_runs` butuh `analytics_dataset_versions`
- composite FK run lebih enak dibuat setelah versi final tersedia

### 8.2. Partial unique index dibuat manual
Untuk index partial current draft/current published, lebih aman dibuat eksplisit manual di migration, misalnya:
- `op.create_index(... unique=True, postgresql_where=sa.text(...))`

Jangan berharap autogenerate selalu menulisnya persis seperti yang kita mau.

### 8.3. Downgrade harus simetris
Urutan downgrade paling aman:
1. drop index partial tabel run jika ada tambahan spesial
2. drop `analytics_dataset_runs`
3. drop index partial tabel version
4. drop `analytics_dataset_versions`
5. drop `analytics_datasets`

---

## 9. Rencana model SQLAlchemy yang direkomendasikan

### 9.1. Konvensi model
Ikuti pola yang sama dengan domain lain:
- `from sqlalchemy.dialects.postgresql import JSONB`
- `from sqlalchemy.sql import func`
- `uuid default=lambda: str(uuid.uuid4())`
- `created_at default=func.now()`
- `updated_at default=func.now(), onupdate=func.now()`

### 9.2. Relationship yang direkomendasikan

Pada `AnalyticsDataset`:
- `versions = relationship('AnalyticsDatasetVersion', back_populates='dataset', ...)`
- `runs = relationship('AnalyticsDatasetRun', back_populates='dataset', ...)`

Pada `AnalyticsDatasetVersion`:
- `dataset = relationship('AnalyticsDataset', back_populates='versions', lazy='joined')`
- `runs = relationship('AnalyticsDatasetRun', back_populates='dataset_version', ...)`

Pada `AnalyticsDatasetRun`:
- `dataset = relationship('AnalyticsDataset', back_populates='runs', lazy='joined')`
- `dataset_version = relationship('AnalyticsDatasetVersion', back_populates='runs', lazy='joined')`
- `requested_reporting_period = relationship('ReportingPeriod', lazy='joined')`

### 9.3. Konstanta enum di model
Supaya service/test nanti tidak memakai string liar, sebaiknya model punya konstanta baseline, misalnya:
- `STATUS_DRAFT`, `STATUS_ACTIVE`, `STATUS_ARCHIVED`
- `SOURCE_DOMAIN_SUBMISSION`, dst
- `GRAIN_PER_FORM_PER_YEAR`, dst
- `RUN_STATUS_QUEUED`, dst

Ini kecil, tapi akan mengurangi typo saat Domain 5 mulai tumbuh.

---

## 10. Rencana test yang direkomendasikan

Turn C belum coding, tapi migration plan akan lebih sehat kalau dari sekarang kita kunci test target-nya.

### 10.1. Test model contract minimum
File kandidat:
- `tests/test_analytics_models.py`

Target minimal:
1. `AnalyticsDataset` bisa dibuat dengan default yang sehat
2. `AnalyticsDatasetVersion` terhubung ke dataset
3. `AnalyticsDatasetRun` terhubung ke dataset + version
4. relationship dasar berjalan
5. nilai default JSON bukan null

### 10.2. Test constraint helper / migration contract
Karena beberapa rule database-level sulit diverifikasi penuh di sqlite memory, aku sarankan dua lapis:

1. test struktur model / metadata
- memastikan unique/index/constraint terdaftar secara bentuk

2. test migration helper bila ada logika manual
- misalnya bila kita menambahkan helper constant atau builder kecil di migration file

### 10.3. Test integritas service-level awal
Saat nanti masuk Turn D/coding, target test minimum:
1. unique `dataset_key`
2. unique (`dataset_id`, `version_number`)
3. hanya satu current draft per dataset
4. hanya satu current published per dataset
5. run tidak boleh mismatch dataset vs version

Poin 5 idealnya dibuktikan dua kali:
- database-level via composite FK
- service-level via validation eksplisit

---

## 11. Keputusan penting yang menurutku paling bernilai

Kalau aku ringkas, ada 4 keputusan Turn C yang paling penting:

1. Domain 5 foundation cukup satu migration baru
- belum perlu dipecah-pecah dulu

2. tetap pakai string + check constraint
- jangan lompat ke native ENUM

3. `analytics_dataset_runs` menyimpan `dataset_id` dan `dataset_version_id`
- tapi mismatch-nya dijaga dengan composite FK

4. partial unique current draft/current published wajib ada sejak awal
- jangan ditunda ke service saja

Empat hal ini kalau dikunci sekarang, coding nanti bakal jauh lebih tenang.

---

## 12. Urutan eksekusi setelah Turn C

Kalau habis ini kita lanjut ke eksekusi, urutan paling sehat menurutku:

### Step 1
Buat model file awal:
- `app/modules/analytics/models.py`

### Step 2
Register import model di:
- `app/__init__.py`

### Step 3
Buat test RED awal:
- `tests/test_analytics_models.py`

### Step 4
Generate / tulis migration baru:
- `migrations/versions/<revision>_add_analytics_dataset_foundation_v1.py`

### Step 5
Verifikasi migration di container app
- `flask db heads`
- `flask db upgrade`
- cek tidak muncul multiple head yang tidak sengaja

### Step 6
Tambah test perilaku awal untuk publish version / create run bila kita langsung lanjut ke service layer

---

## 13. Kesimpulan praktis Turn C

Kalau dijelaskan paling simpel:
- Turn A mengunci blueprint Domain 5
- Turn B mengunci kontrak tabel
- Turn C sekarang mengunci cara kontrak itu ditanam ke database proyek ini

Dan hasil paling pentingnya adalah:
- kita sudah tahu tiga tabel awal apa saja
- kita sudah tahu bentuk kolom, constraint, dan index-nya
- kita sudah tahu migration sebaiknya satu paket foundation
- kita sudah tahu titik rawan yang harus dijaga:
  - partial unique current draft/current published
  - konsistensi `run.dataset_id` vs `run.dataset_version_id`
  - tetap membedakan freshness source vs freshness hasil run

Menurutku habis ini kita sudah siap masuk Turn D versi eksekusi:
- implement model + migration + test RED/GREEN tipis untuk fondasi Domain 5.

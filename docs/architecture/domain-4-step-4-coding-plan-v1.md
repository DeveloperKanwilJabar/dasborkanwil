# Domain 4 — Step 4 Coding Plan v1

> Untuk Hermes: saat plan ini dieksekusi nanti, tetap ikuti TDD kecil-per-kecil dan jaga agar test Domain 4 existing tidak rusak.

Goal: memecah Step 4 Domain 4 menjadi rencana implementasi coding yang konkret, evaluable, dan tipis untuk tiga jalur kerja berikut:
1. migration foundation,
2. contract tests,
3. coding irisan pertama import workflow generik non-wilayah.

Architecture: kita tidak memulai dari nol, karena repo sudah punya fondasi Domain 4 untuk registry/version/record wilayah serta consumer query service. Jadi slice berikutnya harus menumpang di struktur existing `models -> repositories -> services -> api routes -> tests`, lalu menambahkan dua entity operasional baru (`data_registry_import_batches`, `data_registry_import_rows`) tanpa mengganggu alur published registry resource yang sudah berjalan.

Tech stack: Flask, Flask-SQLAlchemy, Alembic, PostgreSQL JSONB, pytest, API v1 internal, Docker container `dasborkanwil_app`.

---

## 1. Scope yang dikunci untuk irisan pertama

Agar evaluasinya enak dan implementasinya tidak brutal, irisan pertama Step 4 kita batasi ke alur berikut:

1. membuat import batch ke target `data_registry_versions` yang masih draft,
2. menyimpan staged rows ke `data_registry_import_rows`,
3. menyimpan `mapping_snapshot`, `source_headers`, dan `source_snapshot` di batch,
4. menjalankan validasi sinkron berbasis `schema_json.fields`,
5. melakukan normalisasi tipe dasar, terutama `date` / `datetime`,
6. menandai status row (`mapped`, `valid`, `error`, `duplicate`, `skipped`) dan ringkasan batch,
7. menyediakan API tipis untuk:
   - create batch
   - get batch detail
   - validate batch
   - list rows by status

Dengan batas ini, kita sudah bisa menguji inti arsitektur import generik tanpa harus langsung masuk ke:
- upload file beneran ke storage,
- parser XLSX/CSV penuh,
- materialize ke `data_registry_records`,
- error workbook,
- publish final.

Itu semua tetap valid sebagai langkah sesudah slice ini stabil.

---

## 2. Kenapa irisan pertama ini yang paling aman

Karena saat ini codebase sudah punya:
- `DataRegistry`, `DataRegistryVersion`, `DataRegistryRecord`
- query/published consumer API untuk wilayah
- materialization service wilayah
- test service/query/API dasar Domain 4

Yang belum ada untuk generic import workflow adalah lapisan staging. Maka irisan pertama paling sehat adalah menambah staging layer dulu, bukan langsung file parser atau worker.

Secara arsitektur, ini sejalan dengan keputusan dokumen induk:
- entity baru prioritas: `data_registry_import_batches` dan `data_registry_import_rows`
- normalisasi tanggal adalah concern inti
- publish tetap eksplisit di step lanjutan

---

## 3. Deliverable akhir plan ini

Kalau plan ini nanti dieksekusi sampai selesai, hasil minimal yang harus terlihat adalah:

1. model baru untuk `data_registry_import_batches` dan `data_registry_import_rows` sudah ada,
2. migration Alembic untuk dua tabel itu sudah ada dan bisa di-upgrade,
3. repository/service contract import sudah terkunci oleh test,
4. ada behavior test untuk create batch + validate batch + date normalization,
5. ada API v1 tipis untuk create/detail/validate/list rows,
6. seluruh test Domain 4 existing tetap hijau,
7. test baru untuk slice import juga hijau.

---

## 4. File yang akan disentuh

### 4.1. File existing yang hampir pasti diubah

- `/home/user/projects/dasborkanwil/app/modules/data_registry/models.py`
- `/home/user/projects/dasborkanwil/app/modules/data_registry/repositories.py`
- `/home/user/projects/dasborkanwil/app/modules/data_registry/services.py`
- `/home/user/projects/dasborkanwil/app/api/v1/data_registries/routes.py`
- `/home/user/projects/dasborkanwil/tests/test_data_registry_models.py`
- `/home/user/projects/dasborkanwil/tests/test_data_registry_service_contracts.py`
- `/home/user/projects/dasborkanwil/tests/test_api_data_registry_routes.py`

### 4.2. File baru yang direkomendasikan

- `/home/user/projects/dasborkanwil/migrations/versions/<new_revision>_add_data_registry_import_batches_and_rows.py`
- `/home/user/projects/dasborkanwil/tests/test_data_registry_import_service_behaviors.py`
- `/home/user/projects/dasborkanwil/tests/test_api_data_registry_import_routes.py`
- opsional bila ingin memisahkan concern test lebih rapi:
  - `/home/user/projects/dasborkanwil/tests/test_data_registry_import_postgres_integration.py`

Catatan:
- kalau user ingin file test tetap sedikit, behavior/API import boleh ditambahkan ke file test Domain 4 yang sudah ada.
- tapi untuk evaluasi yang nyaman, aku lebih condong memisahkan file test import baru agar boundary slice ini jelas.

---

## 5. Kontrak data yang dikunci untuk migration v1

## 5.1. `data_registry_import_batches`

Kolom minimum yang direkomendasikan untuk irisan pertama:
- `id`
- `uuid`
- `registry_id`
- `registry_version_id`
- `batch_type` (`file_upload`, `manual_seed`, `submission_refresh`, `source_refresh`)
- `status` (`uploaded`, `mapped`, `validating`, `validated`, `failed`, `cancelled`)
- `original_filename` nullable
- `mime_type` nullable
- `reporting_year` nullable
- `total_rows`
- `mapped_rows`
- `valid_rows`
- `error_rows`
- `duplicate_rows`
- `skipped_rows`
- `mapping_snapshot` JSONB
- `source_headers` JSONB
- `source_snapshot` JSONB
- `validation_summary` JSONB
- `created_at`
- `updated_at`
- `deleted_at`
- `created_by`, `created_by_uuid`, `updated_by`, `updated_by_uuid`, `deleted_by`, `deleted_by_uuid`

Sengaja belum wajib di slice pertama:
- `source_id`
- `mapping_id`
- `reporting_period_id`
- `materialization_summary`
- `error_workbook_path`

## 5.2. `data_registry_import_rows`

Kolom minimum yang direkomendasikan untuk irisan pertama:
- `id`
- `uuid`
- `import_batch_id`
- `row_number`
- `row_hash`
- `status` (`pending`, `mapped`, `valid`, `error`, `duplicate`, `skipped`)
- `record_key_candidate` nullable
- `record_code_candidate` nullable
- `duplicate_of_row_id` nullable
- `raw_payload` JSONB
- `mapped_payload` JSONB
- `normalized_payload` JSONB
- `validation_errors` JSONB
- `validation_warnings` JSONB
- `lineage_snapshot` JSONB
- `created_at`
- `updated_at`

Sengaja belum wajib di slice pertama:
- `target_record_id`
- `source_updated_at`
- audit actor penuh pada level row

Alasan: row-level actor audit untuk staging rows bisa ditambahkan nanti bila memang dibutuhkan. Untuk slice awal, batch-level actor audit sudah cukup informatif.

---

## 6. Kontrak service yang dikunci untuk irisan pertama

### 6.1. Repository baru

Tambahkan di `app/modules/data_registry/repositories.py`:

1. `DataRegistryImportBatchRepository`
   - `get_by_id(batch_id)`
   - `list_by_registry_version(registry_version_id)`
   - `save(batch)`

2. `DataRegistryImportRowRepository`
   - `bulk_create(rows)`
   - `list_by_batch(import_batch_id, status=None)`
   - `count_by_batch_and_status(import_batch_id)` atau helper ringkasan serupa
   - `save(row)`

### 6.2. Service baru/lanjutan

Tambahkan di `app/modules/data_registry/services.py`:

1. `DataRegistryImportBatchService`
   - `create_batch(registry_version_id, payload, actor=None)`
   - `get_batch_detail(batch_id)`
   - `list_batch_rows(batch_id, status=None)`

2. `DataRegistryImportValidationService`
   - `validate_batch(batch_id, actor=None)`
   - helper internal:
     - `_normalize_field_value(field_contract, raw_value, mapping_rule)`
     - `_normalize_date(...)`
     - `_normalize_datetime(...)`
     - `_build_validation_summary(...)`

### 6.3. Kontrak perilaku yang harus dijaga

`create_batch()` minimal harus:
- menolak target version yang tidak ada,
- menolak target version yang bukan `draft`,
- menolak payload tanpa rows,
- menyimpan batch status awal `mapped` bila `mapping_snapshot` + rows langsung diberikan,
- membuat `data_registry_import_rows` dengan `raw_payload` dan `mapped_payload`,
- menghitung `row_hash`,
- mengisi counter awal `total_rows` dan `mapped_rows`.

`validate_batch()` minimal harus:
- mengubah status batch `mapped -> validating -> validated`,
- membaca `schema_json.fields` dari target version,
- mengecek required fields,
- mengecek type dasar (`string`, `integer`, `number`, `boolean`, `date`, `datetime`),
- menormalisasi field `date`/`datetime` ke format canonical,
- bila parsing gagal, menulis `validation_errors` yang eksplisit,
- mendeteksi duplicate intra-batch berdasarkan candidate key/code bila rule tersedia,
- meng-update counter `valid_rows`, `error_rows`, `duplicate_rows`, `skipped_rows`,
- menyimpan `validation_summary` di batch.

---

## 7. Kontrak API yang dikunci untuk irisan pertama

Tambahkan endpoint baru di `app/api/v1/data_registries/routes.py`:

1. `POST /api/v1/data-registry-versions/<version_id>/import-batches`
   - membuat batch + staged rows

2. `GET /api/v1/data-registry-import-batches/<batch_id>`
   - mengambil detail batch

3. `POST /api/v1/data-registry-import-batches/<batch_id>/validate`
   - menjalankan validasi sinkron

4. `GET /api/v1/data-registry-import-batches/<batch_id>/rows`
   - list row staging, optional filter `status`

Prinsip response:
- validation error tetap `HTTP 400` + `data.error_type='validation_error'`
- route hanya tipis: parse request, panggil service, serialize response
- jangan campur logic validasi/normalisasi di route

### 7.1. Payload minimum create batch

Contoh payload awal yang realistis untuk slice pertama:

```json
{
  "batch_type": "file_upload",
  "original_filename": "program-2026.xlsx",
  "mime_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  "reporting_year": 2026,
  "mapping_snapshot": {
    "fields": {
      "record_code": {"source": "Kode Program"},
      "label": {"source": "Nama Program"},
      "effective_date": {
        "source": "Tanggal Berlaku",
        "accepted_input_formats": ["%d/%m/%Y", "%Y-%m-%d"],
        "target_format": "%Y-%m-%d"
      }
    }
  },
  "source_headers": ["Kode Program", "Nama Program", "Tanggal Berlaku"],
  "rows": [
    {
      "Kode Program": "PRG-001",
      "Nama Program": "Program A",
      "Tanggal Berlaku": "21/05/2026"
    }
  ]
}
```

Catatan penting:
- di irisan pertama, `rows` diasumsikan sudah berupa hasil parsing file ke array of object.
- jadi kita belum mengurus upload file fisik atau parser xlsx/csv. Itu memang sengaja ditunda.

---

## 8. Urutan implementasi coding yang direkomendasikan

## Task 0 — Preflight dan proteksi baseline

Objective: memastikan kita mengerjakan slice baru di atas baseline migration/test yang benar.

Files:
- Tidak ada perubahan kode dulu.

Langkah:
1. cek migration head aktif dan pastikan hanya ada head yang diinginkan,
2. cek test Domain 4 existing dulu sebagai baseline,
3. catat command regresi utama yang akan dipakai berulang.

Command verifikasi yang direkomendasikan:
- `docker exec -w /usr/src/app dasborkanwil_app sh -lc 'PYTHONPATH=/usr/src/app pytest tests/test_data_registry_models.py tests/test_data_registry_service_contracts.py tests/test_data_registry_service_behaviors.py tests/test_api_data_registry_routes.py -q'`

Expected:
- baseline hijau sebelum slice baru masuk.

---

## Task 1 — Tulis failing contract tests untuk import batch/row

Objective: mengunci interface Python dan API dulu sebelum migration/service dirakit.

Files:
- Modify: `/home/user/projects/dasborkanwil/tests/test_data_registry_models.py`
- Modify: `/home/user/projects/dasborkanwil/tests/test_data_registry_service_contracts.py`
- Create: `/home/user/projects/dasborkanwil/tests/test_data_registry_import_service_behaviors.py`
- Create: `/home/user/projects/dasborkanwil/tests/test_api_data_registry_import_routes.py`

Step 1: model metadata test
- tambah assertion bahwa model baru punya kolom minimum sesuai section 5.

Step 2: repository/service contract test
- assertion callable untuk repository baru dan service baru.

Step 3: behavior test fail-first
Minimal skenario fail-first:
1. `create_batch()` menolak version yang bukan draft
2. `create_batch()` membuat batch dan staged rows
3. `validate_batch()` menandai row valid bila required fields lengkap
4. `validate_batch()` menandai row error bila required field kosong
5. `validate_batch()` menormalisasi `date` dari `21/05/2026` menjadi `2026-05-21`
6. `validate_batch()` memberi error eksplisit bila `31/02/2026` tidak valid
7. duplicate intra-batch pada `record_code_candidate` ditandai `duplicate`

Step 4: API route test fail-first
Minimal route yang dites:
- route registered
- success create batch
- success get batch detail
- success validate batch
- validation error standardized untuk create/validate

Command:
- `docker exec -w /usr/src/app dasborkanwil_app sh -lc 'PYTHONPATH=/usr/src/app pytest tests/test_data_registry_models.py tests/test_data_registry_service_contracts.py tests/test_data_registry_import_service_behaviors.py tests/test_api_data_registry_import_routes.py -q'`

Expected:
- FAIL, karena model/repository/service/route import belum ada.

Commit rekomendasi:
- `test: add failing contracts for Domain 4 import batch slice`

---

## Task 2 — Tambah model dan migration untuk staging layer

Objective: menurunkan kontrak entity import ke SQLAlchemy + Alembic.

Files:
- Modify: `/home/user/projects/dasborkanwil/app/modules/data_registry/models.py`
- Create: `/home/user/projects/dasborkanwil/migrations/versions/<new_revision>_add_data_registry_import_batches_and_rows.py`

Step 1: tambahkan 2 model baru
- `DataRegistryImportBatch`
- `DataRegistryImportRow`

Relationship minimum:
- `DataRegistryVersion.import_batches`
- `DataRegistryImportBatch.registry`
- `DataRegistryImportBatch.registry_version`
- `DataRegistryImportBatch.rows`
- `DataRegistryImportRow.batch`
- optional self-link `duplicate_of_row`

Step 2: tambahkan enum/check constraint di migration
Batch status yang cukup untuk slice ini:
- `uploaded`, `mapped`, `validating`, `validated`, `failed`, `cancelled`

Row status yang cukup untuk slice ini:
- `pending`, `mapped`, `valid`, `error`, `duplicate`, `skipped`

Step 3: tambahkan unique/index minimum
Rekomendasi:
- index `registry_version_id` pada batch
- index `status` pada batch
- unique `(import_batch_id, row_number)` pada row
- index `status` pada row
- index `record_code_candidate` pada row
- index `record_key_candidate` pada row

Step 4: buat migration dengan `down_revision` yang benar
Catatan penting:
- jangan tebak `down_revision`
- pastikan mengarah ke head repo saat implementasi dimulai
- setelah generate/edit migration, verifikasi tidak terjadi multiple heads tidak sengaja

Step 5: jalankan test metadata dan upgrade migration
Command contoh:
- `docker exec -w /usr/src/app dasborkanwil_app sh -lc 'flask db heads'`
- `docker exec -w /usr/src/app dasborkanwil_app sh -lc 'flask db upgrade'`
- `docker exec -w /usr/src/app dasborkanwil_app sh -lc 'PYTHONPATH=/usr/src/app pytest tests/test_data_registry_models.py tests/test_data_registry_service_contracts.py -q'`

Expected:
- metadata test mulai hijau
- behavior/API import masih merah

Commit rekomendasi:
- `feat: add Domain 4 import batch staging models and migration`

---

## Task 3 — Implement repository dan service batch creation

Objective: membuat batch dan staged rows bisa dipersist dengan aman.

Files:
- Modify: `/home/user/projects/dasborkanwil/app/modules/data_registry/repositories.py`
- Modify: `/home/user/projects/dasborkanwil/app/modules/data_registry/services.py`

Step 1: tambah repository baru
- `DataRegistryImportBatchRepository`
- `DataRegistryImportRowRepository`

Step 2: implement `create_batch()`
Perilaku minimum:
- version harus ada
- version harus `draft`
- payload `rows` tidak boleh kosong
- batch disimpan dengan status `mapped`
- row disimpan satu per satu / bulk create
- `mapped_payload` dibentuk dari `mapping_snapshot`
- `row_hash` dihitung deterministik dari `raw_payload` atau `mapped_payload`

Step 3: implement `get_batch_detail()` dan `list_batch_rows()`
Response service minimal mengembalikan:
- batch object
- counters
- summary JSONB
- rows terfilter opsional per `status`

Command:
- `docker exec -w /usr/src/app dasborkanwil_app sh -lc 'PYTHONPATH=/usr/src/app pytest tests/test_data_registry_import_service_behaviors.py -q'`

Expected:
- sebagian test create batch hijau
- test validate batch masih merah

Commit rekomendasi:
- `feat: add Domain 4 import batch creation service`

---

## Task 4 — Implement validation + date normalization

Objective: menjadikan batch bisa divalidasi dan typed field bisa dinormalisasi secara eksplisit.

Files:
- Modify: `/home/user/projects/dasborkanwil/app/modules/data_registry/services.py`
- bila helper mulai besar, boleh pecah helper internal ke file terpisah nanti, tapi untuk slice pertama masih boleh satu file selama tetap terbaca.

Step 1: implement resolver kontrak field dari `schema_json.fields`
Asumsi kontrak minimal field:
- `key`
- `type`
- `required`

Step 2: implement normalizer tipe dasar
Minimal support:
- `string`
- `integer`
- `number`
- `boolean`
- `date`
- `datetime`

Step 3: implement normalisasi date/datetime
Aturan awal yang dikunci:
- baca `accepted_input_formats` dari mapping rule bila ada
- fallback ke beberapa format aman yang sudah disepakati:
  - `%d/%m/%Y`
  - `%Y-%m-%d`
  - `%d-%m-%Y`
- output canonical:
  - `date` => `YYYY-MM-DD`
  - `datetime` => ISO-like string, mis. `YYYY-MM-DDTHH:MM:SS`
- parsing gagal => `validation_errors[field_key]`

Step 4: implement duplicate intra-batch sederhana
Aturan awal cukup:
- bila `record_code_candidate` sama antar row valid, row kedua dan seterusnya ditandai `duplicate`
- `duplicate_of_row_id` diisi bila memungkinkan

Step 5: implement `validation_summary`
Minimal isi:
- `total_rows`
- `valid_rows`
- `error_rows`
- `duplicate_rows`
- `skipped_rows`
- `field_error_counts`

Command:
- `docker exec -w /usr/src/app dasborkanwil_app sh -lc 'PYTHONPATH=/usr/src/app pytest tests/test_data_registry_import_service_behaviors.py -q'`

Expected:
- behavior test import hijau

Commit rekomendasi:
- `feat: add Domain 4 import validation and date normalization`

---

## Task 5 — Expose API v1 tipis untuk import slice

Objective: membuka kontrak HTTP minimal supaya irisan ini bisa diuji dari frontend atau Postman nantinya.

Files:
- Modify: `/home/user/projects/dasborkanwil/app/api/v1/data_registries/routes.py`
- Modify: `/home/user/projects/dasborkanwil/tests/test_api_data_registry_routes.py` bila helper serialization dipakai ulang
- Create: `/home/user/projects/dasborkanwil/tests/test_api_data_registry_import_routes.py`

Step 1: tambah serializer batch/row
Minimal field response batch:
- `id`, `uuid`, `registry_id`, `registry_version_id`
- `batch_type`, `status`, `reporting_year`
- counters
- `mapping_snapshot`, `source_headers`, `source_snapshot`, `validation_summary`

Minimal field response row:
- `id`, `row_number`, `status`
- `record_key_candidate`, `record_code_candidate`
- `mapped_payload`, `normalized_payload`
- `validation_errors`, `validation_warnings`

Step 2: implement route create batch
- validasi JSON body dasar
- panggil `DataRegistryImportBatchService.create_batch()`

Step 3: implement route detail dan rows
- panggil `get_batch_detail()` dan `list_batch_rows()`

Step 4: implement route validate
- panggil `DataRegistryImportValidationService.validate_batch()`

Step 5: pastikan standardized error mengikuti pola Domain 2-3

Command:
- `docker exec -w /usr/src/app dasborkanwil_app sh -lc 'PYTHONPATH=/usr/src/app pytest tests/test_api_data_registry_import_routes.py tests/test_api_data_registry_routes.py -q'`

Expected:
- semua test route import hijau
- route registry resource existing tetap hijau

Commit rekomendasi:
- `feat: expose Domain 4 import batch API slice`

---

## Task 6 — Regresi penuh dan evaluasi akhir slice

Objective: memastikan slice baru tidak merusak Domain 4 existing dan siap direview pelan-pelan.

Files:
- Tidak harus ada perubahan, fokus verifikasi.

Command regresi utama:
- `docker exec -w /usr/src/app dasborkanwil_app sh -lc 'PYTHONPATH=/usr/src/app pytest tests/test_data_registry_models.py tests/test_data_registry_service_contracts.py tests/test_data_registry_service_behaviors.py tests/test_data_registry_import_service_behaviors.py tests/test_api_data_registry_routes.py tests/test_api_data_registry_import_routes.py -q'`

Kalau test PostgreSQL integration juga ikut dirapikan:
- `docker exec -w /usr/src/app dasborkanwil_app sh -lc 'PYTHONPATH=/usr/src/app TEST_DATABASE_URI=<postgres-test-uri> pytest tests/test_data_registry_postgres_integration.py tests/test_data_registry_import_postgres_integration.py -q'`

Kriteria lulus evaluasi:
1. migration berhasil upgrade,
2. test import slice hijau,
3. test query/consumer wilayah existing tetap hijau,
4. date normalization terbukti lewat test,
5. duplicate intra-batch minimal terbukti lewat test,
6. route error format konsisten dengan standar proyek.

Commit rekomendasi setelah seluruh slice aman:
- `feat: add Domain 4 import batch validation slice`

---

## 9. Out of scope yang sengaja ditunda

Supaya tidak melebar, hal-hal ini jangan masuk dulu ke irisan pertama kecuali user eksplisit minta:
- parser file XLSX/CSV fisik
- upload storage nyata
- error workbook generation
- materialize ke `data_registry_records`
- publish workflow dari batch ke version
- duplicate detection versus published baseline yang kompleks
- worker async / cron orchestration
- UI web upload/mapping

---

## 10. Urutan evaluasi yang paling enak untuk user

Kalau nanti eksekusi coding dimulai, review-nya paling nyaman dibagi jadi 3 checkpoint besar:

### Checkpoint A — Migration
User review:
- nama tabel
- nama kolom
- enum/check constraints
- relasi FK
- index/unique minimum

### Checkpoint B — Contract test
User review:
- behavior apa saja yang sudah dikunci
- format error
- date normalization cases
- duplicate cases

### Checkpoint C — Thin slice code
User review:
- service boundary
- route tipis atau tidak
- response shape
- apakah implementasi masih sesuai blueprint dan belum over-engineering

---

## 11. Rekomendasi eksekusi paling waras sesudah plan ini

Kalau setelah plan ini mau langsung gas coding, aku sarankan urutan kerjanya tetap begini:
1. mulai dari Task 1 dulu, jangan lompat ke migration,
2. setelah test merah, baru Task 2 migration + model,
3. lanjut Task 3 dan 4 sampai service hijau,
4. baru Task 5 route,
5. tutup dengan Task 6 regresi penuh.

Jadi step user yang tadi diminta:
- 1. migration
- 2. contract test
- 3. coding tipis irisan pertama

secara implementasi real di lapangan tetap dijalankan dengan semangat TDD:
- tulis contract/failing test dulu,
- lalu migration/model,
- lalu code supaya hijau.

Secara engineering ini lebih aman daripada menulis migration dulu tanpa pagar test.

---

## 12. Definition of Done untuk Step 4 coding slice ini

Step 4 coding slice dianggap selesai bila:
- staging layer import generic sudah hadir,
- date/datetime normalization sudah punya behavior test,
- API minimal create/detail/validate/list rows sudah ada,
- Domain 4 existing tidak rusak,
- dan kita punya fondasi yang cukup kuat untuk next slice:
  - materialize
  - error workbook
  - publish
  - file parser/upload nyata

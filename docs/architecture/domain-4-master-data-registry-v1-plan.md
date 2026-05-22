# Domain 4 Master Data / Data Registry v1 Plan

> Draft implementasi bertahap yang tipis tetapi enterprise-minded.

## Goal

Membangun fondasi Domain 4 sebagai reusable data layer yang:
- punya registry definition yang versioned,
- bisa menyimpan record reusable berbasis relasional + JSONB,
- bisa menerima source manual/import/submission,
- dan bisa melayani consumer sederhana sebelum masuk domain analytics penuh.

## Scope v1

Fokus v1:
1. definisi boundary domain,
2. entity inti,
3. service contract,
4. satu alur CRUD/manual registry,
5. satu alur import/reference,
6. satu alur submission-derived registry minimal,
7. baseline period-awareness (`active_year`) dan freshness contract.

Belum masuk v1:
- scheduler ETL kompleks
- query builder bebas
- dashboard/reporting
- visualization
- orchestration async berat

## Prinsip delivery

- tipis, bertahap, TDD
- jangan langsung semua use case sekaligus
- stabilkan contract dulu, baru UI besar
- mulai dari service/API dulu, baru web container bila memang perlu

## Phase 0 — Finalisasi kontrak arsitektur

Output:
- boundary Domain 4 disepakati
- taxonomy registry Domain 4 (`lookup`, `scope`, `geo`, `master_data`, `submission_derived`) disepakati
- schema contract generik registry non-wilayah disepakati
- import workflow generik non-wilayah disepakati
- implementation slice v1 untuk migration/service/API disepakati
- entity candidate disepakati
- daftar kolom relasional vs JSONB disepakati
- tiga use case driver disepakati

Artefak:
- `docs/architecture/domain-4-master-data-registry-v1.md`

Kriteria selesai:
- tidak ada kebingungan lagi antara Domain 4 vs Domain 5
- naming awal entity sudah disepakati

## Phase 1 — Schema foundation minimal

Target entity yang dibuat dulu:
- `data_registries`
- `data_registry_versions`
- `data_registry_records`

Kenapa tiga ini dulu:
- cukup untuk membuktikan registry definition + versioning + record store
- belum perlu source/mapping/run penuh untuk mulai CRUD manual

Kemampuan yang ditargetkan:
- buat registry draft
- buat version draft awal
- simpan record manual
- publish version registry
- baca published records
- siapkan field period-aware (`reporting_year`) untuk registry yang memang time-scoped
- siapkan metadata freshness minimal di level version

Test minimum:
- model metadata terdaftar
- relationship registry-version-record benar
- publish version mengunci contract published aktif
- record dapat dibaca per registry version

## Phase 2 — Service contract minimal

Service candidate:
- `DataRegistryService`
- `DataRegistryVersionService`
- `DataRegistryRecordService`

Repository candidate:
- `DataRegistryRepository`
- `DataRegistryVersionRepository`
- `DataRegistryRecordRepository`

Contract minimal:
- `create_registry()`
- `create_draft_version()`
- `publish_version()`
- `create_record()`
- `bulk_upsert_records()`
- `list_published_records()`
- `get_option_items()`
- `get_record_by_key()`
- `get_freshness_status()`
- `resolve_reporting_context()`

Test minimum:
- create registry draft berhasil
- publish version tanpa contract/schema valid ditolak
- upsert record menghormati key unik
- option items hanya membaca published records aktif

## Phase 3 — Registry manual CRUD v1

Use case pertama yang disarankan:
- registry wilayah referensial sederhana

Kenapa ini bagus:
- nyata dan mudah diverifikasi
- langsung relevan ke select/lookup form
- nanti bisa diperluas ke geojson

Kemampuan v1:
- buat registry `wilayah.kabupaten_kota`
- tambah/edit/nonaktifkan record
- publish versi registry
- serve option list dasar `label/value`

Belum perlu dulu:
- UI kompleks bertingkat
- tree browser besar

## Phase 4 — Generic import workflow foundation

Entity prioritas yang mulai ditambahkan:
- `data_registry_import_batches`
- `data_registry_import_rows`

Kemampuan yang ditargetkan:
- upload file/source metadata ke target draft version
- menyimpan `mapping_snapshot` dan `source_snapshot` pada batch
- membuat staged rows
- validasi row-level + batch-level
- normalisasi tipe data termasuk `date` / `datetime`
- menghasilkan error workbook
- materialize valid rows ke draft records

Test minimum:
- batch lifecycle benar (`uploaded -> mapped -> validating -> validated -> materializing -> completed`)
- row status benar (`mapped/valid/error/duplicate/skipped/materialized`)
- parsing/normalisasi tanggal salah format ditolak sebagai validation error
- error workbook dapat dibentuk dari row gagal

## Phase 4.5 — Source catalog, freshness & worker foundation

Target tambahan sebelum scheduler berat:
- `data_registry_sources`
- `data_registry_mappings`
- `DataRegistryFreshnessService`
- `DataRegistrySyncService`
- worker/orchestrator ringan yang masih synchronous atau cron-friendly

Kemampuan yang ditargetkan:
- resolve konteks `reporting_year` dari actor (`active_year`) atau override eksplisit
- baca watermark source terakhir
- bandingkan dengan materialized watermark yang sudah dipublish
- hitung `freshness_signature`
- tentukan `fresh`, `stale`, `refreshing`, atau `failed`
- expose metadata freshness ke consumer/UI

Catatan:
- worker v1 tidak perlu langsung queue system kompleks
- cukup service yang bisa dipanggil manual, via cron, atau on-demand dari admin/UI

## Phase 5 — API v1 untuk import dan publish workflow

Use case kedua yang disarankan:
- import csv/xlsx untuk registry non-wilayah

Kemampuan v1:
- buat batch import ke target draft version
- simpan/finalisasi mapping
- jalankan validation pass
- unduh error workbook
- materialize ke draft records
- publish record hasil import secara eksplisit

Contract yang perlu dijaga:
- source file tidak otomatis overwrite published version lama
- ingest menghasilkan staging + draft materialization dulu
- publish adalah langkah eksplisit

## Phase 6 — Submission-derived registry v1

Use case ketiga yang disarankan:
- satu form tertentu menjadi source registry reusable

Kemampuan v1:
- definisikan source dari `form_id` / `form_version_id`
- definisikan transform/projection field penting
- jalankan extract snapshot dari submissions
- materialize ke `data_registry_records`
- publish sebagai registry source untuk form lain

Prinsip penting:
- consumer membaca registry published, bukan query live ke `submissions`
- lineage minimal harus bisa ditelusuri dari source snapshot
- freshness submission-derived registry harus bisa dibandingkan terhadap submission terakhir per `reporting_year`

## Phase 7 — Consumer integration ringan

Target integrasi awal:
- option source untuk form component select
- lookup API untuk validasi atau autofill ringan
- geojson output endpoint bila use case wilayah aktif

Belum perlu dulu:
- visual builder source-mapping super canggih
- orchestration DSL yang rumit

## Urutan implementasi yang direkomendasikan

Urutan paling aman:
1. Phase 1 — schema foundation minimal
2. Phase 2 — service contract minimal
3. Phase 3 — registry manual CRUD v1
4. Phase 4 — generic import workflow foundation
5. Phase 5 — API v1 untuk import dan publish workflow
6. Phase 4.5 — source catalog, freshness & worker foundation
7. Phase 6 — submission-derived registry v1
8. Phase 7 — consumer integration ringan

## Saran use case implementasi pertama

Kalau harus pilih satu jalur paling aman untuk memulai coding:

Pilihan terbaik:
- registry wilayah referensial sederhana

Kenapa:
- domainnya jelas
- mudah diuji
- langsung terlihat manfaatnya di form select
- membuka jalan ke geojson tanpa harus memaksa submission-derived flow dulu

## Definition of Done v1 (realistis)

Domain 4 v1 dianggap sehat jika sudah ada:
- registry definition versioned
- record store reusable
- published registry records dapat dikonsumsi via option/lookup contract
- minimal satu source import/reference berjalan
- minimal satu source submission-derived berjalan
- semua ini masih tipis, belum over-engineered

## Next technical step yang paling tepat

Setelah plan ini, langkah coding pertama yang paling aman adalah:
1. buat contract test untuk model/repository/service Domain 4,
2. buat tiga tabel inti dulu:
   - `data_registries`
   - `data_registry_versions`
   - `data_registry_records`
3. validasi dulu publish lifecycle + option lookup minimal,
4. baru perluas ke source/mapping/ingestion.

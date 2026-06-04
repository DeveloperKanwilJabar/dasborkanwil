# Domain 5 — Dynamic Analytics Indicators Migration / Schema Plan v1

Dokumen ini menurunkan `domain-5-dynamic-performance-indicators-schema-contract-v1.md` menjadi rencana migration/schema implementation yang siap dibawa ke tahap model SQLAlchemy, Alembic migration, contract test, dan slice service tipis.

Dokumen terkait:
- `docs/architecture/domain-5-blueprint-v1.md`
- `docs/architecture/domain-5-schema-contract-v1.md`
- `docs/architecture/domain-5-migration-schema-plan-v1.md`
- `docs/architecture/domain-5-dynamic-performance-indicators-blueprint-v1.md`
- `docs/architecture/domain-5-dynamic-performance-indicators-schema-contract-v1.md`

Tujuan dokumen ini:
- mengunci strategi migration paling aman untuk layer `dynamic analytics indicators`
- menentukan tabel mana yang wajib masuk fase awal dan mana yang boleh ditunda
- memastikan konsep PK, Renaksi, indikator kinerja, target kinerja, dan istilah bisnis serupa diperlakukan sebagai konten terkelola di atas satu engine yang sama
- membedakan constraint yang wajib dijaga database vs yang lebih sehat dijaga service layer
- menyiapkan jembatan ke test dan implementasi bertahap

Naming v1 yang dikunci di plan ini:
- foundation tetap `analytics_datasets`, `analytics_dataset_versions`, `analytics_dataset_runs`
- layer container/report memakai `analytics_report_*`
- layer definisi/versi/hasil/progres indikator memakai `analytics_indicator_*`
- istilah PK/Renaksi tetap ditempatkan di kategori bisnis/UI, bukan dijadikan prefix tabel

Dokumen ini belum berisi kode migration final, tetapi sudah cukup teknis untuk diturunkan langsung ke plan coding.

---

## 1. Konteks hasil review terbaru

Dari review terbaru dengan user, ada satu penajaman penting yang perlu dikunci:

- PK, Renaksi, indikator kinerja, target kinerja, dan istilah bisnis lain bukan berarti masing-masing harus menjadi subsistem tabel yang berbeda.
- Layer ini lebih sehat diperlakukan sebagai semacam `analytics indicator CMS` di atas foundation dataset.
- Yang dibedakan di UI dan konfigurasi adalah kategori/keluarga laporan serta mode sumber indikator:
  - `dataset_driven`
  - `manual_input`
  - `hybrid`

Implikasi teknisnya:
1. Jangan buat tabel khusus `pk_*`, `renaksi_*`, atau `target_kinerja_*`.
2. Tetap pakai keluarga tabel generik `analytics_report_*` dan `analytics_indicator_*`.
3. Variasi bisnis ditaruh pada metadata/tipe/kategori, bukan dengan memecah bounded context baru tanpa alasan.
4. UI create nanti boleh memberi pilihan kategori bisnis, tetapi persistence layer tetap generik.
5. Istilah `indicator` dipilih untuk persistence karena objek ini membawa target, formula, periodisasi, dan narasi; lebih tepat daripada `metric` untuk v1.

Kesimpulan penting:
- nama bisnis boleh berubah-ubah,
- engine penyimpanan dan versioning tetap satu.

---

## 2. Audit kondisi repo saat dokumen ini ditulis

Dari audit file repo saat ini:
- foundation Domain 5 sudah lebih dulu punya migration draft:
  - `migrations/versions/a1b2c3d4e5f6_add_analytics_dataset_foundation_v1.py`
- migration tersebut merevisi:
  - `c4d7a9e2b1f0`
- artinya layer indikator dinamis harus dianggap sebagai lapisan lanjutan di atas foundation dataset, bukan cabang terpisah.

Pola implementasi repo yang sudah konsisten dan sebaiknya dipertahankan:
- integer PK + `uuid`
- timestamp standar `created_at`, `updated_at`, `deleted_at`
- audit actor `created_by/_uuid`, `updated_by/_uuid`, `deleted_by/_uuid`
- enum direpresentasikan sebagai `String(...)` + check constraint, bukan native PostgreSQL enum
- field fleksibel memakai `JSONB`
- partial unique index PostgreSQL dipakai untuk kasus `current draft/current published`

Kesimpulan audit:
- migration indikator dinamis sebaiknya mengikuti gaya Domain 3, Domain 4, dan foundation Domain 5 yang sudah ada
- jangan memperkenalkan gaya schema baru yang terlalu berbeda

---

## 3. Prinsip desain migration yang dikunci

1. Engine ini adalah `content-managed analytics indicator layer`, bukan hardcoded modul PK/Renaksi.
2. Migration awal harus cukup kaya untuk menjaga integritas domain, tetapi jangan terlalu berat sampai hasil perhitungan dan workflow operasional semuanya dipaksa masuk sekaligus.
3. Definition/version layer lebih sehat dipisahkan dari result/progress layer.
4. Constraint inti seperti uniqueness, lifecycle dasar, dan relasi FK harus masuk sejak migration awal.
5. Validasi kombinasi yang kompleks lebih sehat dijaga di service layer.
6. Native PostgreSQL ENUM belum perlu; tetap pakai `varchar + check constraint`.
7. JSONB dipakai untuk formula spec, target spec, display spec, trace, dan detail hasil yang fleksibel.
8. Period awareness harus tetap first-class lewat kolom relasional, bukan hanya JSONB.
9. Kebutuhan narasi kualitatif / `meta description` harus masuk engine utama sejak plan, tetapi jangan overdesign menjadi subsystem terpisah; v1 cukup lewat kolom teks + JSONB pendamping di layer versi indikator, hasil indikator, dan progres manual.

---

## 4. Strategi fase migration yang direkomendasikan

## 4.1. Rekomendasi utama: pecah menjadi dua migration

Supaya implementasi dan review lebih aman, layer ini sebaiknya dipecah menjadi dua migration utama.

### Migration A — definition / CMS foundation
Fokus:
- identitas report
- versi report
- identitas indikator
- versi indikator
- mapping indikator ke versi report

Tabel:
1. `analytics_report_definitions`
2. `analytics_report_versions`
3. `analytics_indicator_definitions`
4. `analytics_indicator_versions`
5. `analytics_report_version_indicators`

### Migration B — result + manual progress layer
Fokus:
- hasil indikator per periode
- progres manual untuk use case Renaksi/checklist/evidence

Tabel:
6. `analytics_indicator_results`
7. `analytics_indicator_progress_entries`
8. `analytics_indicator_progress_items`

## 4.2. Kenapa tidak dijadikan satu migration besar saja

Boleh saja dijadikan satu migration besar, tetapi aku lebih menyarankan dua migration karena:
- definition layer bisa direview dan dites dulu tanpa noise hasil operasional
- current draft/current published uniqueness lebih mudah diverifikasi lebih awal
- use case CMS-like sudah bisa hidup lebih cepat
- result layer dan manual progress bisa menyusul tanpa memblokir definisi report/indicator
- risiko rollback lebih kecil bila ada koreksi desain pada layer hasil

Kesimpulan praktis:
- jika ingin paling aman: dua migration
- jika ingin paling cepat tetapi lebih padat: satu migration besar
- rekomendasi plan ini: tetap dua migration

---

## 5. Urutan revision yang direkomendasikan

Dengan asumsi foundation dataset Domain 5 tetap memakai revision:
- `a1b2c3d4e5f6`

maka urutan aman yang direkomendasikan:

1. `<rev_a>_add_analytics_indicator_definition_layer_v1.py`
   - `down_revision = 'a1b2c3d4e5f6'`
2. `<rev_b>_add_analytics_indicator_results_and_progress_v1.py`
   - `down_revision = '<rev_a>'`

Catatan:
- nama file boleh sedikit berubah, tetapi semangatnya jangan hilang
- istilah bisnis di UI boleh tetap memakai "laporan kinerja", PK, Renaksi, atau scorecard, tetapi nama tabel persistence v1 dikunci ke keluarga `analytics_report_*` dan `analytics_indicator_*` demi konsistensi boundary analytics

---

## 6. Scope migration A — definition / CMS foundation

## 6.1. `analytics_report_definitions`

Peran:
- kepala laporan/scorecard yang dilihat user sebagai objek konten bisnis

Kolom inti yang wajib masuk migration A:
- `id`, `uuid`
- `report_key`
- `name`
- `description`
- `report_type`
- `status`
- `is_active`
- `default_reporting_year_mode`
- `owner_scope_type`, `owner_scope_code`, `owner_scope_name`
- `owner_scope_path`
- `settings_json`
- `tags_json`
- audit fields standar

Catatan migration:
- `report_type` diperlakukan sebagai kategori/keluarga konten bisnis, bukan pemicu pembuatan tabel baru
- `settings_json` boleh menyimpan hint UI/template ringan
- bila nanti dibutuhkan kategori yang lebih granular dari enum utama, taruh dulu di metadata atau tambah kolom baru lewat migration terpisah, jangan buru-buru overdesign

Constraint minimum:
- unique `uuid`
- unique `report_key`
- check `report_type` in allowed enum
- check `status` in allowed enum
- check `default_reporting_year_mode in ('active_year', 'explicit', 'all_time')`

Index minimum:
- `report_type`
- `status`
- `is_active`
- `owner_scope_code`
- `deleted_at`

## 6.2. `analytics_report_versions`

Peran:
- versi resmi susunan satu report

Kolom inti yang wajib masuk migration A:
- `id`, `uuid`
- `report_definition_id`
- `version_number`
- `status`
- `is_current_draft`
- `is_current_published`
- `published_at`
- `publish_notes`
- `title_snapshot`
- `description_snapshot`
- `reporting_year`
- `period_mode`
- `layout_spec_json`
- `display_config_json`
- `scope_snapshot_json`
- `settings_json`
- audit fields standar

Constraint minimum:
- unique `uuid`
- unique `(report_definition_id, version_number)`
- check `status in ('draft', 'published', 'archived')`
- check `period_mode` in enum baseline
- check state conflict agar `is_current_draft` dan `is_current_published` tidak true bersamaan pada row yang sama
- partial unique index untuk memastikan hanya satu current draft aktif per report
- partial unique index untuk memastikan hanya satu current published aktif per report

Index minimum:
- `report_definition_id`
- `status`
- `reporting_year`
- `period_mode`
- `published_at`
- `deleted_at`

## 6.3. `analytics_indicator_definitions`

Peran:
- kartu identitas indikator yang reusable lintas report

Kolom inti yang wajib masuk migration A:
- `id`, `uuid`
- `indicator_key`
- `name`
- `description`
- `status`
- `is_active`
- `indicator_group_key`
- `unit_label`
- `owner_scope_type`, `owner_scope_code`, `owner_scope_name`
- `owner_scope_path`
- `settings_json`
- `tags_json`
- audit fields standar

Catatan migration:
- `indicator_group_key` penting untuk nuansa CMS-like karena istilah bisnis bisa dikelompokkan tanpa harus membuat tabel berbeda
- field ini tidak menggantikan `source_mode`; `source_mode` tetap milik versi indikator karena rumus/sumber bisa berubah antar versi

Constraint minimum:
- unique `uuid`
- unique `indicator_key`
- check `status in ('draft', 'active', 'archived')`

Index minimum:
- `status`
- `is_active`
- `indicator_group_key`
- `owner_scope_code`
- `deleted_at`

## 6.4. `analytics_indicator_versions`

Peran:
- kontrak formula resmi satu indikator pada satu versi

Kolom inti yang wajib masuk migration A:
- `id`, `uuid`
- `indicator_definition_id`
- `version_number`
- `status`
- `is_current_draft`
- `is_current_published`
- `published_at`
- `publish_notes`
- `title_snapshot`
- `description_snapshot`
- `source_mode`
- `calculation_type`
- `target_source_type`
- `period_mode`
- `aggregation_strategy`
- `dataset_id` nullable
- `dataset_version_id` nullable
- `formula_spec_json`
- `target_spec_json`
- `scoring_spec_json`
- `display_config_json`
- `meta_description`
- `narrative_guidance_json`
- `manual_input_spec_json`
- `evidence_requirement_json`
- `scope_snapshot_json`
- `settings_json`
- audit fields standar

Catatan migration:
- `dataset_id` dan `dataset_version_id` nullable karena `manual_input` tidak wajib memakai foundation dataset
- `manual_input_spec_json` sengaja first-class JSONB agar backend bisa mengontrol bentuk checklist/progress tanpa membuat tabel template terlalu cepat
- `source_mode` adalah pusat kategorisasi operasional, bukan `report_type`
- `meta_description` sengaja ditaruh di level versi indikator, bukan definition, karena narasi baseline indikator bisa berubah ketika kebijakan, formula, atau tafsir capaian berubah antar tahun

Constraint minimum:
- unique `uuid`
- unique `(indicator_definition_id, version_number)`
- check `status in ('draft', 'published', 'archived')`
- check `source_mode in ('dataset_driven', 'manual_input', 'hybrid')`
- check `calculation_type` in enum baseline
- check `target_source_type` in enum baseline
- check `period_mode` in enum baseline
- check `aggregation_strategy` in enum baseline
- check state conflict agar `is_current_draft` dan `is_current_published` tidak true bersamaan pada row yang sama
- partial unique index satu current draft per indicator definition
- partial unique index satu current published per indicator definition

Index minimum:
- `indicator_definition_id`
- `status`
- `source_mode`
- `calculation_type`
- `target_source_type`
- `period_mode`
- `dataset_id`
- `dataset_version_id`
- `published_at`
- `deleted_at`

## 6.5. `analytics_report_version_indicators`

Peran:
- tabel penghubung indikator apa saja yang masuk ke satu versi report

Kolom inti yang wajib masuk migration A:
- `id`, `uuid`
- `report_version_id`
- `indicator_version_id`
- `section_key`
- `display_order`
- `is_required`
- `weight_value`
- `label_override`
- `notes_json`
- audit fields standar

Constraint minimum:
- unique `uuid`
- unique `(report_version_id, indicator_version_id)`
- optional unique `(report_version_id, section_key, display_order)` bila urutan display mau dijaga ketat sejak awal

Index minimum:
- `report_version_id`
- `indicator_version_id`
- `section_key`
- `display_order`
- `deleted_at`

---

## 7. Scope migration B — results + manual progress layer

## 7.1. `analytics_indicator_results`

Peran:
- menyimpan hasil capaian indikator per periode yang bisa dibaca dashboard/report consumer

Kolom inti yang wajib masuk migration B:
- `id`, `uuid`
- `indicator_version_id`
- `report_version_id` nullable
- `reporting_year`
- `reporting_period_id` nullable
- `period_mode`
- `scope_type`, `scope_code`, `scope_name`
- `scope_path_json`
- `status`
- `completion_status`
- `dataset_run_id` nullable
- `target_value_numeric` nullable
- `actual_value_numeric` nullable
- `achievement_percentage` nullable
- `score_value` nullable
- `qualitative_summary` nullable
- `constraint_notes` nullable
- `result_summary_json`
- `result_detail_json`
- `source_trace_json`
- `narrative_context_json`
- `computed_at`
- `verified_at`
- `published_at`
- audit fields standar

Catatan migration:
- `report_version_id` nullable agar satu indikator bisa dihitung dulu di luar packaging report tertentu bila nanti dibutuhkan
- `dataset_run_id` nullable untuk `manual_input`
- `scope_*` sebaiknya eksplisit agar hasil bisa diaudit dan di-query tanpa membaca JSONB penuh
- `qualitative_summary` dan `constraint_notes` disimpan sebagai kolom teks biasa karena kebutuhan utamanya authoring narasi panjang, bukan filtering berat
- `narrative_context_json` dipakai hanya sebagai struktur bantu opsional untuk AI/UI seperti `drivers`, `obstacles`, `next_actions`, atau `confidence_level`

Constraint minimum:
- unique `uuid`
- unique business key baseline yang direkomendasikan:
  `(indicator_version_id, reporting_year, reporting_period_id, scope_code)`
  dengan penyesuaian null-safe sesuai implementasi PostgreSQL
- check `status` in enum baseline
- check `completion_status` in enum baseline
- check `period_mode` in enum baseline

Index minimum:
- `indicator_version_id`
- `report_version_id`
- `reporting_year`
- `reporting_period_id`
- `period_mode`
- `scope_code`
- `status`
- `completion_status`
- `dataset_run_id`
- `published_at`
- `deleted_at`

## 7.2. `analytics_indicator_progress_entries`

Peran:
- kepala entri progres manual untuk satu indikator pada satu konteks periode/scope

Kolom inti yang wajib masuk migration B:
- `id`, `uuid`
- `indicator_version_id`
- `report_version_id` nullable
- `reporting_year`
- `reporting_period_id` nullable
- `period_mode`
- `scope_type`, `scope_code`, `scope_name`
- `scope_path_json`
- `status`
- `completion_status`
- `target_count` nullable
- `completed_count` nullable
- `progress_summary_json`
- `evidence_summary_json`
- `qualitative_summary`
- `constraint_notes`
- `narrative_context_json`
- `submitted_at` nullable
- `verified_at` nullable
- audit fields standar

Constraint minimum:
- unique `uuid`
- unique baseline `(indicator_version_id, reporting_year, reporting_period_id, scope_code)` dengan penyesuaian null-safe
- check `status` in enum manual entry baseline
- check `completion_status` in enum baseline
- check `period_mode` in enum baseline

Catatan migration:
- di level manual progress, narasi sering justru muncul lebih dulu sebelum hasil indikator dipublish; karena itu `qualitative_summary` dan `constraint_notes` jangan ditunda ke tabel hasil saja

Index minimum:
- `indicator_version_id`
- `report_version_id`
- `reporting_year`
- `reporting_period_id`
- `scope_code`
- `status`
- `completion_status`
- `submitted_at`
- `deleted_at`

## 7.3. `analytics_indicator_progress_items`

Peran:
- detail checklist/item/evidence dari satu entri progres manual

Kolom inti yang wajib masuk migration B:
- `id`, `uuid`
- `progress_entry_id`
- `item_key`
- `label`
- `description`
- `item_order`
- `is_required`
- `status`
- `is_complete`
- `completed_at` nullable
- `evidence_count` nullable
- `item_payload_json`
- `evidence_meta_json`
- `notes_json`
- audit fields standar

Constraint minimum:
- unique `uuid`
- unique `(progress_entry_id, item_key)`
- optional unique `(progress_entry_id, item_order)` bila urutan checklist mau dijaga ketat dari awal

Index minimum:
- `progress_entry_id`
- `item_key`
- `item_order`
- `status`
- `is_complete`
- `deleted_at`

---

## 8. Constraint yang dijaga database vs service layer

## 8.1. Wajib dijaga database
- uniqueness `uuid`
- uniqueness key teknis (`report_key`, `indicator_key`)
- uniqueness `(definition_id, version_number)`
- partial unique satu `current draft` per definition
- partial unique satu `current published` per definition
- check enum dasar
- FK antar tabel
- not-null pada kolom inti identitas/lifecycle

## 8.2. Lebih sehat dijaga service layer
- kombinasi `source_mode` dengan field wajib, misalnya:
  - `dataset_driven` wajib punya `dataset_id` dan biasanya `dataset_version_id`
  - `manual_input` tidak boleh diam-diam tergantung `dataset_run_id`
  - `hybrid` boleh butuh kombinasi target/manual/dataset
- validitas `formula_spec_json` sesuai `calculation_type`
- validitas `target_spec_json` sesuai `target_source_type`
- validitas `manual_input_spec_json` terhadap bentuk item checklist
- konsistensi `report_version` dan `indicator_version` dalam satu scope/tahun/periode
- aturan publish, archive, dan cloning version
- penentuan `achievement_percentage` dan `score_value`
- jika `meta_description` diisi, backend sebaiknya membatasi panjang minimum/maksimum wajar dan menyediakan sanitization/rendering policy agar aman dipakai UI maupun AI consumer
- jika `constraint_notes` terisi tetapi `completion_status='complete'`, service tidak wajib menolak, tetapi sebaiknya bisa memberi warning agar user sadar narasi hambatan masih tersisa pada hasil yang sudah lengkap

Prinsipnya:
- database menjaga integritas struktural
- service menjaga integritas bisnis

---

## 9. Rekomendasi tipe data SQL v1

Ikuti pola repo saat ini:
- PK: `Integer` atau `BigInteger` mengikuti standar aktif repo
- UUID: `String(36)` bila ingin konsisten penuh dengan foundation yang sudah ada sekarang
- enum semu: `String(length)` + check constraint
- waktu: `DateTime(timezone=True)`
- angka capaian/score/target: `Numeric(...)` untuk nilai yang mungkin desimal
- payload fleksibel: `postgresql.JSONB`
- boolean flags: `Boolean`
- narasi/publish notes/description: `Text`

Catatan penting:
- karena foundation Domain 5 yang sudah ada memakai `String(36)` untuk UUID, layer indikator dinamis sebaiknya ikut pola itu agar satu domain tidak campur gaya tanpa alasan

---

## 10. Rekomendasi enum v1 yang benar-benar dipakai lebih dulu

Walaupun schema contract sudah membuka baseline enum yang lebih luas, migration + implementasi v1 paling aman bisa memulai dari subset yang paling sering dipakai:

### source mode
- `dataset_driven`
- `manual_input`
- `hybrid`

### calculation type
- `absolute_count`
- `percentage`
- `checklist_completion`
- `score`

### target source type
- `manual_central_target`
- `manual_local_target`
- `derived_from_dataset`
- `hybrid`

### period mode
- `quarterly`
- `semester`
- `yearly`
- `multi_period`

### report type baseline
- `pk`
- `renaksi`
- `scorecard`
- `monitoring`
- `custom`

Catatan:
- enum yang belum dipakai aktif tetap boleh dipertahankan di contract bila tidak memberatkan migration
- tetapi service/UI v1 tidak harus langsung membuka semua variasi formula

---

## 11. Urutan implementasi paling aman setelah migration plan ini

### Fase 1
- finalkan file plan ini
- finalkan perubahan kecil pada blueprint/schema contract bila ada koreksi wording

### Fase 2
- buat model SQLAlchemy untuk 5 tabel definition layer
- buat migration A
- buat contract test untuk uniqueness/current draft/current published
- pastikan `meta_description` dan `narrative_guidance_json` sudah ikut di definition/version layer supaya authoring narasi baseline hidup dari awal

### Fase 3
- buat service slice tipis:
  - create report definition
  - create draft report version
  - create indicator definition
  - create draft indicator version
  - attach indicator version ke report version
  - publish draft version

### Fase 4
- buat model SQLAlchemy untuk results/manual progress
- buat migration B
- buat contract test untuk result uniqueness dan manual progress lifecycle minimal
- pastikan `qualitative_summary`, `constraint_notes`, dan `narrative_context_json` tersedia untuk result dan manual progress

### Fase 5
- baru buka vertical slice UI/API sederhana untuk create report / create indicator / manual progress input
- AI/report consumer menyusul sebagai pembaca data naratif + numerik, bukan penentu struktur data inti

---

## 12. Test target minimal yang sebaiknya ditulis

Setelah plan ini diterjemahkan ke kode, minimal test yang harus ada:

1. model metadata memuat semua tabel baru
2. migration upgrade sukses pada database test
3. migration downgrade sukses bila repo memang menjaga downgrade path
4. hanya satu current draft report version per report
5. hanya satu current published report version per report
6. hanya satu current draft indicator version per indicator
7. hanya satu current published indicator version per indicator
8. `dataset_driven` ditolak service bila `dataset_id` kosong
9. `manual_input` dapat membuat progress entry tanpa `dataset_run_id`
10. hasil indikator period-aware bisa diquery dengan `reporting_year` dan `reporting_period_id`
11. `meta_description` tersimpan di `analytics_indicator_versions`
12. `qualitative_summary` / `constraint_notes` tersimpan di `analytics_indicator_results`
13. `manual_input` tetap bisa menyimpan narasi periodik walau tanpa `dataset_run_id`

---

## 13. Risiko desain yang perlu dijaga

1. Menjadikan PK/Renaksi subsistem tabel yang terpisah.
   - Hindari. Tetap satu engine generik.

2. Menaruh semua perbedaan konsep hanya di `report_type`.
   - Hindari. `source_mode`, `calculation_type`, `target_source_type`, dan metadata versi tetap jauh lebih penting.

3. Memaksa semua indikator ke dataset run.
   - Hindari. `manual_input` adalah use case sah.

4. Membiarkan item manual progress hidup di JSONB tunggal tanpa tabel detail.
   - Hindari bila checklist/evidence perlu audit dan status item.

5. Memasukkan workflow approval kompleks terlalu dini.
   - Tunda ke migration berikutnya.

---

## 14. Kesimpulan awam

Kalau disederhanakan:
- foundation Domain 5 adalah dapur data
- layer ini adalah CMS rapor kinerja di atas dapur itu
- PK, Renaksi, indikator kinerja, target kinerja, dan nama-nama lain hanyalah variasi konten bisnis yang memakai engine yang sama

Karena itu migration plan paling sehat adalah:
1. bangun dulu definition/CMS foundation,
2. lalu bangun result dan manual progress layer,
3. jaga kategori bisnis di level metadata/tipe/UI,
4. jaga source mode dan formula di level versi indikator.

Dengan urutan ini, arsitektur tetap rapi, implementasi tetap pragmatis, dan kita tidak terkunci pada satu istilah bisnis yang bisa berubah nanti.
# Domain 4 — Implementation Plan Wilayah v1

> **Untuk Hermes:** gunakan skill `subagent-driven-development` bila nanti plan ini dieksekusi task-by-task.

**Goal:** membangun fondasi implementasi Domain 4 subdomain wilayah administratif sampai level model, Alembic migration, repository, service, consumer API v1, dan test dasar sehingga registry wilayah bisa dipublish sebagai resource API dinamis untuk option field form, lookup, tree, dan peta ringan.

**Architecture:** implementasi mengikuti pola yang sudah dipakai di repo saat ini: `models` untuk struktur tabel, `repositories` untuk query/persistence, `services` untuk lifecycle/publish/serving contract, dan `app/api/v1/.../routes.py` untuk API tipis. V1 fokus pada registry/version/record wilayah yang sudah curated dan published; consumer tidak membaca draft, raw CSV, atau query builder bebas.

**Tech Stack:** Flask, Flask-SQLAlchemy, Alembic, PostgreSQL JSONB, pytest, API v1 internal, pola service-repository existing project.

---

## 1. Keputusan implementasi yang dikunci sebelum coding

1. Domain 4 memang **boleh** mempublish data registry menjadi API resource dinamis.
2. Tetapi yang boleh diserve hanya **published registry contract**, bukan draft version.
3. Consumer API v1 dibatasi ke pola:
   - option list `label/value`
   - lookup by `record_key` / `record_code`
   - children listing berdasarkan parent/level
   - tree ringan
   - feature collection ringan
   - filtered listing dengan parameter terbatas
4. Query builder generik bebas ditunda.
5. Ingest CSV wilayah ditunda setelah fondasi model+migration+service+API dasar stabil.

---

## 2. Target hasil implementasi v1

Setelah seluruh plan ini selesai, sistem minimal harus bisa:

1. membuat registry `wilayah.administratif`;
2. membuat draft version registry;
3. menyimpan row wilayah hierarchy di `data_registry_records`;
4. publish satu version aktif;
5. melakukan lookup record wilayah berdasarkan key/code;
6. menyajikan option list untuk select form;
7. menyajikan dependent select `province -> city_regency -> district -> village`;
8. menyajikan feature collection ringan dari version published;
9. menjaga contract test dasar agar iterasi berikutnya aman.

---

## 3. File yang akan dibuat / diubah

### 3.1. File baru yang direncanakan

**Module Domain 4**
- `app/modules/data_registry/__init__.py`
- `app/modules/data_registry/models.py`
- `app/modules/data_registry/repositories.py`
- `app/modules/data_registry/services.py`

**API v1 Domain 4**
- `app/api/v1/data_registries/__init__.py`
- `app/api/v1/data_registries/routes.py`

**Tests**
- `tests/test_data_registry_models.py`
- `tests/test_data_registry_service_contracts.py`
- `tests/test_data_registry_service_behaviors.py`
- `tests/test_api_data_registry_routes.py`

**Migration**
- `migrations/versions/<revision>_add_data_registry_wilayah_v1.py`

### 3.2. File existing yang perlu diubah

- `app/__init__.py`
  - import model Domain 4 agar metadata SQLAlchemy terbaca oleh Alembic/autoload app.
  - register blueprint API v1 Domain 4.
- `docs/architecture/domain-4-master-data-registry-v1.md`
  - sudah ditajamkan untuk publish resource API dinamis.
- `docs/architecture/domain-4-wilayah-migration-schema-plan-v1.md`
  - perlu ditautkan ke implementation plan ini.
- `docs/architecture/domain-4-wilayah-schema-contract-v1.md`
  - perlu ditautkan ke implementation plan ini.

---

## 4. Urutan implementasi yang direkomendasikan

Implementasi paling aman dibagi menjadi 8 task besar, masing-masing masih dipecah ke langkah kecil TDD.

---

## Task 1: Tambah contract tests dan metadata tests Domain 4

**Objective:** mengunci bentuk API internal Python terlebih dahulu sebelum model dan service diimplementasikan penuh.

**Files:**
- Create: `tests/test_data_registry_models.py`
- Create: `tests/test_data_registry_service_contracts.py`

### Step 1: Tulis failing metadata test untuk model-table utama

Tambahkan test yang memverifikasi minimal kolom berikut ada:

- `DataRegistry`
  - `uuid`
  - `registry_slug`
  - `registry_code`
  - `name`
  - `registry_type`
  - `source_mode`
  - `data_shape`
  - `is_year_scoped`
  - `status`
  - `schema_meta`

- `DataRegistryVersion`
  - `uuid`
  - `registry_id`
  - `version_number`
  - `status`
  - `schema_json`
  - `mapping_spec`
  - `source_snapshot`
  - `published_at`
  - `freshness_status`

- `DataRegistryRecord`
  - `uuid`
  - `registry_id`
  - `registry_version_id`
  - `parent_record_id`
  - `record_key`
  - `record_code`
  - `external_code`
  - `label`
  - `normalized_label`
  - `admin_level`
  - `city_regency_kind`
  - `province_code`
  - `city_regency_code`
  - `district_code`
  - `village_code`
  - `village_adm_status`
  - `centroid_lat`
  - `centroid_lng`
  - `geometry_json`
  - `payload`
  - `source_snapshot`

### Step 2: Tulis failing repository/service contract test

Minimal kontrak yang harus ada:

`DataRegistryRepository`
- `get_by_slug`
- `get_active_by_slug`
- `list_by_status`

`DataRegistryVersionRepository`
- `get_draft_version`
- `get_published_version`
- `get_next_version_number`
- `list_versions`
- `archive_published_others`

`DataRegistryRecordRepository`
- `get_by_key`
- `get_by_code`
- `list_children`
- `list_by_level`
- `list_options`
- `list_feature_collection_records`

`DataRegistryService`
- `create_registry`
- `publish_registry`
- `get_registry_detail`

`DataRegistryVersionService`
- `create_draft_version`
- `publish_version`
- `get_published_version`

`DataRegistryQueryService`
- `get_option_list`
- `get_lookup`
- `get_children`
- `get_tree`
- `get_feature_collection`

### Step 3: Jalankan test untuk memastikan fail

Run:
`docker exec -w /usr/src/app dasborkanwil_app sh -lc 'PYTHONPATH=/usr/src/app pytest tests/test_data_registry_models.py tests/test_data_registry_service_contracts.py -q'`

Expected:
- FAIL karena module/file Domain 4 belum ada.

### Step 4: Commit

Message rekomendasi:
`test: add failing contracts for data registry wilayah v1`

---

## Task 2: Implement model SQLAlchemy Domain 4

**Objective:** membuat struktur model Python yang sesuai schema contract dan siap diimport app.

**Files:**
- Create: `app/modules/data_registry/__init__.py`
- Create: `app/modules/data_registry/models.py`
- Modify: `app/__init__.py`

### Step 1: Buat package module baru

`app/modules/data_registry/__init__.py`
minimal:
```python
from .models import DataRegistry, DataRegistryVersion, DataRegistryRecord
```

### Step 2: Buat `models.py`

Definisikan tiga model:
- `DataRegistry`
- `DataRegistryVersion`
- `DataRegistryRecord`

Ikuti konvensi repo saat ini:
- `id` integer PK
- `uuid` string 36
- `created_at`, `updated_at`, `deleted_at`
- `created_by`, `created_by_uuid`, `updated_by`, `updated_by_uuid`, `deleted_by`, `deleted_by_uuid`
- JSONB dari `sqlalchemy.dialects.postgresql`
- relationship `lazy='select'` atau `lazy='joined'` secukupnya

Relationship minimal:
- `DataRegistry.versions`
- `DataRegistry.records`
- `DataRegistryVersion.registry`
- `DataRegistryVersion.records`
- `DataRegistryRecord.registry`
- `DataRegistryRecord.registry_version`
- `DataRegistryRecord.parent`
- `DataRegistryRecord.children`

### Step 3: Tambahkan `__table_args__`

Minimal:
- unique (`registry_id`, `version_number`) pada version
- unique (`registry_version_id`, `record_key`) pada record
- unique (`registry_version_id`, `record_code`) pada record
- index `deleted_at`
- index hierarchy fields penting

### Step 4: Import model di `app/__init__.py`

Tambahkan import eksplisit dalam `with app.app_context()`:
```python
from .modules.data_registry.models import DataRegistry, DataRegistryVersion, DataRegistryRecord
```

### Step 5: Jalankan test metadata

Run:
`docker exec -w /usr/src/app dasborkanwil_app sh -lc 'PYTHONPATH=/usr/src/app pytest tests/test_data_registry_models.py -q'`

Expected:
- PASS untuk metadata/kolom dasar.
- contract service masih boleh FAIL.

### Step 6: Commit

Message rekomendasi:
`feat: add data registry SQLAlchemy models`

---

## Task 3: Implement Alembic migration wilayah v1

**Objective:** menurunkan model ke migration schema nyata dengan constraint/index inti.

**Files:**
- Create: `migrations/versions/<revision>_add_data_registry_wilayah_v1.py`

### Step 1: Generate migration dari model

Run:
`docker exec -w /usr/src/app dasborkanwil_app sh -lc 'PYTHONPATH=/usr/src/app flask db migrate -m "add data registry wilayah v1"'`

### Step 2: Rapikan file migration secara manual

Hal yang wajib dicek di migration:
- urutan create table:
  1. `data_registries`
  2. `data_registry_versions`
  3. `data_registry_records`
- FK ke `users.id`
- self FK `parent_record_id`
- unique constraints
- indexes
- check constraints utama sesuai migration/schema plan

Constraint yang wajib masuk sejak v1:
- check `status`
- check `registry_type`
- check `source_mode`
- check `data_shape`
- check `freshness_status`
- check `admin_level`
- check `city_regency_kind`
- check `village_adm_status`
- check range koordinat latitude/longitude
- check `valid_to >= valid_from`

### Step 3: Upgrade database lokal/container

Run:
`docker exec -w /usr/src/app dasborkanwil_app sh -lc 'PYTHONPATH=/usr/src/app flask db upgrade'`

### Step 4: Verifikasi head migration

Run:
`docker exec -w /usr/src/app dasborkanwil_app sh -lc 'PYTHONPATH=/usr/src/app flask db current'`

Expected:
- revision baru Domain 4 menjadi head.

### Step 5: Commit

Message rekomendasi:
`feat: add alembic migration for data registry wilayah v1`

---

## Task 4: Implement repository layer Domain 4

**Objective:** menyediakan query dasar yang stabil untuk service dan API.

**Files:**
- Create: `app/modules/data_registry/repositories.py`
- Update: `tests/test_data_registry_service_contracts.py`

### Step 1: Implement `DataRegistryRepository`

Method minimal:
```python
class DataRegistryRepository(BaseRepository):
    def get_by_slug(self, slug): ...
    def get_active_by_slug(self, slug): ...
    def list_by_status(self, status): ...
```

### Step 2: Implement `DataRegistryVersionRepository`

Method minimal:
```python
class DataRegistryVersionRepository(BaseRepository):
    def get_draft_version(self, registry_id): ...
    def get_published_version(self, registry_id): ...
    def get_next_version_number(self, registry_id): ...
    def list_versions(self, registry_id, include_deleted=False): ...
    def archive_published_others(self, registry_id, except_version_id=None): ...
```

### Step 3: Implement `DataRegistryRecordRepository`

Method minimal:
```python
class DataRegistryRecordRepository(BaseRepository):
    def get_by_key(self, registry_version_id, record_key): ...
    def get_by_code(self, registry_version_id, record_code): ...
    def list_children(self, registry_version_id, parent_record_id): ...
    def list_by_level(self, registry_version_id, admin_level, parent_record_id=None): ...
    def list_options(self, registry_version_id, admin_level=None, parent_record_id=None, q=None, limit=100): ...
    def list_feature_collection_records(self, registry_version_id, admin_level=None): ...
```

### Step 4: Jalankan contract tests

Run:
`docker exec -w /usr/src/app dasborkanwil_app sh -lc 'PYTHONPATH=/usr/src/app pytest tests/test_data_registry_service_contracts.py -q'`

Expected:
- repository contract PASS
- service behavior mungkin masih FAIL.

### Step 5: Commit

Message rekomendasi:
`feat: add data registry repositories`

---

## Task 5: Implement service lifecycle registry + version

**Objective:** membuat lifecycle create registry, draft version, publish version, dan detail registry.

**Files:**
- Create: `app/modules/data_registry/services.py`
- Update: `tests/test_data_registry_service_contracts.py`
- Create: `tests/test_data_registry_service_behaviors.py`

### Step 1: Tulis failing behavior tests

Minimal behavior yang harus dikunci:
1. `create_registry()` membuat registry dengan slug unik.
2. `create_draft_version()` membuat draft version pertama bernomor `1`.
3. `create_draft_version()` mengupdate draft aktif, bukan membuat draft baru liar, bila policy-nya mengikuti pola Form Version saat ini.
4. `publish_version()`:
   - hanya boleh publish draft valid,
   - mengarsipkan published version lain,
   - mengisi `published_at`,
   - mengubah status registry menjadi `published`.
5. `get_registry_detail()` mengembalikan registry, draft version, published version.

### Step 2: Implement `DataRegistryService`

Method minimal:
```python
class DataRegistryService(BaseService):
    def create_registry(self, data, actor=None): ...
    def get_registry_detail(self, registry_id): ...
    def publish_registry(self, registry_id, version_id=None, actor=None): ...
```

### Step 3: Implement `DataRegistryVersionService`

Method minimal:
```python
class DataRegistryVersionService(BaseService):
    def create_draft_version(self, registry_id, schema_json, mapping_spec=None, source_snapshot=None, actor=None): ...
    def publish_version(self, version_id, actor=None): ...
    def get_published_version(self, registry_id): ...
```

### Step 4: Audit helper

Gunakan pola helper seperti di `app/modules/form/services.py` untuk:
- `_apply_actor_audit(...)`
- validasi slug/code unik
- update status publish

### Step 5: Jalankan tests

Run:
`docker exec -w /usr/src/app dasborkanwil_app sh -lc 'PYTHONPATH=/usr/src/app pytest tests/test_data_registry_service_contracts.py tests/test_data_registry_service_behaviors.py -q'`

Expected:
- PASS untuk lifecycle dasar.

### Step 6: Commit

Message rekomendasi:
`feat: add data registry lifecycle services`

---

## Task 6: Implement query service untuk serving contract consumer API

**Objective:** mengunci bahwa Domain 4 benar-benar bisa dipublish sebagai resource API dinamis untuk form options dan lookup.

**Files:**
- Modify: `app/modules/data_registry/services.py`
- Modify: `tests/test_data_registry_service_behaviors.py`

### Step 1: Tulis failing behavior tests untuk serving contract

Minimal behavior:
1. `get_option_list()` hanya membaca version published.
2. `get_option_list()` bisa filter `admin_level` dan `parent_record_id`.
3. `get_lookup()` bisa cari by `record_key` atau `record_code`.
4. `get_children()` mengembalikan children aktif terurut.
5. `get_tree()` mengembalikan nested tree ringan untuk consumer.
6. `get_feature_collection()` hanya mengeluarkan record yang punya `geometry_json` atau centroid minimal.

### Step 2: Tambah `DataRegistryQueryService`

Signature minimal:
```python
class DataRegistryQueryService:
    def get_option_list(self, registry_slug, version_number=None, admin_level=None, parent_record_id=None, parent_code=None, q=None, limit=100): ...
    def get_lookup(self, registry_slug, record_key=None, record_code=None, version_number=None): ...
    def get_children(self, registry_slug, parent_record_id=None, parent_code=None, admin_level=None, version_number=None): ...
    def get_tree(self, registry_slug, root_level='province', max_depth=4, version_number=None): ...
    def get_feature_collection(self, registry_slug, admin_level=None, parent_code=None, version_number=None): ...
```

### Step 3: Serializer internal sederhana

Tambahkan helper internal untuk membentuk:
- option item `{label, value, meta}`
- lookup payload detail
- feature collection GeoJSON ringan

### Step 4: Jalankan behavior tests

Run:
`docker exec -w /usr/src/app dasborkanwil_app sh -lc 'PYTHONPATH=/usr/src/app pytest tests/test_data_registry_service_behaviors.py -q'`

Expected:
- PASS untuk serving contract service-layer.

### Step 5: Commit

Message rekomendasi:
`feat: add data registry query services for consumer API`

---

## Task 7: Implement API v1 Domain 4

**Objective:** mengekspose published registry sebagai consumer API tipis untuk frontend dan runtime form.

**Files:**
- Create: `app/api/v1/data_registries/__init__.py`
- Create: `app/api/v1/data_registries/routes.py`
- Modify: `app/__init__.py`

### Step 1: Buat blueprint API baru

`app/api/v1/data_registries/routes.py`
minimal:
```python
api_data_registry_bp = Blueprint(
    'api_data_registry_v1',
    __name__,
    url_prefix='/api/v1',
)
```

### Step 2: Endpoint lifecycle admin/internal

Endpoint minimal:
- `POST /api/v1/data-registries`
- `GET /api/v1/data-registries/<int:registry_id>`
- `POST /api/v1/data-registries/<int:registry_id>/versions/draft`
- `POST /api/v1/data-registry-versions/<int:version_id>/publish`

### Step 3: Endpoint consumer/published resource

Endpoint minimal v1:
- `GET /api/v1/registry-resources/<string:registry_slug>/options`
- `GET /api/v1/registry-resources/<string:registry_slug>/lookup`
- `GET /api/v1/registry-resources/<string:registry_slug>/children`
- `GET /api/v1/registry-resources/<string:registry_slug>/tree`
- `GET /api/v1/registry-resources/<string:registry_slug>/feature-collection`

### Step 4: Prinsip route

Semua route harus tipis seperti route form/submission yang sudah ada:
- parsing request
- panggil service
- serialize response
- tangani `ValueError` -> 400
- tangani `PermissionError` -> 403
- tangani error tak terduga -> rollback + 500

### Step 5: Register blueprint di `app/__init__.py`

Tambahkan:
```python
from .api.v1.data_registries.routes import api_data_registry_bp
app.register_blueprint(api_data_registry_bp)
csrf.exempt(api_data_registry_bp)
```

### Step 6: Jalankan smoke route test manual

Run:
`docker exec -w /usr/src/app dasborkanwil_app sh -lc 'PYTHONPATH=/usr/src/app python - <<"PY"
from app import create_app
app = create_app("testing")
for rule in sorted(str(r.rule) for r in app.url_map.iter_rules() if "registry" in r.rule):
    print(rule)
PY'`

Catatan: jika `python` belum tersedia di shell container, gunakan pendekatan yang sama melalui test pytest atau `execute_code` saat sesi agent.

### Step 7: Commit

Message rekomendasi:
`feat: add data registry api v1 routes`

---

## Task 8: Tambah API tests Domain 4

**Objective:** memverifikasi route registration dan payload contract tanpa menunggu UI.

**Files:**
- Create: `tests/test_api_data_registry_routes.py`

### Step 1: Tulis route registration tests

Minimal route yang harus ada:
- `/api/v1/data-registries`
- `/api/v1/data-registries/<int:registry_id>`
- `/api/v1/data-registries/<int:registry_id>/versions/draft`
- `/api/v1/data-registry-versions/<int:version_id>/publish`
- `/api/v1/registry-resources/<string:registry_slug>/options`
- `/api/v1/registry-resources/<string:registry_slug>/lookup`
- `/api/v1/registry-resources/<string:registry_slug>/children`
- `/api/v1/registry-resources/<string:registry_slug>/tree`
- `/api/v1/registry-resources/<string:registry_slug>/feature-collection`

### Step 2: Tulis payload tests dengan monkeypatch service

Minimal skenario:
1. create registry success
2. create draft version success
3. publish version success
4. options endpoint success
5. lookup endpoint success
6. children endpoint success
7. validation error distandarkan ke `400 + data.error_type='validation_error'`
8. authorization error distandarkan ke `403 + data.error_type='authorization_error'`

### Step 3: Jalankan test API

Run:
`docker exec -w /usr/src/app dasborkanwil_app sh -lc 'PYTHONPATH=/usr/src/app pytest tests/test_api_data_registry_routes.py -q'`

Expected:
- PASS seluruh route contract dasar.

### Step 4: Commit

Message rekomendasi:
`test: add api contract tests for data registry`

---

## Task 9: Full regression test dan housekeeping

**Objective:** memastikan fondasi Domain 4 tidak merusak fondasi form/submission yang sudah ada.

**Files:**
- Modify bila perlu: docs arsitektur yang menautkan implementation plan

### Step 1: Tautkan dokumen implementation plan ini

Tambahkan tautan ke file ini dari:
- `docs/architecture/domain-4-master-data-registry-v1.md`
- `docs/architecture/domain-4-wilayah-schema-contract-v1.md`
- `docs/architecture/domain-4-wilayah-migration-schema-plan-v1.md`

### Step 2: Jalankan seluruh test suite

Run:
`docker exec -w /usr/src/app dasborkanwil_app sh -lc 'PYTHONPATH=/usr/src/app pytest tests/ -q'`

Expected:
- semua test existing tetap pass
- test Domain 4 pass

### Step 3: Verifikasi Alembic head

Run:
`docker exec -w /usr/src/app dasborkanwil_app sh -lc 'PYTHONPATH=/usr/src/app flask db current'`

### Step 4: Commit

Message rekomendasi:
`docs: link domain 4 wilayah implementation plan`

---

## 5. Catatan desain API resource dinamis

Agar menjawab concern user secara eksplisit:

### 5.1. Ya, Domain 4 bisa publish API resource dinamis
Tetapi definisi “dinamis” di sini harus disiplin:
- dinamis di level **registry resource selection**
- bukan dinamis di level **query arbitrary bebas**

Contoh yang sehat:
- Form component memilih `registry_slug=wilayah.administratif`
- runtime minta `/api/v1/registry-resources/wilayah.administratif/options?admin_level=district&parent_code=3201`
- backend membaca published version aktif
- backend mengembalikan `label/value/meta`

### 5.2. Kenapa ini sehat
Karena:
- frontend form tidak perlu tahu tabel fisik
- runtime tidak query CSV/raw submission langsung
- publish boundary tetap stabil
- versioning tetap dijaga
- nanti registry lain selain wilayah bisa memakai serving contract yang sama

### 5.3. Yang belum perlu di v1
- query builder bebas berbasis semua field JSONB
- user-defined endpoint generator penuh
- GraphQL-like registry explorer
- ABAC policy final per endpoint resource
- external public API hardening lengkap

---

## 6. Risiko yang harus dijaga saat implementasi

1. Jangan campur lifecycle draft registry dengan consumer query published.
2. Jangan biarkan options endpoint membaca draft by default.
3. Jangan simpan field filter penting hanya di JSONB.
4. Jangan implementasi ingest CSV sebelum contract service+API stabil.
5. Jangan buat endpoint terlalu generik sampai boundary Domain 4 kabur.
6. Jangan lupa import model baru di `app/__init__.py`, karena ini penting untuk metadata migration.

---

## 7. Definisi selesai untuk slice implementasi pertama

Slice ini dianggap selesai bila:
- migration baru sudah ada dan bisa `upgrade`;
- model Domain 4 sudah terbaca app;
- repository/service/query service dasar sudah ada;
- API v1 registry resource dasar sudah terdaftar;
- test metadata, service contract/behavior, dan API route pass;
- docs arsitektur saling tertaut rapi.

---

## 8. Next step setelah plan ini dieksekusi

Setelah implementation plan ini selesai di-code, next step paling natural adalah:
1. bootstrap seed registry `wilayah.administratif`;
2. implement command/service ingest CSV flat -> hierarchy records;
3. integrasi Form Builder agar field select bisa memilih registry resource sebagai option source;
4. evaluasi apakah perlu `data_registry_sources`, `data_registry_mappings`, dan `data_registry_ingestion_runs` pada iterasi berikutnya.

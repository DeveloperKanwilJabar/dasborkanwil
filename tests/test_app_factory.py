from io import BytesIO
from types import SimpleNamespace
from zipfile import ZipFile

from app import create_app
from app.core.extensions import db
from app.modules.form.import_services import FormDataImportPipelineService
from app.modules.form.models import FormVersion
from app.modules.import_pipeline.models import ImportBatch, ImportBatchRow


def test_create_app_testing_config_enables_testing_mode():
    app = create_app('testing')

    assert app.testing is True
    assert app.config['LOGIN_DISABLED'] is True
    assert app.config['WTF_CSRF_ENABLED'] is False


def test_index_page_smoke_returns_success():
    app = create_app('testing')

    client = app.test_client()
    response = client.get('/')

    assert response.status_code == 200


def test_form_list_page_smoke_returns_grid_contract():
    app = create_app('testing')

    client = app.test_client()
    response = client.get('/forms')

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'Daftar Form' in html
    assert 'id="forms-table-data"' in html
    assert 'libs/gridjs/dist/gridjs.umd.js' in html
    assert 'js/pages/forms.js' in html
    assert 'formsDataUrl' in html
    assert 'builderUrlTemplate' in html
    assert 'previewUrlTemplate' in html
    assert 'templateUrlTemplate' in html
    assert 'importMappingUrlTemplate' in html


def test_form_builder_page_smoke_returns_velzon_container_and_assets():
    app = create_app('testing')

    client = app.test_client()
    response = client.get('/forms/builder')

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'Form Builder' in html
    assert 'id="formioBuilder"' in html
    assert 'libs/@formio/js/dist/formio.builder.min.css' in html
    assert 'libs/@formio/js/dist/formio.full.min.js' in html
    assert 'id="formBuilderCreateForm"' in html
    assert 'id="formBuilderCreateFormBtn"' in html
    assert 'Buat Form & Draft' in html
    assert 'id="formBuilderManualSaveBtn"' in html
    assert 'id="formBuilderPublishBtn"' in html
    assert 'Publish Draft' in html
    assert 'id="formBuilderPreviewFormBtn"' in html
    assert 'Preview / Isi Form' in html
    assert 'id="formBuilderPreviewFormBtn" aria-disabled="true"' in html
    assert 'js/pages/form-builder.js' in html
    assert 'createFormUrl' in html
    assert 'autosaveUrlTemplate' in html
    assert 'publishUrlTemplate' in html
    assert 'Preset Konsumen Registry' in html
    assert 'id="formBuilderInsertWilayahCascadeBtn"' in html
    assert 'registryConsumerPresets' in html
    assert 'formioBaseUrl' in html
    assert 'http://localhost/api/v1/registry-resources/wilayah.administratif/options?admin_level=province' in html


def test_forms_data_returns_form_list_payload(monkeypatch):
    app = create_app('testing')
    form = SimpleNamespace(
        id=1,
        uuid='form-uuid',
        code='FORM-LIST',
        slug='form-list',
        name='Form List',
        description=None,
        status='draft',
        visibility='internal',
        created_at=None,
        updated_at=None,
    )
    draft_version = SimpleNamespace(id=3, version_number=2, schema={'components': [{'key': 'nama'}]})

    class StubFormService:
        repository = SimpleNamespace(get_all=lambda: [form])

    class StubFormVersionService:
        def get_draft_version(self, form_id):
            return draft_version

        def get_published_version(self, form_id):
            return None

    monkeypatch.setattr('app.modules.form.routes_web.FormService', StubFormService)
    monkeypatch.setattr('app.modules.form.routes_web.FormVersionService', StubFormVersionService)

    client = app.test_client()
    response = client.get('/forms/data')

    assert response.status_code == 200
    payload = response.get_json()
    assert payload[0]['code'] == 'FORM-LIST'
    assert payload[0]['draft_version_number'] == 2
    assert payload[0]['published_version_number'] is None
    assert payload[0]['component_count'] == 1


def test_form_builder_with_form_id_loads_existing_draft_schema(monkeypatch):
    app = create_app('testing')

    class StubFormVersionService:
        def get_draft_version(self, form_id):
            return SimpleNamespace(
                id=7,
                form_id=form_id,
                version_number=2,
                status='draft',
                is_published=False,
                schema={'display': 'form', 'components': [{'key': 'nama', 'type': 'textfield'}]},
            )

        def get_published_version(self, form_id):
            return None

    class StubFormService:
        def get_form_detail(self, form_id):
            return SimpleNamespace(
                id=form_id,
                code='FORM-DRAFT',
                slug='form-draft',
                name='Form Draft',
                description='Deskripsi draft',
                visibility='internal',
            )

    monkeypatch.setattr('app.modules.form.routes_web.FormVersionService', StubFormVersionService)
    monkeypatch.setattr('app.modules.form.routes_web.FormService', StubFormService)

    client = app.test_client()
    response = client.get('/forms/builder?form_id=1')

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'Edit Draft' in html
    assert 'draftVersionId: 7' in html
    assert 'builderMode: "edit_draft"' in html
    assert 'Version Number' in html
    assert '<h6 class="mb-0" id="formBuilderDraftVersionId">2</h6>' in html
    assert 'aria-disabled="true"' in html
    assert 'value="Form Draft"' in html
    assert 'value="FORM-DRAFT"' in html
    assert 'value="form-draft"' in html
    assert 'Deskripsi draft' in html
    assert '"key": "nama"' in html


def test_form_builder_with_form_id_falls_back_to_published_source(monkeypatch):
    app = create_app('testing')

    class StubFormVersionService:
        def get_draft_version(self, form_id):
            return None

        def get_published_version(self, form_id):
            return SimpleNamespace(
                id=9,
                form_id=form_id,
                version_number=1,
                status='published',
                is_published=True,
                schema={'display': 'form', 'components': [{'key': 'judul', 'type': 'textfield'}]},
            )

    monkeypatch.setattr('app.modules.form.routes_web.FormVersionService', StubFormVersionService)

    client = app.test_client()
    response = client.get('/forms/builder?form_id=1')

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'Published Source' in html
    assert 'draftVersionId: null' in html
    assert 'sourceVersionId: 9' in html
    assert 'builderMode: "published_source"' in html
    assert '<h6 class="mb-0" id="formBuilderDraftVersionId">1</h6>' in html
    assert 'aria-disabled="false"' in html
    assert '"key": "judul"' in html


def test_form_import_service_extracts_fields_and_builds_xlsx_template():
    service = FormDataImportPipelineService()
    form = SimpleNamespace(id=1, uuid='form-uuid', code='FORM-IMPORT', slug='form-import', name='Form Import')
    version = SimpleNamespace(
        id=2,
        uuid='version-uuid',
        version_number=1,
        is_published=True,
        status='published',
        schema={
            'display': 'form',
            'components': [
                {'type': 'textfield', 'key': 'nama', 'label': 'Nama', 'validate': {'required': True}},
                {'type': 'number', 'key': 'jumlah', 'label': 'Jumlah'},
                {'type': 'button', 'key': 'submit', 'label': 'Submit'},
            ],
        },
    )

    fields = service.extract_importable_fields(version.schema)
    workbook = service.build_template_workbook(form, version)

    assert [field['key'] for field in fields] == ['nama', 'jumlah']
    assert fields[0]['required'] is True
    with ZipFile(BytesIO(workbook)) as archive:
        names = archive.namelist()
        assert 'xl/workbook.xml' in names
        assert 'xl/worksheets/sheet1.xml' in names
        sheet = archive.read('xl/worksheets/sheet1.xml').decode('utf-8')
        assert 'Nama' in sheet
        assert 'Jumlah' in sheet
        assert 'nama' in sheet
        assert 'jumlah' in sheet


def test_form_export_template_route_returns_xlsx(monkeypatch):
    app = create_app('testing')
    form = SimpleNamespace(id=1, uuid='form-uuid', code='FORM-XLSX', slug='form-xlsx', name='Form XLSX')
    version = SimpleNamespace(
        id=3,
        uuid='version-uuid',
        version_number=1,
        is_published=True,
        status='published',
        schema={'display': 'form', 'components': [{'type': 'textfield', 'key': 'nama', 'label': 'Nama'}]},
    )

    class StubFormService:
        def get_form_detail(self, form_id):
            return form

    class StubFormVersionService:
        def get_published_version(self, form_id):
            return version

    monkeypatch.setattr('app.modules.form.routes_web.FormService', StubFormService)
    monkeypatch.setattr('app.modules.form.routes_web.FormVersionService', StubFormVersionService)

    client = app.test_client()
    response = client.get('/forms/1/template.xlsx')

    assert response.status_code == 200
    assert response.mimetype == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    assert 'attachment;' in response.headers['Content-Disposition']
    assert response.data.startswith(b'PK')


def test_form_import_mapping_page_get_returns_upload_contract(monkeypatch):
    app = create_app('testing')
    form = SimpleNamespace(id=1, uuid='form-uuid', code='FORM-IMPORT', slug='form-import', name='Form Import')
    version = SimpleNamespace(
        id=3,
        uuid='version-uuid',
        version_number=1,
        is_published=True,
        status='published',
        schema={'display': 'form', 'components': [{'type': 'textfield', 'key': 'nama', 'label': 'Nama'}]},
    )

    class StubFormService:
        def get_form_detail(self, form_id):
            return form

    class StubFormVersionService:
        def get_published_version(self, form_id):
            return version

    monkeypatch.setattr('app.modules.form.routes_web.FormService', StubFormService)
    monkeypatch.setattr('app.modules.form.routes_web.FormVersionService', StubFormVersionService)

    client = app.test_client()
    response = client.get('/forms/1/import/mapping')

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'Import Data Form' in html
    assert 'id="excel_file"' in html
    assert 'Mapping Kolom' in html
    assert 'Download Template Excel' in html


def test_form_import_mapping_page_read_only_when_actor_cannot_submit(monkeypatch):
    app = create_app('testing')
    form = SimpleNamespace(id=1, uuid='form-uuid', code='FORM-IMPORT', slug='form-import', name='Form Import')
    version = SimpleNamespace(
        id=3,
        uuid='version-uuid',
        version_number=1,
        is_published=True,
        status='published',
        schema={'display': 'form', 'components': [{'type': 'textfield', 'key': 'nama', 'label': 'Nama'}]},
    )

    class StubFormService:
        def get_form_detail(self, form_id):
            return form

    class StubFormVersionService:
        def get_published_version(self, form_id):
            return version

    monkeypatch.setattr('app.modules.form.routes_web.FormService', StubFormService)
    monkeypatch.setattr('app.modules.form.routes_web.FormVersionService', StubFormVersionService)
    monkeypatch.setattr('app.modules.form.routes_web.can_submit_form', lambda actor, form: False)

    client = app.test_client()
    response = client.get('/forms/1/import/mapping')

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'mode review-only' in html
    assert 'Upload &amp; Baca Kolom' in html or 'Upload & Baca Kolom' in html
    assert html.count('disabled') >= 2


def test_form_import_mapping_upload_reads_headers_and_auto_mapping(monkeypatch):
    app = create_app('testing')
    service = FormDataImportPipelineService()
    form = SimpleNamespace(id=1, uuid='form-uuid', code='FORM-IMPORT', slug='form-import', name='Form Import')
    version = SimpleNamespace(
        id=3,
        uuid='version-uuid',
        version_number=1,
        is_published=True,
        status='published',
        schema={'display': 'form', 'components': [{'type': 'textfield', 'key': 'nama', 'label': 'Nama'}]},
    )
    workbook = service.build_template_workbook(form, version)

    class StubFormService:
        def get_form_detail(self, form_id):
            return form

    class StubFormVersionService:
        def get_published_version(self, form_id):
            return version

    monkeypatch.setattr('app.modules.form.routes_web.FormService', StubFormService)
    monkeypatch.setattr('app.modules.form.routes_web.FormVersionService', StubFormVersionService)

    client = app.test_client()
    response = client.post(
        '/forms/1/import/mapping',
        data={'action': 'preview_mapping', 'excel_file': (BytesIO(workbook), 'template.xlsx')},
        content_type='multipart/form-data',
    )

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'template.xlsx' in html
    assert 'Nama' in html
    assert 'name="mapping_nama"' in html
    assert 'selected' in html
    assert 'Buat Batch Import' in html
    assert 'csrf_token' in html


def test_import_batch_models_registered_in_app_metadata():
    app = create_app('testing')

    with app.app_context():
        assert 'import_batches' in db.metadata.tables
        assert 'import_batch_rows' in db.metadata.tables
        assert ImportBatch.__tablename__ == 'import_batches'
        assert ImportBatchRow.__tablename__ == 'import_batch_rows'


def test_import_service_creates_import_batch_and_rows_from_mapping(monkeypatch):
    service = FormDataImportPipelineService()
    added_objects = []

    class FakeSession:
        def add(self, obj):
            if isinstance(obj, ImportBatch) and obj.id is None:
                obj.id = 10
            added_objects.append(obj)

        def flush(self):
            return None

        def commit(self):
            return None

        def rollback(self):
            return None

    monkeypatch.setattr('app.modules.form.import_services.db.session', FakeSession())

    form = SimpleNamespace(
        id=1,
        uuid='form-import-batch-uuid',
        code='FORM-BATCH',
        slug='form-batch',
        name='Form Batch',
    )
    version = SimpleNamespace(
        id=2,
        uuid='form-version-import-batch-uuid',
        version_number=1,
        schema={'display': 'form', 'components': [{'type': 'textfield', 'key': 'nama', 'label': 'Nama'}]},
        status='published',
        is_published=True,
    )
    workbook = service._create_xlsx([
        {'name': 'data', 'rows': [['Nama'], ['Alice'], ['Bob']]},
    ])
    upload = SimpleNamespace(filename='data.xlsx', read=lambda: workbook)

    batch = service.create_import_batch_from_workbook(
        form,
        version,
        upload,
        {'nama': 'Nama'},
    )
    rows = [obj for obj in added_objects if isinstance(obj, ImportBatchRow)]

    assert batch.status == ImportBatch.STATUS_MAPPED
    assert batch.total_rows == 2
    assert batch.mapped_rows == 2
    assert batch.mapping_config == {'nama': 'Nama'}
    assert len(rows) == 2
    assert rows[0].row_number == 2
    assert rows[0].mapped_payload == {'nama': 'Alice'}
    assert rows[1].mapped_payload == {'nama': 'Bob'}
    assert rows[0].row_hash


def test_form_import_mapping_create_batch_redirects_to_resume(monkeypatch):
    app = create_app('testing')
    form = SimpleNamespace(id=1, uuid='form-uuid', code='FORM-IMPORT', slug='form-import', name='Form Import')
    version = SimpleNamespace(
        id=3,
        uuid='version-uuid',
        version_number=1,
        is_published=True,
        status='published',
        schema={'display': 'form', 'components': [{'type': 'textfield', 'key': 'nama', 'label': 'Nama'}]},
    )

    class StubFormService:
        def get_form_detail(self, form_id):
            return form

    class StubFormVersionService:
        def get_published_version(self, form_id):
            return version

    class StubImportService:
        def extract_importable_fields(self, schema):
            return [{'key': 'nama', 'label': 'Nama', 'type': 'textfield', 'required': False, 'path': 'nama'}]

        def create_import_batch_from_workbook(self, form_arg, version_arg, upload, mapping_config, actor=None):
            assert mapping_config == {'nama': 'Nama'}
            return SimpleNamespace(id=77)

    monkeypatch.setattr('app.modules.form.routes_web.FormService', StubFormService)
    monkeypatch.setattr('app.modules.form.routes_web.FormVersionService', StubFormVersionService)
    monkeypatch.setattr('app.modules.form.routes_web.FormDataImportPipelineService', StubImportService)

    client = app.test_client()
    response = client.post(
        '/forms/1/import/mapping',
        data={
            'action': 'create_batch',
            'mapping_nama': 'Nama',
            'excel_file': (BytesIO(b'dummy'), 'data.xlsx'),
        },
        content_type='multipart/form-data',
    )

    assert response.status_code == 302
    assert response.headers['Location'].endswith('/forms/import/batches/77')


def test_form_import_batch_resume_page_returns_summary(monkeypatch):
    app = create_app('testing')
    batch = SimpleNamespace(
        id=77,
        uuid='batch-uuid',
        form_id=1,
        form=SimpleNamespace(name='Form Import', code='FORM-IMPORT'),
        form_version=SimpleNamespace(version_number=1),
        status='mapped',
        original_filename='data.xlsx',
        total_rows=1,
        mapped_rows=1,
        valid_rows=0,
        error_rows=0,
        created_at='2026-05-08',
    )
    rows = [SimpleNamespace(row_number=2, status='mapped', mapped_payload={'nama': 'Alice'}, validation_errors=None)]

    class StubImportService:
        def get_import_batch_summary(self, batch_id):
            return {'batch': batch, 'rows': rows, 'error_rows': []}

    monkeypatch.setattr('app.modules.form.routes_web.FormDataImportPipelineService', StubImportService)

    client = app.test_client()
    response = client.get('/forms/import/batches/77')

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'Resume Import Batch' in html
    assert 'batch-uuid' in html
    assert 'data.xlsx' in html
    assert 'Alice' in html
    assert 'Proses Validasi & Import' in html
    assert 'Download Error Excel' in html


def test_form_import_batch_resume_page_disables_process_when_actor_cannot_submit(monkeypatch):
    app = create_app('testing')
    batch = SimpleNamespace(
        id=78,
        uuid='batch-uuid-2',
        form_id=2,
        form=SimpleNamespace(name='Form Import Read Only', code='FORM-IMPORT-RO'),
        form_version=SimpleNamespace(version_number=1),
        status='mapped',
        original_filename='data-error.xlsx',
        total_rows=3,
        mapped_rows=3,
        valid_rows=1,
        error_rows=2,
        created_at='2026-05-08',
    )
    rows = [SimpleNamespace(row_number=2, status='error', mapped_payload={'nama': 'Bob'}, validation_errors='required')]

    class StubImportService:
        def get_import_batch_summary(self, batch_id):
            return {
                'batch': batch,
                'rows': rows,
                'error_rows': rows,
                'error_rows_count': 2,
            }

    monkeypatch.setattr('app.modules.form.routes_web.FormDataImportPipelineService', StubImportService)
    monkeypatch.setattr('app.modules.form.routes_web.can_submit_form', lambda actor, form: False)

    client = app.test_client()
    response = client.get('/forms/import/batches/78')

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'Akun Anda tidak memiliki izin submit untuk form ini.' in html
    assert 'Proses Validasi &amp; Import' in html or 'Proses Validasi & Import' in html
    assert "document.getElementById('formImportFlashMessages')" in html
    assert html.count('disabled') >= 3


def test_import_validation_checks_required_number_email_and_options():
    service = FormDataImportPipelineService()
    fields = [
        {'key': 'nama', 'label': 'Nama', 'type': 'textfield', 'required': True, 'options': []},
        {'key': 'jumlah', 'label': 'Jumlah', 'type': 'number', 'required': False, 'options': []},
        {'key': 'email', 'label': 'Email', 'type': 'email', 'required': False, 'options': []},
        {'key': 'status', 'label': 'Status', 'type': 'select', 'required': False, 'options': [{'value': 'aktif'}]},
    ]

    invalid = service.validate_mapped_payload(
        {'nama': '', 'jumlah': 'abc', 'email': 'not-email', 'status': 'unknown'},
        fields,
    )
    valid = service.validate_mapped_payload(
        {'nama': 'Alice', 'jumlah': '10', 'email': 'alice@example.test', 'status': 'aktif'},
        fields,
    )

    assert invalid['is_valid'] is False
    assert {error['code'] for error in invalid['errors']} == {'required', 'invalid_number', 'invalid_email', 'invalid_option'}
    assert valid['is_valid'] is True


def test_import_service_process_batch_validates_imports_and_marks_duplicates(monkeypatch):
    service = FormDataImportPipelineService()
    batch = ImportBatch(
        id=99,
        uuid='batch-uuid',
        form_id=1,
        form_version_id=2,
        status=ImportBatch.STATUS_MAPPED,
        total_rows=3,
        mapped_rows=3,
        original_filename='data.xlsx',
    )
    batch.form_version = FormVersion(
        id=2,
        form_id=1,
        version_number=1,
        status='published',
        is_published=True,
        schema={
            'display': 'form',
            'components': [
                {'type': 'textfield', 'key': 'nama', 'label': 'Nama', 'validate': {'required': True}},
            ],
        },
    )
    row_valid = ImportBatchRow(
        id=1,
        uuid='row-valid',
        import_batch_id=99,
        row_number=2,
        status=ImportBatchRow.STATUS_MAPPED,
        mapped_payload={'nama': 'Alice'},
        row_hash='hash-1',
    )
    row_error = ImportBatchRow(
        id=2,
        uuid='row-error',
        import_batch_id=99,
        row_number=3,
        status=ImportBatchRow.STATUS_MAPPED,
        mapped_payload={'nama': ''},
        row_hash='hash-2',
    )
    row_duplicate = ImportBatchRow(
        id=3,
        uuid='row-duplicate',
        import_batch_id=99,
        row_number=4,
        status=ImportBatchRow.STATUS_MAPPED,
        mapped_payload={'nama': 'Bob'},
        row_hash='hash-existing',
    )
    batch.rows = [row_valid, row_error, row_duplicate]

    class StubBatchRepository:
        def get_by_id(self, batch_id):
            return batch

    class StubSubmissionService:
        def submit(self, form_id, payload, actor=None, context=None):
            assert form_id == 1
            assert payload == {'nama': 'Alice'}
            assert context['source_type'] == 'excel_import'
            assert context['source_ref'] == 'batch-uuid'
            return SimpleNamespace(id=123)

    class FakeSession:
        def flush(self):
            return None

        def commit(self):
            return None

        def rollback(self):
            return None

    monkeypatch.setattr('app.modules.form.import_services.ImportBatchRepository', StubBatchRepository)
    monkeypatch.setattr('app.modules.form.import_services.SubmissionService', StubSubmissionService)
    monkeypatch.setattr('app.modules.form.import_services.db.session', FakeSession())
    monkeypatch.setattr(service, '_load_existing_imported_hashes', lambda form_id, form_version_id, exclude_batch_id=None: {'hash-existing'})

    result = service.process_import_batch(99)

    assert result['status'] == ImportBatch.STATUS_COMPLETED_WITH_ERRORS
    assert result['valid_rows'] == 1
    assert result['error_rows'] == 1
    assert result['duplicate_rows'] == 1
    assert row_valid.status == ImportBatchRow.STATUS_IMPORTED
    assert row_valid.submission_id == 123
    assert row_error.status == ImportBatchRow.STATUS_ERROR
    assert row_error.validation_errors[0]['code'] == 'required'
    assert row_duplicate.status == ImportBatchRow.STATUS_DUPLICATE
    assert row_duplicate.validation_errors[0]['code'] == 'duplicate'


def test_form_process_import_batch_route_redirects_to_resume(monkeypatch):
    app = create_app('testing')
    processed = {}

    class StubImportService:
        def process_import_batch(self, batch_id, actor=None):
            processed['batch_id'] = batch_id
            return {'status': 'completed'}

    monkeypatch.setattr('app.modules.form.routes_web.FormDataImportPipelineService', StubImportService)

    client = app.test_client()
    response = client.post('/forms/import/batches/77/process')

    assert response.status_code == 302
    assert response.headers['Location'].endswith('/forms/import/batches/77')
    assert processed['batch_id'] == 77


def test_build_error_workbook_matches_template_shape_with_inline_field_errors(monkeypatch):
    service = FormDataImportPipelineService()
    batch = SimpleNamespace(
        uuid='batch-uuid',
        original_filename='data.xlsx',
        form=SimpleNamespace(code='FORM-IMPORT', name='Form Import'),
        form_version=SimpleNamespace(
            version_number=1,
            schema={
                'display': 'form',
                'components': [
                    {'type': 'textfield', 'key': 'nama', 'label': 'Nama', 'validate': {'required': True}},
                    {'type': 'email', 'key': 'email', 'label': 'Email'},
                    {'type': 'number', 'key': 'jumlah', 'label': 'Jumlah'},
                ],
            },
        ),
        created_at='2026-05-12T07:00:00Z',
    )
    error_rows = [
        SimpleNamespace(
            row_number=3,
            status='error',
            raw_payload={'Nama': '', 'Email': 'bad', 'Jumlah': 'sepuluh'},
            mapped_payload={'nama': '', 'email': 'bad', 'jumlah': 'sepuluh'},
            validation_errors=[
                {'field': 'nama', 'code': 'required', 'message': 'Nama wajib diisi.'},
                {'field': 'email', 'code': 'invalid_email', 'message': 'Email harus berupa email valid.'},
            ],
        )
    ]

    workbook = service.build_error_workbook(batch, error_rows)
    rows = service._read_first_sheet_rows(workbook, max_rows=10)

    assert rows[0] == ['Nama', 'Email', 'Jumlah']
    assert 'Nama wajib diisi.' in rows[1][0]
    assert rows[1][1].startswith('bad')
    assert 'Email harus berupa email valid.' in rows[1][1]
    assert rows[1][2] == 'sepuluh'


def test_download_import_batch_errors_returns_excel_attachment(monkeypatch):
    app = create_app('testing')
    batch = SimpleNamespace(id=77)
    workbook = b'fake-xlsx-content'

    class StubImportService:
        def export_import_batch_errors(self, batch_id):
            assert batch_id == 77
            return {
                'batch': batch,
                'filename': 'FORM-IMPORT-v1-errors.xlsx',
                'content': workbook,
            }

    monkeypatch.setattr('app.modules.form.routes_web.FormDataImportPipelineService', StubImportService)

    client = app.test_client()
    response = client.get('/forms/import/batches/77/errors.xlsx')

    assert response.status_code == 200
    assert response.data == workbook
    assert 'attachment; filename=FORM-IMPORT-v1-errors.xlsx' in response.headers['Content-Disposition']
    assert response.mimetype == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'


def test_reimport_error_workbook_creates_new_batch_from_previous_batch(monkeypatch):
    service = FormDataImportPipelineService()
    created_batches = []

    old_batch = SimpleNamespace(
        id=11,
        uuid='batch-old-uuid',
        form_id=1,
        form_version_id=2,
        form=SimpleNamespace(id=1, uuid='form-uuid', code='FORM-IMPORT', slug='form-import', name='Form Import'),
        form_version=SimpleNamespace(
            id=2,
            uuid='version-uuid',
            version_number=1,
            status='published',
            is_published=True,
            schema={'display': 'form', 'components': [
                {'type': 'textfield', 'key': 'nama', 'label': 'Nama', 'validate': {'required': True}},
                {'type': 'email', 'key': 'email', 'label': 'Email'},
            ]},
        ),
        mapping_config={'nama': 'Nama Lama', 'email': 'Email Lama'},
        rows=[],
    )

    class StubBatchRepository:
        def get_by_id(self, batch_id):
            assert batch_id == 11
            return old_batch

    class FakeSession:
        def add(self, obj):
            if isinstance(obj, ImportBatch) and obj.id is None:
                obj.id = 88
            created_batches.append(obj)

        def flush(self):
            return None

        def commit(self):
            return None

        def rollback(self):
            return None

    monkeypatch.setattr('app.modules.form.import_services.ImportBatchRepository', StubBatchRepository)
    monkeypatch.setattr('app.modules.form.import_services.db.session', FakeSession())

    workbook = service._create_xlsx([
        {'name': 'data', 'rows': [
            ['Nama', 'Email'],
            ['Alice', 'alice@example.com'],
            ['Bob', 'bob@example.com'],
        ]},
    ])
    upload = SimpleNamespace(filename='FORM-IMPORT-v1-errors.xlsx', read=lambda: workbook)

    new_batch = service.reimport_corrected_error_workbook(11, upload)
    rows = [obj for obj in created_batches if isinstance(obj, ImportBatchRow)]

    assert new_batch.id == 88
    assert new_batch.meta['created_from'] == 'error_reimport'
    assert new_batch.meta['reimport_of_batch_id'] == 11
    assert new_batch.mapping_config == {'nama': 'Nama', 'email': 'Email'}
    assert len(rows) == 2
    assert rows[0].mapped_payload == {'nama': 'Alice', 'email': 'alice@example.com'}
    assert rows[1].mapped_payload == {'nama': 'Bob', 'email': 'bob@example.com'}


def test_reimport_error_workbook_route_redirects_to_new_processed_batch(monkeypatch):
    app = create_app('testing')
    processed = {}

    class StubImportService:
        def reimport_corrected_error_workbook(self, batch_id, upload, actor=None):
            processed['source_batch_id'] = batch_id
            processed['filename'] = upload.filename
            return SimpleNamespace(id=91)

        def process_import_batch(self, batch_id, actor=None):
            processed['processed_batch_id'] = batch_id
            return {'status': 'completed'}

    monkeypatch.setattr('app.modules.form.routes_web.FormDataImportPipelineService', StubImportService)

    client = app.test_client()
    response = client.post(
        '/forms/import/batches/77/reimport',
        data={'excel_file': (BytesIO(b'dummy'), 'FORM-IMPORT-v1-errors.xlsx')},
        content_type='multipart/form-data',
    )

    assert response.status_code == 302
    assert response.headers['Location'].endswith('/forms/import/batches/91')
    assert processed['source_batch_id'] == 77
    assert processed['processed_batch_id'] == 91
    assert processed['filename'] == 'FORM-IMPORT-v1-errors.xlsx'


def test_form_preview_page_smoke_returns_preview_container_and_submit_contract():
    app = create_app('testing')

    client = app.test_client()
    response = client.get('/forms/1/preview')

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'Preview Form' in html
    assert 'id="formioPreview"' not in html
    assert 'Belum Published' in html
    assert 'libs/@formio/js/dist/formio.form.min.css' in html
    assert 'libs/@formio/js/dist/formio.full.min.js' in html
    assert 'js/pages/form-preview.js' in html
    assert 'formioBaseUrl' in html
    assert 'submitUrl' in html

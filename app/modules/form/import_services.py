import hashlib
import json
import re
import uuid
from collections import defaultdict
from io import BytesIO

from openpyxl import Workbook, load_workbook

from app.core.extensions import db
from app.core.utils import now_utc
from app.modules.import_pipeline.models import ImportBatch, ImportBatchRow
from app.modules.import_pipeline.repositories import ImportBatchRepository
from app.modules.submission.services import SubmissionService


IMPORTABLE_COMPONENT_TYPES = {
    'textfield',
    'textarea',
    'number',
    'currency',
    'datetime',
    'day',
    'time',
    'select',
    'radio',
    'checkbox',
    'selectboxes',
    'email',
    'phoneNumber',
    'url',
}

SKIPPED_COMPONENT_TYPES = {
    'button',
    'html',
    'content',
    'panel',
    'fieldset',
    'well',
    'columns',
    'table',
    'tabs',
    'container',
    'datagrid',
    'editgrid',
    'hidden',
}

XML_NS = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
REL_NS = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
PKG_REL_NS = 'http://schemas.openxmlformats.org/package/2006/relationships'
CONTENT_NS = 'http://schemas.openxmlformats.org/package/2006/content-types'


class FormDataImportPipelineService:
    """Service awal Form Data Import Pipeline v1.

    Scope saat ini:
    - extract field importable dari published Form.io schema,
    - export template Excel sederhana berbasis schema,
    - parse header/sample row Excel untuk halaman mapping,
    - membuat import batch + row staging hasil mapping.

    Service ini belum melakukan validasi final dan belum insert submission.
    """

    def build_template_workbook(self, form, form_version):
        if not form_version or not getattr(form_version, 'is_published', False) or getattr(form_version, 'status', None) != 'published':
            raise ValueError('Template Excel hanya dapat dibuat dari published schema.')

        fields = self.extract_importable_fields(form_version.schema or {})
        if not fields:
            raise ValueError('Published schema belum memiliki field input yang bisa diexport ke template.')

        generated_at = now_utc().to_iso8601_string()
        data_sheet = [[field['label'] for field in fields], [field['key'] for field in fields]]
        meta_sheet = [
            ['meta_key', 'meta_value'],
            ['form_id', getattr(form, 'id', '')],
            ['form_uuid', getattr(form, 'uuid', '')],
            ['form_code', getattr(form, 'code', '')],
            ['form_name', getattr(form, 'name', '')],
            ['form_version_id', getattr(form_version, 'id', '')],
            ['form_version_uuid', getattr(form_version, 'uuid', '')],
            ['version_number', getattr(form_version, 'version_number', '')],
            ['generated_at', generated_at],
            [],
            ['key', 'label', 'type', 'required', 'path'],
        ]
        for field in fields:
            meta_sheet.append([
                field['key'],
                field['label'],
                field['type'],
                'yes' if field['required'] else 'no',
                field['path'],
            ])

        dictionary_sheet = [['field_key', 'field_label', 'option_label', 'option_value']]
        for field in fields:
            for option in field.get('options') or []:
                dictionary_sheet.append([
                    field['key'],
                    field['label'],
                    option.get('label', ''),
                    option.get('value', ''),
                ])

        sheets = [
            {'name': 'data', 'rows': data_sheet},
            {'name': '_meta', 'rows': meta_sheet},
        ]
        if len(dictionary_sheet) > 1:
            sheets.append({'name': '_dictionary', 'rows': dictionary_sheet})

        return self._create_xlsx(sheets)

    def extract_importable_fields(self, schema):
        fields = []
        components = schema.get('components') if isinstance(schema, dict) else []
        self._collect_components(components or [], fields=fields, parent_path=[])
        return fields

    def parse_mapping_workbook(self, file_storage, form_version, sample_limit=5):
        if not form_version or not getattr(form_version, 'is_published', False) or getattr(form_version, 'status', None) != 'published':
            raise ValueError('Mapping import hanya dapat dilakukan terhadap published schema.')

        filename, content = self._read_upload_content(file_storage)
        rows = self._parse_workbook_content(content, max_rows=sample_limit + 2)
        headers, data_rows = self._split_headers_and_rows(rows)

        fields = self.extract_importable_fields(form_version.schema or {})
        data_rows, _ = self._drop_template_key_row(fields, headers, data_rows)
        sample_rows = [self._row_to_payload(row, headers) for row in data_rows[:sample_limit]]
        auto_mapping = self.build_auto_mapping(fields, headers)

        return {
            'filename': filename,
            'headers': headers,
            'sample_rows': sample_rows,
            'fields': fields,
            'auto_mapping': auto_mapping,
        }

    def create_import_batch_from_workbook(self, form, form_version, file_storage, mapping_config, actor=None):
        if not form_version or not getattr(form_version, 'is_published', False) or getattr(form_version, 'status', None) != 'published':
            raise ValueError('Import batch hanya dapat dibuat dari published schema.')

        filename, content = self._read_upload_content(file_storage)
        rows = self._parse_workbook_content(content, max_rows=None)
        headers, data_rows = self._split_headers_and_rows(rows)
        fields = self.extract_importable_fields(form_version.schema or {})
        data_rows, dropped_template_key_row = self._drop_template_key_row(fields, headers, data_rows)
        normalized_mapping = self.normalize_mapping_config(mapping_config, fields, headers)

        return self._create_import_batch_records(
            form=form,
            form_version=form_version,
            filename=filename,
            headers=headers,
            data_rows=data_rows,
            mapping_config=normalized_mapping,
            actor=actor,
            start_row_number=3 if dropped_template_key_row else 2,
            meta={
                'form_uuid': getattr(form, 'uuid', None),
                'form_version_uuid': getattr(form_version, 'uuid', None),
                'version_number': getattr(form_version, 'version_number', None),
                'created_from': 'mapping_page',
            },
        )

    def reimport_corrected_error_workbook(self, import_batch_id, file_storage, actor=None):
        previous_batch = ImportBatchRepository().get_by_id(import_batch_id)
        if not previous_batch:
            raise ValueError('Import batch sumber tidak ditemukan.')
        if not previous_batch.form or not previous_batch.form_version:
            raise ValueError('Import batch sumber tidak memiliki relasi form/version yang lengkap.')

        filename, content = self._read_upload_content(file_storage)
        rows = self._parse_workbook_content(content, max_rows=None)
        headers, data_rows = self._split_headers_and_rows(rows)
        fields = self.extract_importable_fields(previous_batch.form_version.schema or {})
        auto_mapping = self.build_auto_mapping(fields, headers)
        normalized_mapping = self.normalize_mapping_config(auto_mapping, fields, headers)

        missing_required_headers = [field['label'] for field in fields if not normalized_mapping.get(field['key'])]
        if missing_required_headers:
            raise ValueError(
                'Header file koreksi tidak sesuai template error. Kolom yang belum terpetakan: '
                + ', '.join(missing_required_headers)
            )

        return self._create_import_batch_records(
            form=previous_batch.form,
            form_version=previous_batch.form_version,
            filename=filename,
            headers=headers,
            data_rows=data_rows,
            mapping_config=normalized_mapping,
            actor=actor,
            start_row_number=2,
            meta={
                'form_uuid': getattr(previous_batch.form, 'uuid', None),
                'form_version_uuid': getattr(previous_batch.form_version, 'uuid', None),
                'version_number': getattr(previous_batch.form_version, 'version_number', None),
                'created_from': 'error_reimport',
                'reimport_of_batch_id': previous_batch.id,
                'reimport_of_batch_uuid': getattr(previous_batch, 'uuid', None),
                'source_error_filename': getattr(previous_batch, 'original_filename', None),
            },
        )

    def _create_import_batch_records(self, form, form_version, filename, headers, data_rows, mapping_config, actor=None, start_row_number=2, meta=None):
        import_batch = ImportBatch(
            uuid=str(uuid.uuid4()),
            form_id=form.id,
            form_version_id=form_version.id,
            status=ImportBatch.STATUS_MAPPED,
            original_filename=filename,
            total_rows=len(data_rows),
            mapped_rows=0,
            valid_rows=0,
            error_rows=0,
            duplicate_rows=0,
            mapping_config=mapping_config,
            source_headers=headers,
            meta=meta or {},
        )
        self._apply_actor_audit(import_batch, actor, action='create')

        try:
            db.session.add(import_batch)
            db.session.flush()

            mapped_count = 0
            for offset, row in enumerate(data_rows, start=0):
                raw_payload = self._row_to_payload(row, headers)
                mapped_payload = self.map_raw_payload(raw_payload, mapping_config)
                if any(value not in [None, ''] for value in mapped_payload.values()):
                    mapped_count += 1
                import_row = ImportBatchRow(
                    uuid=str(uuid.uuid4()),
                    import_batch_id=import_batch.id,
                    row_number=start_row_number + offset,
                    raw_payload=raw_payload,
                    mapped_payload=mapped_payload,
                    validation_errors=None,
                    status=ImportBatchRow.STATUS_MAPPED,
                    row_hash=self._hash_payload(mapped_payload),
                )
                db.session.add(import_row)

            import_batch.mapped_rows = mapped_count
            db.session.commit()
            return import_batch
        except Exception:
            db.session.rollback()
            raise

    def normalize_mapping_config(self, mapping_config, fields, headers):
        mapping_config = mapping_config or {}
        header_set = set(headers or [])
        normalized = {}
        for field in fields:
            field_key = field.get('key')
            header = mapping_config.get(field_key) or ''
            normalized[field_key] = header if header in header_set else ''
        return normalized

    def map_raw_payload(self, raw_payload, mapping_config):
        mapped = {}
        for field_key, header in (mapping_config or {}).items():
            mapped[field_key] = raw_payload.get(header, '') if header else ''
        return mapped

    def process_import_batch(self, import_batch_id, actor=None):
        batch = ImportBatchRepository().get_by_id(import_batch_id)
        if not batch:
            raise ValueError('Import batch tidak ditemukan.')
        if batch.status not in [ImportBatch.STATUS_MAPPED, ImportBatch.STATUS_COMPLETED_WITH_ERRORS, ImportBatch.STATUS_FAILED]:
            raise ValueError('Import batch tidak berada pada status yang bisa diproses.')

        rows = sorted([row for row in batch.rows if row.deleted_at is None], key=lambda row: row.row_number)
        fields = self.extract_importable_fields(batch.form_version.schema or {})
        submission_service = SubmissionService()
        valid_count = 0
        error_count = 0
        imported_count = 0
        duplicate_count = 0
        seen_hashes = set(self._load_existing_imported_hashes(batch.form_id, batch.form_version_id, exclude_batch_id=batch.id))

        try:
            batch.status = ImportBatch.STATUS_VALIDATING
            self._apply_actor_audit(batch, actor, action='update')
            db.session.flush()

            for row in rows:
                if row.status == ImportBatchRow.STATUS_IMPORTED:
                    imported_count += 1
                    valid_count += 1
                    if row.row_hash:
                        seen_hashes.add(row.row_hash)
                    continue

                validation_result = self.validate_mapped_payload(row.mapped_payload or {}, fields)
                if not validation_result['is_valid']:
                    row.status = ImportBatchRow.STATUS_ERROR
                    row.validation_errors = validation_result['errors']
                    row.submission_id = None
                    error_count += 1
                    continue

                if row.row_hash and row.row_hash in seen_hashes:
                    row.status = ImportBatchRow.STATUS_DUPLICATE
                    row.submission_id = None
                    row.validation_errors = [{
                        'field': None,
                        'label': 'Row Import',
                        'code': 'duplicate',
                        'message': 'Row ini terdeteksi duplikat dengan data import yang sudah pernah berhasil diproses.',
                    }]
                    duplicate_count += 1
                    continue

                submission = submission_service.submit(
                    batch.form_id,
                    row.mapped_payload or {},
                    actor=actor,
                    context={
                        'source_type': 'excel_import',
                        'source_ref': batch.uuid,
                        'meta': {
                            'import_batch_uuid': batch.uuid,
                            'import_batch_id': batch.id,
                            'import_batch_row_uuid': row.uuid,
                            'import_batch_row_id': row.id,
                            'row_number': row.row_number,
                            'row_hash': row.row_hash,
                            'original_filename': batch.original_filename,
                        },
                    },
                )
                row.status = ImportBatchRow.STATUS_IMPORTED
                row.submission_id = submission.id
                row.validation_errors = None
                valid_count += 1
                imported_count += 1
                if row.row_hash:
                    seen_hashes.add(row.row_hash)

            batch.valid_rows = valid_count
            batch.error_rows = error_count
            batch.duplicate_rows = duplicate_count
            batch.status = ImportBatch.STATUS_COMPLETED_WITH_ERRORS if (error_count or duplicate_count) else ImportBatch.STATUS_COMPLETED
            self._apply_actor_audit(batch, actor, action='update')
            db.session.commit()

            return {
                'batch': batch,
                'total_rows': batch.total_rows,
                'valid_rows': valid_count,
                'error_rows': error_count,
                'duplicate_rows': duplicate_count,
                'imported_rows': imported_count,
                'status': batch.status,
            }
        except Exception:
            db.session.rollback()
            raise

    def validate_mapped_payload(self, payload, fields):
        errors = []
        payload = payload or {}
        field_map = {field['key']: field for field in fields}

        for field in fields:
            key = field.get('key')
            value = payload.get(key)
            if field.get('required') and self._is_empty_value(value):
                errors.append({
                    'field': key,
                    'label': field.get('label') or key,
                    'code': 'required',
                    'message': f"{field.get('label') or key} wajib diisi.",
                })
                continue

            if self._is_empty_value(value):
                continue

            field_type = field.get('type')
            if field_type in ['number', 'currency'] and not self._is_number(value):
                errors.append({
                    'field': key,
                    'label': field.get('label') or key,
                    'code': 'invalid_number',
                    'message': f"{field.get('label') or key} harus berupa angka.",
                })
            if field_type == 'email' and not self._is_valid_email(value):
                errors.append({
                    'field': key,
                    'label': field.get('label') or key,
                    'code': 'invalid_email',
                    'message': f"{field.get('label') or key} harus berupa email valid.",
                })
            if field_type in ['select', 'radio']:
                allowed_values = [str(option.get('value')) for option in field.get('options') or [] if option.get('value') not in [None, '']]
                if allowed_values and str(value) not in allowed_values:
                    errors.append({
                        'field': key,
                        'label': field.get('label') or key,
                        'code': 'invalid_option',
                        'message': f"{field.get('label') or key} tidak sesuai pilihan yang tersedia.",
                        'allowed_values': allowed_values,
                    })

        unknown_keys = [key for key in payload.keys() if key not in field_map]
        return {
            'is_valid': len(errors) == 0,
            'errors': errors,
            'unknown_keys': unknown_keys,
            'validated_at': now_utc().isoformat(),
        }

    def get_import_batch_summary(self, import_batch_id, row_limit=20):
        batch = ImportBatchRepository().get_by_id(import_batch_id)
        if not batch:
            return None
        sorted_rows = sorted([row for row in batch.rows if row.deleted_at is None], key=lambda row: row.row_number)
        error_rows = [row for row in sorted_rows if row.status == ImportBatchRow.STATUS_ERROR]
        return {
            'batch': batch,
            'rows': sorted_rows[:row_limit],
            'error_rows': error_rows[:row_limit],
            'error_rows_count': len(error_rows),
            'error_filename': self.build_error_workbook_filename(batch),
        }

    def export_import_batch_errors(self, import_batch_id):
        batch = ImportBatchRepository().get_by_id(import_batch_id)
        if not batch:
            raise ValueError('Import batch tidak ditemukan.')

        error_rows = sorted(
            [row for row in batch.rows if row.deleted_at is None and row.status == ImportBatchRow.STATUS_ERROR],
            key=lambda row: row.row_number,
        )
        if not error_rows:
            raise ValueError('Import batch belum memiliki row error untuk diexport.')

        return {
            'batch': batch,
            'filename': self.build_error_workbook_filename(batch),
            'content': self.build_error_workbook(batch, error_rows),
            'error_rows_count': len(error_rows),
        }

    def build_error_workbook_filename(self, batch):
        form_code = getattr(getattr(batch, 'form', None), 'code', None) or f'form-{getattr(batch, "form_id", "unknown")}'
        version_number = getattr(getattr(batch, 'form_version', None), 'version_number', None) or getattr(batch, 'form_version_id', 'unknown')
        return f'{form_code}-v{version_number}-errors.xlsx'

    def build_error_workbook(self, batch, error_rows):
        generated_at = now_utc().to_iso8601_string()
        fields = self.extract_importable_fields((getattr(getattr(batch, 'form_version', None), 'schema', None) or {}))

        if fields:
            data_sheet = [
                [field['label'] for field in fields],
            ]
            for row in error_rows:
                data_sheet.append(self._build_error_data_row(fields, row))
        else:
            data_sheet = [[
                'row_number',
                'status',
                'error_messages',
                'error_codes',
                'raw_payload',
                'mapped_payload',
            ]]
            for row in error_rows:
                errors = row.validation_errors or []
                data_sheet.append([
                    str(getattr(row, 'row_number', '')),
                    str(getattr(row, 'status', '')),
                    ' | '.join(error.get('message', '') for error in errors),
                    ' | '.join(error.get('code', '') for error in errors),
                    json.dumps(getattr(row, 'raw_payload', {}) or {}, ensure_ascii=False, sort_keys=True),
                    json.dumps(getattr(row, 'mapped_payload', {}) or {}, ensure_ascii=False, sort_keys=True),
                ])

        detail_sheet = [[
            'row_number',
            'status',
            'field',
            'label',
            'error_code',
            'error_message',
            'current_value',
        ]]
        for row in error_rows:
            for error in (row.validation_errors or []):
                field_key = error.get('field', '')
                detail_sheet.append([
                    str(getattr(row, 'row_number', '')),
                    str(getattr(row, 'status', '')),
                    field_key,
                    error.get('label', field_key),
                    error.get('code', ''),
                    error.get('message', ''),
                    str((getattr(row, 'mapped_payload', {}) or {}).get(field_key, '')),
                ])

        meta_sheet = [
            ['meta_key', 'meta_value'],
            ['batch_uuid', getattr(batch, 'uuid', '')],
            ['original_filename', getattr(batch, 'original_filename', '')],
            ['form_code', getattr(getattr(batch, 'form', None), 'code', '')],
            ['form_name', getattr(getattr(batch, 'form', None), 'name', '')],
            ['form_version', getattr(getattr(batch, 'form_version', None), 'version_number', '')],
            ['generated_at', generated_at],
            ['error_rows_count', len(error_rows)],
            [],
            ['catatan', 'Edit sheet data lalu upload ulang file ini melalui halaman import mapping.'],
            ['catatan', 'Jika sebuah sel mengandung teks [ERROR], hapus pesan tersebut dan ganti dengan nilai final yang benar.'],
        ]

        dictionary_sheet = [['field_key', 'field_label', 'option_label', 'option_value']]
        for field in fields:
            for option in field.get('options') or []:
                dictionary_sheet.append([
                    field['key'],
                    field['label'],
                    option.get('label', ''),
                    option.get('value', ''),
                ])

        sheets = [
            {'name': 'data', 'rows': data_sheet},
            {'name': '_errors', 'rows': detail_sheet},
            {'name': '_meta', 'rows': meta_sheet},
        ]
        if len(dictionary_sheet) > 1:
            sheets.append({'name': '_dictionary', 'rows': dictionary_sheet})

        return self._create_xlsx(sheets)

    def _build_error_data_row(self, fields, row):
        mapped_payload = getattr(row, 'mapped_payload', {}) or {}
        errors_by_field = defaultdict(list)
        for error in getattr(row, 'validation_errors', None) or []:
            errors_by_field[error.get('field')].append(error)

        rendered = []
        for field in fields:
            field_key = field.get('key')
            base_value = mapped_payload.get(field_key, '')
            field_errors = errors_by_field.get(field_key, [])
            rendered.append(self._render_error_cell_value(base_value, field_errors))
        return rendered

    def _render_error_cell_value(self, value, field_errors):
        base_text = '' if value is None else str(value)
        if not field_errors:
            return base_text
        error_text = ' | '.join(error.get('message', '') for error in field_errors if error.get('message'))
        if base_text.strip():
            return f'{base_text} [ERROR: {error_text}]'
        return f'[ERROR: {error_text}]'

    def _read_upload_content(self, file_storage):
        filename = getattr(file_storage, 'filename', '') or ''
        if not filename.lower().endswith('.xlsx'):
            raise ValueError('Saat ini file import yang didukung adalah Excel .xlsx.')

        content = file_storage.read()
        if not content:
            raise ValueError('File Excel kosong atau tidak dapat dibaca.')
        return filename, content

    def _parse_workbook_content(self, content, max_rows=None):
        rows = self._read_first_sheet_rows(content, max_rows=max_rows)
        if not rows:
            raise ValueError('Sheet pertama tidak memiliki data.')
        return rows

    def _split_headers_and_rows(self, rows):
        headers = [str(value).strip() for value in rows[0] if str(value).strip()]
        if not headers:
            raise ValueError('Header kolom Excel tidak ditemukan di baris pertama.')
        return headers, rows[1:]

    def _row_to_payload(self, row, headers):
        return {
            header: row[index] if index < len(row) else ''
            for index, header in enumerate(headers)
        }

    def _drop_template_key_row(self, fields, headers, data_rows):
        if not data_rows:
            return data_rows, False
        expected_keys = [field.get('key') for field in fields]
        first_payload = self._row_to_payload(data_rows[0], headers)
        first_values = [str(first_payload.get(header, '')).strip() for header in headers]
        expected_prefix = [str(key or '').strip() for key in expected_keys[:len(first_values)]]
        if first_values and first_values == expected_prefix:
            return data_rows[1:], True
        return data_rows, False

    def _load_existing_imported_hashes(self, form_id, form_version_id, exclude_batch_id=None):
        query = (
            db.session.query(ImportBatchRow.row_hash)
            .join(ImportBatch, ImportBatch.id == ImportBatchRow.import_batch_id)
            .filter(
                ImportBatch.deleted_at.is_(None),
                ImportBatchRow.deleted_at.is_(None),
                ImportBatchRow.status == ImportBatchRow.STATUS_IMPORTED,
                ImportBatch.form_id == form_id,
                ImportBatch.form_version_id == form_version_id,
                ImportBatchRow.row_hash.isnot(None),
                ImportBatchRow.row_hash != '',
            )
        )
        if exclude_batch_id is not None:
            query = query.filter(ImportBatch.id != exclude_batch_id)
        return {
            row_hash
            for (row_hash,) in query.all()
            if row_hash
        }

    def _hash_payload(self, payload):
        canonical = json.dumps(payload or {}, sort_keys=True, ensure_ascii=False, default=str)
        return hashlib.sha256(canonical.encode('utf-8')).hexdigest()

    def _is_empty_value(self, value):
        if value is None:
            return True
        if isinstance(value, str) and not value.strip():
            return True
        if isinstance(value, (list, dict)) and not value:
            return True
        return False

    def _is_number(self, value):
        try:
            float(str(value).replace(',', '.'))
            return True
        except (TypeError, ValueError):
            return False

    def _is_valid_email(self, value):
        return re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', str(value or '').strip()) is not None

    def _apply_actor_audit(self, obj, actor=None, action='create'):
        if not actor:
            return obj
        actor_id = getattr(actor, 'id', None)
        actor_uuid = getattr(actor, 'uuid', None)
        if action == 'create':
            obj.created_by = actor_id
            obj.created_by_uuid = actor_uuid
        obj.updated_by = actor_id
        obj.updated_by_uuid = actor_uuid
        return obj

    def build_auto_mapping(self, fields, headers):
        normalized_headers = {self._normalize_label(header): header for header in headers}
        mapping = {}
        for field in fields:
            candidates = [field.get('key'), field.get('label')]
            selected = ''
            for candidate in candidates:
                normalized = self._normalize_label(candidate)
                if normalized in normalized_headers:
                    selected = normalized_headers[normalized]
                    break
            mapping[field['key']] = selected
        return mapping

    def _collect_components(self, components, fields, parent_path):
        if not isinstance(components, list):
            return

        for component in components:
            if not isinstance(component, dict):
                continue

            component_type = component.get('type')
            key = component.get('key')
            label = component.get('label') or key or component_type or 'field'
            current_path = parent_path + ([key] if key else [])

            if component_type in IMPORTABLE_COMPONENT_TYPES and key:
                fields.append({
                    'key': key,
                    'label': label,
                    'type': component_type,
                    'required': bool((component.get('validate') or {}).get('required')),
                    'path': '.'.join(current_path) if current_path else key,
                    'options': self._extract_component_options(component),
                })

            # Form.io layout/container variants keep children in slightly different shapes.
            self._collect_components(component.get('components') or [], fields, current_path)

            for column in component.get('columns') or []:
                self._collect_components((column or {}).get('components') or [], fields, current_path)

            for row in component.get('rows') or []:
                for cell in row or []:
                    self._collect_components((cell or {}).get('components') or [], fields, current_path)

    def _extract_component_options(self, component):
        component_type = component.get('type')
        options = []

        values = ((component.get('data') or {}).get('values') or [])
        for item in values:
            if isinstance(item, dict):
                options.append({
                    'label': item.get('label', item.get('value', '')),
                    'value': item.get('value', item.get('label', '')),
                })

        if component_type == 'radio':
            for item in component.get('values') or []:
                if isinstance(item, dict):
                    options.append({
                        'label': item.get('label', item.get('value', '')),
                        'value': item.get('value', item.get('label', '')),
                    })

        if component_type == 'selectboxes':
            for item in component.get('values') or []:
                if isinstance(item, dict):
                    options.append({
                        'label': item.get('label', item.get('value', '')),
                        'value': item.get('value', item.get('label', '')),
                    })

        return options

    def _normalize_label(self, value):
        return re.sub(r'[^a-z0-9]+', '', str(value or '').strip().lower())

    def _create_xlsx(self, sheets):
        workbook = Workbook()
        default_sheet = workbook.active
        workbook.remove(default_sheet)

        for index, sheet in enumerate(sheets):
            worksheet = workbook.create_sheet(title=sheet['name'], index=index)
            for row in sheet.get('rows', []):
                worksheet.append(list(row))

        buffer = BytesIO()
        workbook.save(buffer)
        buffer.seek(0)
        return buffer.getvalue()

    def _read_first_sheet_rows(self, content, max_rows=6):
        workbook = load_workbook(filename=BytesIO(content), read_only=True, data_only=True)
        worksheet = workbook[workbook.sheetnames[0]]
        rows = []

        for row in worksheet.iter_rows(values_only=True):
            values = list(row or [])
            while values and values[-1] is None:
                values.pop()
            rows.append(['' if value is None else str(value) for value in values])
            if max_rows is not None and len(rows) >= max_rows:
                break

        workbook.close()
        return rows

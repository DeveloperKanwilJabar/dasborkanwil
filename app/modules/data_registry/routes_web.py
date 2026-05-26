from io import BytesIO

from flask import Blueprint, Response, current_app, flash, redirect, render_template, request, send_file, url_for
from flask_login import current_user, login_required
from flask_wtf.csrf import generate_csrf

from app.modules.data_registry.services import (
    DataRegistryImportBatchService,
    DataRegistryImportValidationService,
    DataRegistryMaterializationService,
    DataRegistryService,
    DataRegistryVersionService,
)


data_registry_web_bp = Blueprint(
    'data_registry_web',
    __name__,
)


PREVIEW_ROW_LIMIT = 20
FIELD_DESIGNER_EXTRA_ROWS = 3


REGISTRY_STARTER_PRESETS = {
    'master_data_hierarkis': {
        'label': 'Master Data Hierarkis',
        'description': 'Starter paling ringan untuk bank data/master data bertingkat yang siap diuji via browser.',
        'registry_type': 'master_data',
        'category_key': 'master_data',
        'source_mode': 'import_file',
        'data_shape': 'hierarchical',
        'schema_json': {
            'fields': [
                {'key': 'record_key', 'type': 'text', 'required': True, 'label': 'Record Key'},
                {'key': 'record_code', 'type': 'text', 'required': True, 'label': 'Record Code'},
                {'key': 'label', 'type': 'text', 'required': True, 'label': 'Label'},
                {'key': 'parent_code', 'type': 'text', 'required': False, 'label': 'Parent Code'},
                {'key': 'admin_level', 'type': 'text', 'required': False, 'label': 'Admin Level'},
            ],
        },
        'mapping_spec': {
            'materialization_contract': 'generic_v1',
        },
        'schema_meta': {
            'browser_test_ready': True,
            'hierarchy_mode': 'adjacency_list',
        },
    },
    'wilayah_administratif': {
        'label': 'Wilayah Administratif',
        'description': 'Starter untuk registry wilayah administratif dengan struktur geo-hierarkis.',
        'registry_type': 'geo',
        'category_key': 'wilayah',
        'source_mode': 'import_file',
        'data_shape': 'hierarchical_geo',
        'schema_json': {
            'fields': [
                {'key': 'record_key', 'type': 'text', 'required': True, 'label': 'Record Key'},
                {'key': 'record_code', 'type': 'text', 'required': True, 'label': 'Record Code'},
                {'key': 'label', 'type': 'text', 'required': True, 'label': 'Label'},
                {'key': 'parent_code', 'type': 'text', 'required': False, 'label': 'Parent Code'},
                {'key': 'admin_level', 'type': 'text', 'required': False, 'label': 'Admin Level'},
                {'key': 'latitude', 'type': 'text', 'required': False, 'label': 'Latitude'},
                {'key': 'longitude', 'type': 'text', 'required': False, 'label': 'Longitude'},
            ],
        },
        'mapping_spec': {
            'materialization_contract': 'generic_v1',
        },
        'schema_meta': {
            'browser_test_ready': True,
            'geo_mode': 'point_or_polygon_ready',
        },
    },
}


def _current_actor():
    if current_user and not getattr(current_user, 'is_anonymous', True):
        return current_user
    return None


def _build_registry_browser_items(registries, version_service):
    items = []
    for registry in registries:
        draft_version = version_service.repository.get_draft_version(registry.id)
        published_version = version_service.repository.get_published_version(registry.id)
        items.append({
            'registry': registry,
            'draft_version': draft_version,
            'published_version': published_version,
        })
    return items


def _build_registry_create_payload(form_data):
    template_key = form_data.get('template_key') or 'master_data_hierarkis'
    preset = REGISTRY_STARTER_PRESETS.get(template_key) or REGISTRY_STARTER_PRESETS['master_data_hierarkis']
    schema_meta = dict(preset.get('schema_meta') or {})
    schema_meta['starter_template'] = template_key

    return {
        'name': (form_data.get('name') or '').strip(),
        'registry_slug': (form_data.get('registry_slug') or '').strip(),
        'registry_code': (form_data.get('registry_code') or '').strip() or None,
        'description': (form_data.get('description') or '').strip() or None,
        'registry_type': preset['registry_type'],
        'category_key': preset['category_key'],
        'source_mode': preset['source_mode'],
        'data_shape': preset['data_shape'],
        'is_year_scoped': bool(form_data.get('is_year_scoped')),
        'status': 'draft',
        'schema_json': preset['schema_json'],
        'mapping_spec': preset['mapping_spec'],
        'schema_meta': schema_meta,
        'source_snapshot': {
            'source_name': 'browser_manual_setup',
            'template_key': template_key,
        },
    }


def _build_field_designer_rows(fields, extra_rows=FIELD_DESIGNER_EXTRA_ROWS):
    rows = []
    for field in fields or []:
        options = field.get('options') or field.get('allowed_values') or []
        rows.append({
            'key': field.get('key', ''),
            'label': field.get('label', ''),
            'type': field.get('type', 'text') or 'text',
            'required': bool(field.get('required', False)),
            'options_text': '\n'.join(str(option) for option in options if option not in (None, '')),
        })

    for _ in range(extra_rows):
        rows.append({'key': '', 'label': '', 'type': 'text', 'required': False, 'options_text': ''})
    return rows


def _build_field_schema_payload(form_data):
    keys = form_data.getlist('field_key[]')
    labels = form_data.getlist('field_label[]')
    types = form_data.getlist('field_type[]')
    options_payload = form_data.getlist('field_options[]')
    required_flags = set(form_data.getlist('field_required[]'))

    fields = []
    for index, raw_key in enumerate(keys):
        field_key = (raw_key or '').strip()
        if not field_key:
            continue

        field_label = (labels[index] if index < len(labels) else '') or field_key
        field_type = (types[index] if index < len(types) else 'text') or 'text'
        raw_options = options_payload[index] if index < len(options_payload) else ''
        normalized_options = [
            option.strip()
            for option in str(raw_options).splitlines()
            if option.strip()
        ]
        field_payload = {
            'key': field_key,
            'label': field_label.strip() or field_key,
            'type': field_type.strip() or 'text',
            'required': str(index) in required_flags,
        }
        if field_payload['type'] == 'select' and normalized_options:
            field_payload['options'] = normalized_options
        fields.append(field_payload)

    return fields


@data_registry_web_bp.route('/data-registries')
@login_required
def registry_index():
    error_message = None
    registry_items = []

    try:
        registry_service = DataRegistryService()
        version_service = DataRegistryVersionService()
        registries = registry_service.repository.get_all()
        registry_items = _build_registry_browser_items(registries, version_service)
    except Exception as error:
        current_app.logger.error(f'Data registry index error: {str(error)}')
        error_message = 'Gagal memuat daftar data registry.'

    return render_template(
        'pages/data_registry/registry_index.html',
        registry_items=registry_items,
        error_message=error_message,
    )


@data_registry_web_bp.route('/data-registries/create', methods=['GET', 'POST'])
@login_required
def create_registry():
    form_values = {
        'name': '',
        'registry_slug': '',
        'registry_code': '',
        'description': '',
        'template_key': 'master_data_hierarkis',
        'is_year_scoped': False,
    }

    if request.method == 'POST':
        form_values = {
            'name': request.form.get('name', ''),
            'registry_slug': request.form.get('registry_slug', ''),
            'registry_code': request.form.get('registry_code', ''),
            'description': request.form.get('description', ''),
            'template_key': request.form.get('template_key', 'master_data_hierarkis'),
            'is_year_scoped': bool(request.form.get('is_year_scoped')),
        }
        try:
            payload = _build_registry_create_payload(request.form)
            result = DataRegistryService().create_registry(payload, actor=_current_actor())
            draft_version = result.get('draft_version')
            flash('Data registry draft berhasil dibuat. Lanjutkan uji browser lewat import console.', 'success')
            if draft_version:
                return redirect(url_for('data_registry_web.import_console', version_id=draft_version.id))
            return redirect(url_for('data_registry_web.registry_index'))
        except ValueError as error:
            flash(str(error), 'error')
            current_app.logger.warning(f'Data registry create validation error: {str(error)}')
        except Exception as error:
            flash('Gagal membuat data registry.', 'error')
            current_app.logger.error(f'Data registry create exception: {str(error)}')

    return render_template(
        'pages/data_registry/registry_create.html',
        starter_presets=REGISTRY_STARTER_PRESETS,
        form_values=form_values,
        csrf_token=generate_csrf,
    )


@data_registry_web_bp.route('/data-registries/versions/<int:version_id>/import-mapping', methods=['GET', 'POST'])
@login_required
def import_mapping(version_id):
    detail = None
    version = None
    mapping_result = None
    error_message = None
    batch_service = DataRegistryImportBatchService()

    try:
        detail = DataRegistryVersionService().get_version_detail(version_id)
        version = detail.get('version') if detail else None
        if request.method == 'POST':
            upload = request.files.get('excel_file')
            action = request.form.get('action', 'preview_mapping')
            if not upload:
                raise ValueError('File Excel wajib dipilih.')
            if action == 'create_batch':
                mapping_config = {
                    key.replace('mapping_', '', 1): value
                    for key, value in request.form.items()
                    if key.startswith('mapping_')
                }
                result = batch_service.create_batch_from_workbook(
                    version_id,
                    upload,
                    mapping_config,
                    actor=_current_actor(),
                )
                return redirect(url_for('data_registry_web.import_batch_console', batch_id=result['batch'].id))
            mapping_result = batch_service.parse_mapping_workbook(version_id, upload)
    except ValueError as error:
        error_message = str(error)
    except Exception as error:
        current_app.logger.error(f'Data registry import mapping error: {str(error)}')
        error_message = 'Gagal membaca file Excel untuk shell mapping registry.'

    return render_template(
        'pages/data_registry/import_mapping.html',
        detail=detail,
        version=version,
        batches=detail.get('batches') if detail else [],
        fields=(mapping_result.get('fields') if mapping_result else None) or (batch_service.extract_importable_fields(version) if version and hasattr(batch_service, 'extract_importable_fields') else []),
        mapping_result=mapping_result,
        error_message=error_message,
        csrf_token=generate_csrf,
    )


@data_registry_web_bp.route('/data-registries/versions/<int:version_id>/import-console')
@login_required
def import_console(version_id):
    detail = None
    error_message = None
    manual_entry_fields = []
    field_designer_rows = []

    try:
        detail = DataRegistryVersionService().get_version_detail(version_id)
        version = detail.get('version') if detail else None
        manual_entry_fields = DataRegistryImportBatchService().extract_importable_fields(version) if version else []
        field_designer_rows = _build_field_designer_rows(manual_entry_fields)
    except ValueError as error:
        error_message = str(error)
    except Exception as error:
        current_app.logger.error(f'Data registry import console error: {str(error)}')
        error_message = 'Gagal memuat import console registry.'

    return render_template(
        'pages/data_registry/import_console.html',
        detail=detail,
        version=detail.get('version') if detail else None,
        batches=detail.get('batches') if detail else [],
        manual_entry_fields=manual_entry_fields,
        field_designer_rows=field_designer_rows,
        error_message=error_message,
        csrf_token=generate_csrf,
    )


@data_registry_web_bp.route('/data-registries/versions/<int:version_id>/field-designer', methods=['POST'])
@login_required
def update_registry_field_designer(version_id):
    try:
        fields = _build_field_schema_payload(request.form)
        DataRegistryVersionService().update_draft_schema_fields(version_id, fields, actor=_current_actor())
        flash('Field schema registry draft berhasil diperbarui.', 'success')
    except ValueError as error:
        flash(str(error), 'error')
        current_app.logger.warning(f'Data registry field designer error: {str(error)}')
    except Exception as error:
        flash('Gagal memperbarui field schema registry.', 'error')
        current_app.logger.error(f'Data registry field designer exception: {str(error)}')

    return redirect(url_for('data_registry_web.import_console', version_id=version_id))


@data_registry_web_bp.route('/data-registries/versions/<int:version_id>/template.xlsx')
@login_required
def download_registry_template(version_id):
    try:
        detail = DataRegistryVersionService().get_version_detail(version_id)
        version = detail.get('version') if detail else None
        registry = getattr(version, 'registry', None)
        batch_service = DataRegistryImportBatchService()
        workbook = batch_service.build_template_workbook(version, registry=registry)
        return send_file(
            BytesIO(workbook),
            as_attachment=True,
            download_name=batch_service.build_template_filename(version, registry=registry),
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
    except ValueError as error:
        return Response(str(error), status=400)
    except Exception as error:
        current_app.logger.error(f'Data registry export template error: {str(error)}')
        return Response('Gagal mengunduh template registry.', status=500)


@data_registry_web_bp.route('/data-registries/versions/<int:version_id>/manual-entry', methods=['POST'])
@login_required
def create_manual_entry_batch(version_id):
    try:
        detail = DataRegistryVersionService().get_version_detail(version_id)
        version = detail.get('version') if detail else None
        fields = DataRegistryImportBatchService().extract_importable_fields(version) if version else []
        row_payload = {
            field.get('key'): request.form.get(field.get('key'), '')
            for field in fields
            if field.get('key')
        }
        result = DataRegistryImportBatchService().create_manual_entry_batch(
            version_id,
            row_payload,
            actor=_current_actor(),
        )
        flash('Entry manual berhasil dibuat sebagai batch staging.', 'success')
        return redirect(url_for('data_registry_web.import_batch_console', batch_id=result['batch'].id))
    except ValueError as error:
        flash(str(error), 'error')
        current_app.logger.warning(f'Data registry manual entry error: {str(error)}')
    except Exception as error:
        flash('Gagal membuat entry manual registry.', 'error')
        current_app.logger.error(f'Data registry manual entry exception: {str(error)}')

    return redirect(url_for('data_registry_web.import_console', version_id=version_id))


@data_registry_web_bp.route('/data-registries/import-batches/<int:batch_id>/import-console')
@login_required
def import_batch_console(batch_id):
    detail = None
    row_summary = None
    error_message = None
    row_status_filter = request.args.get('status') or None

    try:
        service = DataRegistryImportBatchService()
        detail = service.get_batch_detail(batch_id)
        row_summary = service.list_batch_rows(batch_id, status=row_status_filter)
    except ValueError as error:
        error_message = str(error)
    except Exception as error:
        current_app.logger.error(f'Data registry import batch console error: {str(error)}')
        error_message = 'Gagal memuat console batch import registry.'

    batch = detail.get('batch') if detail else None
    version = detail.get('version') if detail else None
    rows = (row_summary or {}).get('rows') or []

    return render_template(
        'pages/data_registry/import_batch_console.html',
        batch=batch,
        version=version,
        rows=rows[:PREVIEW_ROW_LIMIT],
        preview_row_limit=PREVIEW_ROW_LIMIT,
        row_status_filter=row_status_filter,
        error_message=error_message,
        csrf_token=generate_csrf,
    )


@data_registry_web_bp.route('/data-registries/import-batches/<int:batch_id>/errors.xlsx')
@login_required
def download_import_batch_errors(batch_id):
    try:
        result = DataRegistryImportBatchService().export_import_batch_errors(batch_id)
        return send_file(
            BytesIO(result['content']),
            as_attachment=True,
            download_name=result['filename'],
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
    except ValueError as error:
        return Response(str(error), status=400)
    except Exception as error:
        current_app.logger.error(f'Data registry export import batch errors error: {str(error)}')
        return Response('Gagal mengunduh workbook error import batch.', status=500)


@data_registry_web_bp.route('/data-registries/import-batches/<int:batch_id>/validate', methods=['POST'])
@login_required
def validate_import_batch(batch_id):
    try:
        DataRegistryImportValidationService().validate_batch(batch_id, actor=_current_actor())
        flash('Import batch berhasil divalidasi.', 'success')
    except ValueError as error:
        flash(str(error), 'error')
        current_app.logger.warning(f'Data registry import batch validate error: {str(error)}')
    except Exception as error:
        flash('Gagal memvalidasi import batch.', 'error')
        current_app.logger.error(f'Data registry import batch validate exception: {str(error)}')

    return redirect(url_for('data_registry_web.import_batch_console', batch_id=batch_id))


@data_registry_web_bp.route('/data-registries/import-batches/<int:batch_id>/materialize', methods=['POST'])
@login_required
def materialize_import_batch(batch_id):
    try:
        DataRegistryMaterializationService().materialize_import_batch(batch_id, actor=_current_actor())
        flash('Import batch berhasil dimaterialisasi.', 'success')
    except ValueError as error:
        flash(str(error), 'error')
        current_app.logger.warning(f'Data registry import batch materialize error: {str(error)}')
    except Exception as error:
        flash('Gagal mematerialisasi import batch.', 'error')
        current_app.logger.error(f'Data registry import batch materialize exception: {str(error)}')

    return redirect(url_for('data_registry_web.import_batch_console', batch_id=batch_id))

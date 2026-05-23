from io import BytesIO

from flask import Blueprint, Response, current_app, flash, redirect, render_template, request, send_file, url_for
from flask_login import current_user, login_required

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
    )


@data_registry_web_bp.route('/data-registries/versions/<int:version_id>/import-console')
@login_required
def import_console(version_id):
    detail = None
    error_message = None

    try:
        detail = DataRegistryVersionService().get_version_detail(version_id)
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
        error_message=error_message,
    )


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

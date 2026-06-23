from io import BytesIO

from flask import Blueprint, Response, current_app, flash, jsonify, redirect, render_template, request, send_file, url_for
from flask_login import current_user, login_required
from flask_wtf.csrf import generate_csrf
from jinja2.utils import htmlsafe_json_dumps
from werkzeug.utils import secure_filename

from app.core.access import (
    ACCESS_POLICY_CATALOG,
    BOOTSTRAP_SCOPE_REGISTRY,
    can_submit_form,
    can_update_form,
    can_view_form,
)
from app.modules.form.import_services import FormDataImportPipelineService
from app.modules.form.registry_consumers import FormRegistryConsumerService
from app.modules.form.services import FormService, FormVersionService


form_web_bp = Blueprint(
    'form',
    __name__,
)


EMPTY_FORMIO_SCHEMA = {
    'display': 'form',
    'components': [],
}


def _resolve_builder_version(form_id, requested_version_id=None):
    version_service = FormVersionService()
    selected_version = None
    selected_source = 'empty'

    if requested_version_id:
        selected_version = version_service.repository.get_by_id(requested_version_id)
        selected_source = 'requested'

    if not selected_version and form_id:
        selected_version = version_service.get_draft_version(form_id)
        selected_source = 'draft'

    if not selected_version and form_id:
        selected_version = version_service.get_published_version(form_id)
        selected_source = 'published'

    return selected_version, selected_source


def _version_summary(form_id):
    version_service = FormVersionService()
    draft_version = version_service.get_draft_version(form_id)
    published_version = version_service.get_published_version(form_id)
    return draft_version, published_version


def _current_actor():
    if current_user and not getattr(current_user, 'is_anonymous', True):
        return current_user
    return None


def _build_form_permissions(form, actor=None):
    if not form:
        return {
            'can_view': False,
            'can_manage': False,
            'can_submit': False,
        }

    actor = actor if actor is not None else _current_actor()
    return {
        'can_view': can_view_form(actor, form),
        'can_manage': can_update_form(actor, form),
        'can_submit': can_submit_form(actor, form),
    }


def _serialize_form_list_item(form):
    permissions = _build_form_permissions(form)
    draft_version, published_version = _version_summary(form.id)
    active_version = draft_version or published_version
    return {
        'id': form.id,
        'uuid': form.uuid,
        'code': form.code,
        'slug': form.slug,
        'name': form.name,
        'description': form.description,
        'status': form.status,
        'visibility': form.visibility,
        'draft_version_number': draft_version.version_number if draft_version else None,
        'draft_version_id': draft_version.id if draft_version else None,
        'published_version_number': published_version.version_number if published_version else None,
        'published_version_id': published_version.id if published_version else None,
        'published_version_uuid': published_version.uuid if published_version else None,
        'active_version_number': active_version.version_number if active_version else None,
        'component_count': len((active_version.schema or {}).get('components', [])) if active_version else 0,
        'created_at': form.created_at.isoformat() if form.created_at else None,
        'updated_at': form.updated_at.isoformat() if form.updated_at else None,
        'permissions': permissions,
    }


@form_web_bp.route('/forms')
@login_required
def index():
    return render_template('pages/forms/form_index.html')


@form_web_bp.route('/forms/data', methods=['GET'])
@login_required
def forms_data():
    try:
        forms = FormService().repository.get_all()
        serialized_forms = []
        for form in forms:
            permissions = _build_form_permissions(form)
            if not permissions['can_view'] and not permissions['can_manage']:
                continue
            serialized_forms.append(_serialize_form_list_item(form))
        return jsonify(serialized_forms)
    except Exception as error:
        current_app.logger.error(f'Error getting forms data: {str(error)}')
        return jsonify([]), 500


@form_web_bp.route('/forms/submissions')
@login_required
def submissions_index():
    """Katalog form yang punya workspace submission seperti CRUD data."""
    error_message = None
    form_options = []
    try:
        all_forms = FormService().repository.get_all()
        for form in all_forms:
            permissions = _build_form_permissions(form)
            if not permissions['can_view'] and not permissions['can_manage']:
                continue
            form_options.append(_serialize_form_list_item(form))
    except Exception as error:
        current_app.logger.error(f'Submissions catalog error: {str(error)}')
        error_message = 'Gagal memuat katalog form submissions.'

    return render_template(
        'pages/forms/submission_index.html',
        form_options=form_options,
        error_message=error_message,
    )


@form_web_bp.route('/forms/submissions/<int:form_id>')
@login_required
def submission_detail(form_id):
    """Halaman data submissions untuk satu form, dengan kolom mengikuti schema."""
    selected_form = None
    published_version = None
    schema = dict(EMPTY_FORMIO_SCHEMA)
    fields = []
    error_message = None
    permissions = _build_form_permissions(None)

    try:
        selected_form = FormService().get_form_detail(form_id)
        permissions = _build_form_permissions(selected_form)
        if not selected_form:
            error_message = 'Form tidak ditemukan.'
        elif not permissions['can_view'] and not permissions['can_manage']:
            error_message = 'Akun Anda tidak memiliki izin membuka submission form ini.'
            selected_form = None
        else:
            published_version = FormVersionService().get_published_version(form_id)
            if published_version and isinstance(published_version.schema, dict):
                schema = published_version.schema
                fields = FormDataImportPipelineService().extract_importable_fields(schema)
    except Exception as error:
        current_app.logger.error(f'Submission detail page error: {str(error)}')
        error_message = 'Gagal memuat data submissions.'

    return render_template(
        'pages/forms/submission_detail.html',
        selected_form=selected_form,
        published_version=published_version,
        schema=schema,
        fields=fields,
        permissions=permissions,
        error_message=error_message,
    )


@form_web_bp.route('/forms/submissions/<int:form_id>/new')
def submission_new(form_id):
    """Halaman tambah submission mandiri, terpisah dari preview form builder."""
    form = None
    published_version = None
    schema = dict(EMPTY_FORMIO_SCHEMA)
    error_message = None

    try:
        form = FormService().get_form_detail(form_id)
        published_version = FormVersionService().get_published_version(form_id)
        if not form:
            error_message = 'Form tidak ditemukan.'
        elif not published_version:
            error_message = 'Form belum memiliki published schema. Publish draft terlebih dahulu.'
        elif isinstance(published_version.schema, dict):
            schema = published_version.schema
    except Exception as error:
        current_app.logger.warning(f'Gagal memuat halaman tambah submission: {str(error)}')
        error_message = 'Gagal memuat form submission.'

    return render_template(
        'pages/forms/submission_new.html',
        form=form,
        form_id=form_id,
        published_version=published_version,
        schema=schema,
        error_message=error_message,
    )


@form_web_bp.route('/forms/builder')
@login_required
def builder():
    """Render Form.io Builder web container.

    Interaksi data tetap diarahkan ke API v1 dari JavaScript halaman. Route web ini
    hanya menyiapkan container Velzon dan konfigurasi awal yang dibutuhkan builder.
    """
    form_id = request.args.get('form_id', type=int)
    requested_version_id = request.args.get('draft_version_id', type=int) or request.args.get('version_id', type=int)
    form = None
    initial_schema = dict(EMPTY_FORMIO_SCHEMA)
    selected_version = None
    selected_source = 'empty'
    builder_mode = 'new'

    try:
        selected_version, selected_source = _resolve_builder_version(form_id, requested_version_id)
        if selected_version:
            form_id = form_id or selected_version.form_id
            if isinstance(selected_version.schema, dict):
                initial_schema = selected_version.schema
            builder_mode = 'edit_draft' if selected_version.status == 'draft' and not selected_version.is_published else 'published_source'

        if form_id:
            form = FormService().get_form_detail(form_id)
    except Exception as error:
        current_app.logger.warning(
            f'Gagal memuat schema untuk Form Builder web container: {str(error)}'
        )

    scope_options = sorted(
        BOOTSTRAP_SCOPE_REGISTRY.values(),
        key=lambda item: (len(item.get('path') or []), item.get('name') or item.get('code') or ''),
    )
    form_access_policies = [
        {
            'key': key,
            **value,
        }
        for key, value in ACCESS_POLICY_CATALOG.items()
        if value.get('resource') == 'form'
    ]
    registry_consumer_presets = FormRegistryConsumerService().list_builder_presets(base_url=request.url_root)
    registry_consumer_presets_json = htmlsafe_json_dumps(
        registry_consumer_presets,
        dumps=current_app.json.dumps,
    )

    return render_template(
        'pages/forms/form_builder.html',
        form=form,
        permissions=_build_form_permissions(form),
        form_id=form_id,
        draft_version_id=selected_version.id if selected_version and selected_version.status == 'draft' else None,
        selected_version=selected_version,
        selected_version_source=selected_source,
        builder_mode=builder_mode,
        initial_schema=initial_schema,
        scope_options=scope_options,
        form_access_policies=form_access_policies,
        registry_consumer_presets_json=registry_consumer_presets_json,
    )


@form_web_bp.route('/forms/<int:form_id>/template.xlsx')
@login_required
def export_template(form_id):
    """Download Excel template berdasarkan published schema aktif."""
    try:
        form = FormService().get_form_detail(form_id)
        if not form:
            return Response('Form tidak ditemukan.', status=404)

        permissions = _build_form_permissions(form)
        if not permissions['can_view'] and not permissions['can_manage'] and not permissions['can_submit']:
            return Response('Akun Anda tidak memiliki izin download template form ini.', status=403)

        published_version = FormVersionService().get_published_version(form_id)
        if not published_version:
            return Response('Form belum memiliki published schema.', status=400)

        workbook = FormDataImportPipelineService().build_template_workbook(form, published_version)
        filename = secure_filename(f'{form.code or form.slug or "form"}-v{published_version.version_number}-template.xlsx')
        return send_file(
            BytesIO(workbook),
            as_attachment=True,
            download_name=filename,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
    except ValueError as error:
        return Response(str(error), status=400)
    except Exception as error:
        current_app.logger.error(f'Export template Excel error: {str(error)}')
        return Response('Gagal membuat template Excel.', status=500)


@form_web_bp.route('/forms/<int:form_id>/import/mapping', methods=['GET', 'POST'])
@login_required
def import_mapping(form_id):
    """Upload Excel dan tampilkan halaman mapping kolom terhadap published schema."""
    form = None
    published_version = None
    fields = []
    mapping_result = None
    error_message = None
    permissions = _build_form_permissions(None)

    try:
        form = FormService().get_form_detail(form_id)
        permissions = _build_form_permissions(form)
        published_version = FormVersionService().get_published_version(form_id)
        if published_version:
            fields = FormDataImportPipelineService().extract_importable_fields(published_version.schema or {})

        if not form:
            error_message = 'Form tidak ditemukan.'
        elif not permissions['can_view'] and not permissions['can_manage'] and not permissions['can_submit']:
            error_message = 'Akun Anda tidak memiliki izin membuka halaman import untuk form ini.'
            current_app.logger.warning(
                'Import mapping page authorization error: actor tanpa izin view membuka form_id=%s',
                form_id,
            )
        elif not published_version:
            error_message = 'Form belum memiliki published schema. Publish draft terlebih dahulu.'
        elif request.method == 'POST' and not permissions['can_submit']:
            error_message = 'Akun Anda tidak memiliki izin submit/import untuk form ini. Halaman dibuka dalam mode review-only.'
            current_app.logger.warning(
                'Import mapping page submit authorization error: actor tanpa izin submit membuka POST form_id=%s',
                form_id,
            )
        elif request.method == 'POST':
            upload = request.files.get('excel_file')
            action = request.form.get('action', 'preview_mapping')
            if not upload:
                error_message = 'File Excel wajib dipilih.'
            elif action == 'create_batch':
                mapping_config = {
                    key.replace('mapping_', '', 1): value
                    for key, value in request.form.items()
                    if key.startswith('mapping_')
                }
                date_formats = {
                    key.replace('date_format_', '', 1): value
                    for key, value in request.form.items()
                    if key.startswith('date_format_') and value
                }
                if date_formats:
                    mapping_config['__date_formats__'] = date_formats
                import_batch = FormDataImportPipelineService().create_import_batch_from_workbook(
                    form,
                    published_version,
                    upload,
                    mapping_config,
                    actor=_current_actor(),
                )
                return redirect(url_for('form.import_batch_resume', batch_id=import_batch.id))
            else:
                mapping_result = FormDataImportPipelineService().parse_mapping_workbook(
                    upload,
                    published_version,
                )
    except ValueError as error:
        error_message = str(error)
    except Exception as error:
        current_app.logger.error(f'Import mapping page error: {str(error)}')
        error_message = 'Gagal membaca file Excel untuk mapping.'

    return render_template(
        'pages/forms/form_import_mapping.html',
        form=form,
        form_id=form_id,
        published_version=published_version,
        fields=fields,
        mapping_result=mapping_result,
        error_message=error_message,
        permissions=permissions,
        csrf_token=generate_csrf,
    )


@form_web_bp.route('/forms/import/batches/<int:batch_id>/process', methods=['POST'])
@login_required
def process_import_batch(batch_id):
    """Validasi row staging dan insert row valid sebagai submissions."""
    try:
        FormDataImportPipelineService().process_import_batch(batch_id, actor=_current_actor())
        flash('Import batch berhasil diproses.', 'success')
    except ValueError as error:
        flash(str(error), 'error')
        current_app.logger.warning(f'Import batch validation error: {str(error)}')
    except PermissionError as error:
        flash(str(error), 'error')
        current_app.logger.warning(f'Process import batch authorization error: {str(error)}')
    except Exception as error:
        flash('Gagal memproses import batch.', 'error')
        current_app.logger.error(f'Process import batch error: {str(error)}')
    return redirect(url_for('form.import_batch_resume', batch_id=batch_id))


@form_web_bp.route('/forms/import/batches/<int:batch_id>/reimport', methods=['POST'])
@login_required
def reimport_corrected_batch(batch_id):
    service = FormDataImportPipelineService()
    try:
        upload = request.files.get('excel_file')
        if not upload:
            raise ValueError('File Excel koreksi wajib dipilih.')
        new_batch = service.reimport_corrected_error_workbook(
            batch_id,
            upload,
            actor=_current_actor(),
        )
        service.process_import_batch(new_batch.id, actor=_current_actor())
        flash('File koreksi berhasil di-import ulang.', 'success')
        return redirect(url_for('form.import_batch_resume', batch_id=new_batch.id))
    except ValueError as error:
        flash(str(error), 'error')
        current_app.logger.warning(f'Reimport corrected workbook validation error: {str(error)}')
    except PermissionError as error:
        flash(str(error), 'error')
        current_app.logger.warning(f'Reimport corrected workbook authorization error: {str(error)}')
    except Exception as error:
        flash('Gagal memproses file koreksi.', 'error')
        current_app.logger.error(f'Reimport corrected workbook error: {str(error)}')
    return redirect(url_for('form.import_batch_resume', batch_id=batch_id))


@form_web_bp.route('/forms/import/batches/<int:batch_id>/errors.xlsx')
@login_required
def download_import_batch_errors(batch_id):
    try:
        export_result = FormDataImportPipelineService().export_import_batch_errors(batch_id)
        return send_file(
            BytesIO(export_result['content']),
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=export_result['filename'],
        )
    except ValueError as error:
        flash(str(error), 'error')
        current_app.logger.warning(f'Download import batch errors validation error: {str(error)}')
    except Exception as error:
        flash('Gagal mengunduh file error import.', 'error')
        current_app.logger.error(f'Download import batch errors error: {str(error)}')
    return redirect(url_for('form.import_batch_resume', batch_id=batch_id))


@form_web_bp.route('/forms/import/batches/<int:batch_id>')
@login_required
def import_batch_resume(batch_id):
    """Halaman resume awal import batch sebelum validasi/submission insert."""
    summary = None
    error_message = None
    can_process_batch = False
    try:
        summary = FormDataImportPipelineService().get_import_batch_summary(batch_id)
        if not summary:
            error_message = 'Import batch tidak ditemukan.'
        else:
            batch = summary.get('batch')
            can_process_batch = can_submit_form(_current_actor(), batch.form if batch else None)
    except Exception as error:
        current_app.logger.error(f'Import batch resume error: {str(error)}')
        error_message = 'Gagal memuat resume import batch.'

    return render_template(
        'pages/forms/form_import_batch_resume.html',
        summary=summary,
        batch=summary.get('batch') if summary else None,
        rows=summary.get('rows') if summary else [],
        error_rows=summary.get('error_rows') if summary else [],
        error_rows_count=summary.get('error_rows_count', 0) if summary else 0,
        error_filename=summary.get('error_filename') if summary else None,
        can_process_batch=can_process_batch,
        error_message=error_message,
        csrf_token=generate_csrf,
    )


@form_web_bp.route('/forms/<int:form_id>/preview')
@login_required
def preview(form_id):
    """Render published form preview/fill container.

    Route web ini hanya mengambil schema published untuk dirender Form.io di frontend.
    Submit response tetap dikirim lewat API v1 Submission.
    """
    form = None
    published_version = None
    schema = dict(EMPTY_FORMIO_SCHEMA)

    try:
        form = FormService().get_form_detail(form_id)
        published_version = FormVersionService().get_published_version(form_id)
        if published_version and isinstance(published_version.schema, dict):
            schema = published_version.schema
    except Exception as error:
        current_app.logger.warning(
            f'Gagal memuat published schema untuk form preview: {str(error)}'
        )

    return render_template(
        'pages/forms/form_preview.html',
        form=form,
        permissions=_build_form_permissions(form),
        form_id=form_id,
        published_version=published_version,
        schema=schema,
    )

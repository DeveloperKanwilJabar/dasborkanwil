from flask import Blueprint, current_app, request
from flask_login import current_user

from app.core.extensions import db
from app.core.utils import json_response, now_utc
from app.modules.form.models import Form, FormVersion
from app.modules.form.services import FormService, FormVersionService


api_form_bp = Blueprint(
    'api_form_v1',
    __name__,
    url_prefix='/api/v1',
)


def validation_error_response(error):
    return json_response(
        False,
        str(error),
        data={'error_type': 'validation_error'},
        status=400,
    )


def authorization_error_response(error):
    return json_response(
        False,
        str(error),
        data={'error_type': 'authorization_error'},
        status=403,
    )


def current_actor():
    if current_user and not getattr(current_user, 'is_anonymous', True):
        return current_user
    return None


def serialize_form(form):
    if not form:
        return None
    return {
        'id': form.id,
        'uuid': form.uuid,
        'code': form.code,
        'slug': form.slug,
        'name': form.name,
        'description': form.description,
        'status': form.status,
        'visibility': form.visibility,
        'settings': form.settings,
        'owner_user_id': form.owner_user_id,
        'owner_scope_type': getattr(form, 'owner_scope_type', None),
        'owner_scope_code': getattr(form, 'owner_scope_code', None),
        'owner_scope_name': getattr(form, 'owner_scope_name', None),
        'owner_scope_path': getattr(form, 'owner_scope_path', None),
        'target_scope_type': getattr(form, 'target_scope_type', None),
        'target_scope_code': getattr(form, 'target_scope_code', None),
        'target_scope_name': getattr(form, 'target_scope_name', None),
        'target_scope_path': getattr(form, 'target_scope_path', None),
        'access_policy_key': getattr(form, 'access_policy_key', None),
        'created_at': form.created_at.isoformat() if form.created_at else None,
        'updated_at': form.updated_at.isoformat() if form.updated_at else None,
    }


def serialize_form_version(version):
    if not version:
        return None
    return {
        'id': version.id,
        'uuid': version.uuid,
        'form_id': version.form_id,
        'version_number': version.version_number,
        'version_label': version.version_label,
        'schema': version.schema,
        'validation_rules': version.validation_rules,
        'submission_contract': version.submission_contract,
        'scope_snapshot': getattr(version, 'scope_snapshot', None),
        'access_policy_snapshot': getattr(version, 'access_policy_snapshot', None),
        'status': version.status,
        'is_published': version.is_published,
        'published_at': version.published_at.isoformat() if version.published_at else None,
        'notes': version.notes,
        'created_at': version.created_at.isoformat() if version.created_at else None,
        'updated_at': version.updated_at.isoformat() if version.updated_at else None,
    }


@api_form_bp.route('/forms', methods=['POST'])
def create_form():
    """Create form + optional initial draft version."""
    data = request.get_json(silent=True) or {}

    try:
        result = FormService().create_form(data, actor=current_actor())
        return json_response(
            True,
            'Form berhasil dibuat.',
            {
                'form': serialize_form(result.get('form')),
                'draft_version': serialize_form_version(result.get('draft_version')),
            },
            status=201,
        )
    except ValueError as error:
        return validation_error_response(error)
    except PermissionError as error:
        current_app.logger.warning(f'Create form API authorization error: {str(error)}')
        return authorization_error_response(error)
    except Exception as error:
        db.session.rollback()
        current_app.logger.error(f'Create form API error: {str(error)}')
        return json_response(False, 'Gagal membuat form.', status=500)


@api_form_bp.route('/forms/<int:form_id>', methods=['GET'])
def get_form_detail(form_id):
    """Get form detail, versions, and draft/published pointers."""
    try:
        form = FormService().get_form_detail(form_id)
        if not form:
            return json_response(False, 'Form tidak ditemukan.', status=404)

        versions = FormVersionService().repository.list_versions(form_id)
        draft_version = next((version for version in versions if version.status == 'draft'), None)
        published_version = next((version for version in versions if version.is_published), None)

        return json_response(
            True,
            'Detail form berhasil diambil.',
            {
                'form': serialize_form(form),
                'versions': [serialize_form_version(version) for version in versions],
                'draft_version': serialize_form_version(draft_version),
                'published_version': serialize_form_version(published_version),
            },
        )
    except Exception as error:
        current_app.logger.error(f'Get form detail API error: {str(error)}')
        return json_response(False, 'Gagal mengambil detail form.', status=500)


@api_form_bp.route('/forms/<int:form_id>/versions/draft', methods=['POST'])
def create_draft_version(form_id):
    """Create or clone draft form version."""
    data = request.get_json(silent=True) or {}

    try:
        draft_version = FormVersionService().create_draft_version(
            form_id=form_id,
            schema=data.get('schema'),
            source_version_id=data.get('source_version_id'),
            validation_rules=data.get('validation_rules'),
            submission_contract=data.get('submission_contract'),
            actor=current_actor(),
        )
        return json_response(
            True,
            'Draft version berhasil dibuat.',
            {'draft_version': serialize_form_version(draft_version)},
            status=201,
        )
    except ValueError as error:
        return validation_error_response(error)
    except PermissionError as error:
        actor = current_actor()
        current_app.logger.warning(
            'Create draft version API authorization error: actor_id=%s form_id=%s error=%s',
            getattr(actor, 'id', None),
            form_id,
            str(error),
        )
        return authorization_error_response(error)
    except Exception as error:
        db.session.rollback()
        current_app.logger.error(f'Create draft version API error: {str(error)}')
        return json_response(False, 'Gagal membuat draft version.', status=500)


@api_form_bp.route('/form-versions/<int:version_id>/draft-schema', methods=['PATCH'])
def update_draft_schema(version_id):
    """Autosave draft schema to the same draft version row."""
    data = request.get_json(silent=True) or {}

    try:
        draft_version = FormVersionService().update_draft_schema(
            version_id=version_id,
            schema=data.get('schema'),
            validation_rules=data.get('validation_rules'),
            actor=current_actor(),
        )
        return json_response(
            True,
            'Draft schema berhasil disimpan.',
            {
                'draft_version': serialize_form_version(draft_version),
                'autosaved_at': now_utc().isoformat(),
            },
        )
    except ValueError as error:
        return validation_error_response(error)
    except PermissionError as error:
        actor = current_actor()
        current_app.logger.warning(
            'Update draft schema API authorization error: actor_id=%s version_id=%s error=%s',
            getattr(actor, 'id', None),
            version_id,
            str(error),
        )
        return authorization_error_response(error)
    except Exception as error:
        db.session.rollback()
        current_app.logger.error(f'Update draft schema API error: {str(error)}')
        return json_response(False, 'Gagal menyimpan draft schema.', status=500)


@api_form_bp.route('/form-versions/<int:version_id>/publish', methods=['POST'])
def publish_version(version_id):
    """Publish draft version and make parent form published."""
    request.get_json(silent=True) or {}

    try:
        published_version = FormVersionService().publish_version(version_id, actor=current_actor())
        return json_response(
            True,
            'Form version berhasil dipublish.',
            {'published_version': serialize_form_version(published_version)},
        )
    except ValueError as error:
        return validation_error_response(error)
    except PermissionError as error:
        actor = current_actor()
        current_app.logger.warning(
            'Publish version API authorization error: actor_id=%s version_id=%s error=%s',
            getattr(actor, 'id', None),
            version_id,
            str(error),
        )
        return authorization_error_response(error)
    except Exception as error:
        db.session.rollback()
        current_app.logger.error(f'Publish version API error: {str(error)}')
        return json_response(False, 'Gagal publish form version.', status=500)

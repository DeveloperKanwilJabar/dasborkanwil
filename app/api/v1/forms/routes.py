"""Endpoint API v1 untuk Form Registry.

Fokus modul ini adalah menyediakan contract HTTP yang tipis di atas service layer.
Setiap endpoint memiliki penjelasan penggunaan, parameter, tipe output, dan contoh
payload agar reviewer lebih mudah membaca alur create form -> draft -> autosave -> publish.
"""

from flask import Blueprint, current_app, request
from flask_login import current_user
from flasgger import swag_from

from app.api.docs import (
    body_parameter,
    build_spec,
    envelope_schema,
    path_parameter,
    standard_responses,
)
from app.core.extensions import db
from app.core.utils import json_response, now_utc
from app.modules.form.services import FormService, FormVersionService


api_form_bp = Blueprint(
    'api_form_v1',
    __name__,
    url_prefix='/api/v1',
)

FORM_SCHEMA = {
    'type': 'object',
    'properties': {
        'id': {'type': 'integer', 'example': 1},
        'uuid': {'type': 'string', 'example': 'f0c11f6b-9e76-4d47-88ec-1b94fef7c001'},
        'code': {'type': 'string', 'example': 'FORM-PK-2026'},
        'slug': {'type': 'string', 'example': 'form-pk-2026'},
        'name': {'type': 'string', 'example': 'Form PK 2026'},
        'description': {'type': 'string', 'nullable': True, 'example': 'Form pengumpulan target dan realisasi PK.'},
        'status': {'type': 'string', 'example': 'draft'},
        'visibility': {'type': 'string', 'example': 'internal'},
        'settings': {'type': 'object', 'nullable': True},
        'owner_user_id': {'type': 'integer', 'nullable': True},
        'owner_scope_type': {'type': 'string', 'nullable': True, 'example': 'kanwil'},
        'owner_scope_code': {'type': 'string', 'nullable': True, 'example': 'KANWIL-JABAR'},
        'target_scope_type': {'type': 'string', 'nullable': True, 'example': 'satker'},
        'target_scope_code': {'type': 'string', 'nullable': True, 'example': 'SATKER-001'},
        'access_policy_key': {'type': 'string', 'nullable': True, 'example': 'form.default'},
        'created_at': {'type': 'string', 'format': 'date-time', 'nullable': True},
        'updated_at': {'type': 'string', 'format': 'date-time', 'nullable': True},
    },
}

FORM_VERSION_SCHEMA = {
    'type': 'object',
    'properties': {
        'id': {'type': 'integer', 'example': 11},
        'uuid': {'type': 'string', 'example': 'a8b31ef6-3dc9-4edf-bf84-c0416fa70011'},
        'form_id': {'type': 'integer', 'example': 1},
        'version_number': {'type': 'integer', 'example': 1},
        'version_label': {'type': 'string', 'nullable': True, 'example': 'Draft awal'},
        'schema': {'type': 'object', 'example': {'display': 'form', 'components': [{'key': 'nama', 'type': 'textfield'}]}},
        'validation_rules': {'type': 'object', 'nullable': True, 'example': {'required': ['nama']}},
        'submission_contract': {'type': 'object', 'nullable': True, 'example': {'reporting_year_required': True}},
        'scope_snapshot': {'type': 'object', 'nullable': True},
        'access_policy_snapshot': {'type': 'object', 'nullable': True},
        'status': {'type': 'string', 'example': 'draft'},
        'is_published': {'type': 'boolean', 'example': False},
        'published_at': {'type': 'string', 'format': 'date-time', 'nullable': True},
        'notes': {'type': 'string', 'nullable': True},
        'created_at': {'type': 'string', 'format': 'date-time', 'nullable': True},
        'updated_at': {'type': 'string', 'format': 'date-time', 'nullable': True},
    },
}

CREATE_FORM_DOC = build_spec(
    tag='Forms',
    summary='Buat form baru beserta draft awal opsional.',
    description=(
        'Digunakan saat user memulai form baru di Form Builder. '\
        'Input utama: code, slug, name, dan optional schema awal. '\
        'Output: object `form` dan `draft_version` bila schema awal dikirim.\n\n'
        'Contoh penggunaan: POST /api/v1/forms dengan body berisi schema Form.io awal.'
    ),
    parameters=[
        body_parameter(
            'body',
            {
                'type': 'object',
                'required': ['code', 'slug', 'name'],
                'properties': {
                    'code': {'type': 'string', 'example': 'FORM-PK-2026'},
                    'slug': {'type': 'string', 'example': 'form-pk-2026'},
                    'name': {'type': 'string', 'example': 'Form PK 2026'},
                    'description': {'type': 'string', 'example': 'Form pengumpulan data PK 2026.'},
                    'visibility': {'type': 'string', 'example': 'internal'},
                    'schema': {'type': 'object', 'example': {'display': 'form', 'components': []}},
                    'validation_rules': {'type': 'object', 'example': {'required': ['nama']}},
                    'submission_contract': {'type': 'object', 'example': {'reporting_year_required': True}},
                },
            },
            description='Payload pembuatan form. Bila `schema` diisi, service otomatis membuat draft version awal.',
        )
    ],
    responses=standard_responses(
        envelope_schema(
            {
                'type': 'object',
                'properties': {
                    'form': FORM_SCHEMA,
                    'draft_version': FORM_VERSION_SCHEMA,
                },
            },
            message_example='Form berhasil dibuat.',
        ),
        'Form berhasil dibuat.',
        success_status=201,
    ),
)

GET_FORM_DETAIL_DOC = build_spec(
    tag='Forms',
    summary='Ambil detail form lengkap beserta daftar version.',
    description=(
        'Endpoint read-only untuk me-render halaman builder/detail form. '\
        'Output mengandung `form`, seluruh `versions`, pointer `draft_version`, '\
        'dan `published_version` agar UI tidak perlu menghitung ulang.'
    ),
    parameters=[path_parameter('form_id', description='ID integer form yang ingin dibaca.', example=1)],
    responses=standard_responses(
        envelope_schema(
            {
                'type': 'object',
                'properties': {
                    'form': FORM_SCHEMA,
                    'versions': {'type': 'array', 'items': FORM_VERSION_SCHEMA},
                    'draft_version': FORM_VERSION_SCHEMA,
                    'published_version': FORM_VERSION_SCHEMA,
                },
            },
            message_example='Detail form berhasil diambil.',
        ),
        'Detail form berhasil diambil.',
    ),
)

CREATE_DRAFT_VERSION_DOC = build_spec(
    tag='Forms',
    summary='Buat draft version baru atau clone dari version sumber.',
    description=(
        'Dipakai ketika user ingin membuat draft baru dari nol atau clone dari versi published. '\
        'Parameter penting: `form_id` pada path. Body dapat berisi `schema`, `source_version_id`, '\
        '`validation_rules`, dan `submission_contract`. Output berupa object `draft_version`.'
    ),
    parameters=[
        path_parameter('form_id', description='ID form induk.', example=1),
        body_parameter(
            'body',
            {
                'type': 'object',
                'properties': {
                    'schema': {'type': 'object', 'example': {'display': 'form', 'components': [{'key': 'nama'}]}},
                    'source_version_id': {'type': 'integer', 'example': 5},
                    'validation_rules': {'type': 'object', 'example': {'required': ['nama']}},
                    'submission_contract': {'type': 'object', 'example': {'reporting_year_required': True}},
                },
            },
            required=False,
            description='Payload draft baru. Bila `source_version_id` dikirim dan `schema` kosong, schema akan diclone dari sumber.',
        ),
    ],
    responses=standard_responses(
        envelope_schema(
            {'type': 'object', 'properties': {'draft_version': FORM_VERSION_SCHEMA}},
            message_example='Draft version berhasil dibuat.',
        ),
        'Draft version berhasil dibuat.',
        success_status=201,
    ),
)

UPDATE_DRAFT_SCHEMA_DOC = build_spec(
    tag='Forms',
    summary='Autosave schema draft pada row version yang sama.',
    description=(
        'Endpoint ini dipanggil berkala oleh UI Form Builder saat autosave. '\
        'Input utama: `version_id` dan object `schema`. Output: `draft_version` terbaru '\
        'serta `autosaved_at` bertipe string datetime ISO-8601.'
    ),
    parameters=[
        path_parameter('version_id', description='ID draft version yang sedang diedit.', example=11),
        body_parameter(
            'body',
            {
                'type': 'object',
                'required': ['schema'],
                'properties': {
                    'schema': {'type': 'object', 'example': {'display': 'form', 'components': [{'key': 'alamat'}]}},
                    'validation_rules': {'type': 'object', 'example': {'required': ['alamat']}},
                },
            },
            description='Schema draft terbaru hasil edit builder.',
        ),
    ],
    responses=standard_responses(
        envelope_schema(
            {
                'type': 'object',
                'properties': {
                    'draft_version': FORM_VERSION_SCHEMA,
                    'autosaved_at': {'type': 'string', 'format': 'date-time'},
                },
            },
            message_example='Draft schema berhasil disimpan.',
        ),
        'Draft schema berhasil disimpan.',
    ),
)

PUBLISH_VERSION_DOC = build_spec(
    tag='Forms',
    summary='Publish draft version menjadi versi aktif form.',
    description=(
        'Digunakan setelah draft lulus review. Endpoint ini memvalidasi draft, '\
        'menandai version sebagai published, dan menyinkronkan status form induk. '\
        'Output: object `published_version`.'
    ),
    parameters=[path_parameter('version_id', description='ID draft version yang akan dipublish.', example=11)],
    responses=standard_responses(
        envelope_schema(
            {'type': 'object', 'properties': {'published_version': FORM_VERSION_SCHEMA}},
            message_example='Form version berhasil dipublish.',
        ),
        'Form version berhasil dipublish.',
    ),
)


def validation_error_response(error):
    """Bangun response 400 standar untuk error validasi.

    Args:
        error (Exception): Error validasi yang ingin dikirim ke client.

    Returns:
        Response: JSON response dengan shape `success/message/data.error_type`.
    """
    return json_response(
        False,
        str(error),
        data={'error_type': 'validation_error'},
        status=400,
    )



def authorization_error_response(error):
    """Bangun response 403 standar untuk error otorisasi."""
    return json_response(
        False,
        str(error),
        data={'error_type': 'authorization_error'},
        status=403,
    )



def current_actor():
    """Ambil actor login aktif bila request datang dari web session.

    Returns:
        User | None: User Flask-Login yang aktif, atau None bila anonymous.
    """
    if current_user and not getattr(current_user, 'is_anonymous', True):
        return current_user
    return None



def serialize_form(form):
    """Serialisasi model Form menjadi dict yang aman untuk JSON response.

    Args:
        form (Form | None): Instance form dari service/repository.

    Returns:
        dict | None: Representasi form untuk API response.
    """
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
    """Serialisasi model FormVersion menjadi dict JSON-friendly.

    Args:
        version (FormVersion | None): Instance version hasil service layer.

    Returns:
        dict | None: Payload version untuk response API.
    """
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
@swag_from(CREATE_FORM_DOC)
def create_form():
    """Create form + optional initial draft version.

    Penggunaan:
    - method: POST
    - input: JSON body berisi code/slug/name dan optional schema
    - output: envelope JSON dengan `form` dan optional `draft_version`

    Contoh body:
        {
          "code": "FORM-PK-2026",
          "slug": "form-pk-2026",
          "name": "Form PK 2026",
          "schema": {"display": "form", "components": []}
        }
    """
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
@swag_from(GET_FORM_DETAIL_DOC)
def get_form_detail(form_id):
    """Get form detail, versions, and draft/published pointers.

    Args:
        form_id (int): ID form yang ingin dibaca.

    Returns:
        Response: JSON envelope berisi detail form, daftar version, draft, dan published.
    """
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
@swag_from(CREATE_DRAFT_VERSION_DOC)
def create_draft_version(form_id):
    """Create or clone draft form version.

    Args:
        form_id (int): ID form induk.

    Returns:
        Response: JSON envelope dengan object `draft_version`.
    """
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
@swag_from(UPDATE_DRAFT_SCHEMA_DOC)
def update_draft_schema(version_id):
    """Autosave draft schema to the same draft version row.

    Args:
        version_id (int): ID draft version yang akan diautosave.

    Returns:
        Response: JSON envelope berisi `draft_version` dan timestamp `autosaved_at`.
    """
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
@swag_from(PUBLISH_VERSION_DOC)
def publish_version(version_id):
    """Publish draft version and make parent form published.

    Args:
        version_id (int): ID draft version yang akan dipublish.

    Returns:
        Response: JSON envelope berisi `published_version`.
    """
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

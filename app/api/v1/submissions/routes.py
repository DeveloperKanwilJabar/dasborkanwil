"""Endpoint API v1 untuk Submission.

Modul ini menjelaskan alur submit form dan pembacaan freshness data. Dokumen
Swagger difokuskan agar reviewer memahami payload, konteks scope, serta bentuk
respons yang dipakai dashboard dan integrasi eksternal.
"""

from flask import Blueprint, current_app, request
from flask_login import current_user, login_required
from flasgger import swag_from

from app.api.docs import (
    body_parameter,
    build_spec,
    envelope_schema,
    path_parameter,
    query_parameter,
    standard_responses,
)
from app.core.access import can_update_submission, can_view_submission
from app.core.extensions import db
from app.core.utils import json_response
from app.modules.submission.services import SubmissionService


api_submission_bp = Blueprint(
    'api_submission_v1',
    __name__,
    url_prefix='/api/v1',
)

SUBMISSION_SCHEMA = {
    'type': 'object',
    'properties': {
        'id': {'type': 'integer', 'example': 101},
        'uuid': {'type': 'string', 'example': 'subm-uuid'},
        'submission_number': {'type': 'string', 'example': 'SUB-2026-0001'},
        'form_id': {'type': 'integer', 'example': 1},
        'form_version_id': {'type': 'integer', 'example': 11},
        'reporting_year': {'type': 'integer', 'example': 2026},
        'reporting_period_id': {'type': 'integer', 'nullable': True, 'example': 7},
        'status': {'type': 'string', 'example': 'submitted'},
        'submitted_at': {'type': 'string', 'format': 'date-time', 'nullable': True},
        'payload': {'type': 'object', 'example': {'nama': 'Budi', 'nilai': 95}},
        'meta': {'type': 'object', 'nullable': True, 'example': {'source': 'web'}},
        'validation_snapshot': {'type': 'object', 'nullable': True, 'example': {'is_valid': True}},
        'submitted_by': {'type': 'integer', 'nullable': True},
        'submitted_by_uuid': {'type': 'string', 'nullable': True},
        'owner_scope_type': {'type': 'string', 'nullable': True, 'example': 'kanwil'},
        'owner_scope_code': {'type': 'string', 'nullable': True, 'example': 'KANWIL-JABAR'},
        'subject_type': {'type': 'string', 'nullable': True, 'example': 'satker'},
        'subject_ref_id': {'type': 'integer', 'nullable': True, 'example': 8},
        'subject_ref_uuid': {'type': 'string', 'nullable': True},
        'subject_ref_code': {'type': 'string', 'nullable': True},
        'subject_ref_name': {'type': 'string', 'nullable': True},
        'access_policy_key': {'type': 'string', 'nullable': True, 'example': 'submission.default'},
        'source_type': {'type': 'string', 'nullable': True, 'example': 'web'},
        'source_ref': {'type': 'string', 'nullable': True},
        'created_at': {'type': 'string', 'format': 'date-time', 'nullable': True},
        'updated_at': {'type': 'string', 'format': 'date-time', 'nullable': True},
    },
}

SUBMIT_FORM_DOC = build_spec(
    tag='Submissions',
    summary='Kirim submission ke published form version.',
    description=(
        'Endpoint utama untuk menyimpan jawaban form. '
        'Input: `form_id` pada path, `payload` object, serta optional konteks '
        '`owner_scope`, `subject`, `reporting_year`, dan `reporting_period_id`. '
        'Output: object `submission` dan `submission_number`.\n\n'
        'Contoh penggunaan: POST /api/v1/forms/1/submissions dari preview form atau import pipeline.'
    ),
    parameters=[
        path_parameter('form_id', description='ID form yang published version-nya akan menerima submission.', example=1),
        body_parameter(
            'body',
            {
                'type': 'object',
                'required': ['payload'],
                'properties': {
                    'payload': {'type': 'object', 'example': {'nama': 'Budi', 'nilai': 95}},
                    'meta': {'type': 'object', 'example': {'source': 'web', 'channel': 'preview'}},
                    'source_type': {'type': 'string', 'example': 'web'},
                    'source_ref': {'type': 'string', 'example': 'preview-form-1'},
                    'owner_scope': {
                        'type': 'object',
                        'example': {'type': 'kanwil', 'code': 'KANWIL-JABAR', 'name': 'Kanwil Jawa Barat'},
                    },
                    'subject': {
                        'type': 'object',
                        'example': {'type': 'satker', 'ref_id': 8, 'ref_code': 'SATKER-001', 'ref_name': 'Satker Bandung'},
                    },
                    'reporting_year': {'type': 'integer', 'example': 2026},
                    'reporting_period_id': {'type': 'integer', 'example': 7},
                },
            },
            description='Payload jawaban form dan konteks submission yang akan diaudit di backend.',
        ),
    ],
    responses=standard_responses(
        envelope_schema(
            {
                'type': 'object',
                'properties': {
                    'submission': SUBMISSION_SCHEMA,
                    'submission_number': {'type': 'string', 'example': 'SUB-2026-0001'},
                },
            },
            message_example='Submission berhasil dikirim.',
        ),
        'Submission berhasil dikirim.',
        success_status=201,
    ),
)

FRESHNESS_DOC = build_spec(
    tag='Submissions',
    summary='Ambil freshness sumber data dari submissions.submitted_at.',
    description=(
        'Dipakai dashboard analytics untuk mengetahui kapan terakhir data bisnis resmi masuk. '\
        'Output utama adalah `data_last_updated_at` dan metadata filter yang dipakai.'
    ),
    parameters=[
        query_parameter('form_id', value_type='integer', description='Filter ID form.', example=1),
        query_parameter('reporting_year', value_type='integer', description='Filter tahun laporan.', example=2026),
        query_parameter('reporting_period_id', value_type='integer', description='Filter reporting period.', example=7),
    ],
    responses=standard_responses(
        envelope_schema(
            {
                'type': 'object',
                'properties': {
                    'data_last_updated_at': {'type': 'string', 'format': 'date-time', 'nullable': True},
                    'source': {'type': 'string', 'example': 'submissions.submitted_at'},
                    'form_id': {'type': 'integer', 'nullable': True},
                    'reporting_year': {'type': 'integer', 'nullable': True},
                    'reporting_period_id': {'type': 'integer', 'nullable': True},
                },
            },
            message_example='Freshness berhasil diambil.',
        ),
        'Freshness berhasil diambil.',
    ),
)


def validation_error_response(error):
    """Bangun response 400 standar untuk validasi submission."""
    return json_response(
        False,
        str(error),
        data={'error_type': 'validation_error'},
        status=400,
    )



def authorization_error_response(error):
    """Bangun response 403 standar untuk kegagalan otorisasi submission."""
    return json_response(
        False,
        str(error),
        data={'error_type': 'authorization_error'},
        status=403,
    )



def current_actor():
    """Ambil actor login aktif dari Flask-Login, bila ada."""
    if current_user and not getattr(current_user, 'is_anonymous', True):
        return current_user
    return None



def parse_optional_int(value):
    """Konversi nilai query/body opsional menjadi integer.

    Args:
        value (str | int | None): Nilai mentah dari request.

    Returns:
        int | None: Integer hasil parsing, atau None bila input kosong.
    """
    if value in (None, ''):
        return None
    return int(value)



def serialize_submission_permissions(submission, actor=None):
    """Serialisasi capability ABAC per submission untuk UI."""
    return {
        'can_view': can_view_submission(actor, submission) if actor else True,
        'can_edit': can_update_submission(actor, submission) if actor else True,
    }



def serialize_submission(submission):
    """Serialisasi model Submission ke dict JSON-friendly."""
    if not submission:
        return None
    return {
        'id': submission.id,
        'uuid': submission.uuid,
        'submission_number': submission.submission_number,
        'form_id': submission.form_id,
        'form_version_id': submission.form_version_id,
        'reporting_year': submission.reporting_year,
        'reporting_period_id': submission.reporting_period_id,
        'status': submission.status,
        'submitted_at': submission.submitted_at.isoformat() if submission.submitted_at else None,
        'payload': submission.payload,
        'meta': submission.meta,
        'validation_snapshot': submission.validation_snapshot,
        'submitted_by': submission.submitted_by,
        'submitted_by_uuid': submission.submitted_by_uuid,
        'owner_scope_type': getattr(submission, 'owner_scope_type', None),
        'owner_scope_code': getattr(submission, 'owner_scope_code', None),
        'owner_scope_name': getattr(submission, 'owner_scope_name', None),
        'owner_scope_path': getattr(submission, 'owner_scope_path', None),
        'subject_type': getattr(submission, 'subject_type', None),
        'subject_ref_id': getattr(submission, 'subject_ref_id', None),
        'subject_ref_uuid': getattr(submission, 'subject_ref_uuid', None),
        'subject_ref_code': getattr(submission, 'subject_ref_code', None),
        'subject_ref_name': getattr(submission, 'subject_ref_name', None),
        'access_policy_key': getattr(submission, 'access_policy_key', None),
        'source_type': submission.source_type,
        'source_ref': submission.source_ref,
        'created_at': submission.created_at.isoformat() if submission.created_at else None,
        'updated_at': submission.updated_at.isoformat() if submission.updated_at else None,
        'permissions': serialize_submission_permissions(submission, current_actor()),
    }


@api_submission_bp.route('/submissions', methods=['GET'])
@login_required
def list_submissions():
    """List submission untuk UI Grid.js dengan filter ABAC di service layer."""
    try:
        statuses = request.args.getlist('status') or None
        submissions = SubmissionService().list_submissions(
            actor=current_actor(),
            form_id=parse_optional_int(request.args.get('form_id')),
            reporting_year=parse_optional_int(request.args.get('reporting_year')),
            reporting_period_id=parse_optional_int(request.args.get('reporting_period_id')),
            statuses=statuses,
        )
        return json_response(True, 'Submissions berhasil diambil.', [serialize_submission(item) for item in submissions])
    except ValueError as error:
        return validation_error_response(error)
    except Exception as error:
        current_app.logger.error(f'List submissions API error: {str(error)}')
        return json_response(False, 'Gagal mengambil daftar submission.', status=500)


@api_submission_bp.route('/submissions/<int:submission_id>', methods=['GET'])
@login_required
def get_submission(submission_id):
    """Ambil detail submission untuk modal edit."""
    try:
        submission = SubmissionService().get_submission(submission_id, actor=current_actor())
        return json_response(True, 'Submission berhasil diambil.', {'submission': serialize_submission(submission)})
    except ValueError as error:
        return validation_error_response(error)
    except PermissionError as error:
        return authorization_error_response(error)
    except Exception as error:
        current_app.logger.error(f'Get submission API error: {str(error)}')
        return json_response(False, 'Gagal mengambil submission.', status=500)


@api_submission_bp.route('/submissions/<int:submission_id>', methods=['PUT'])
@login_required
def update_submission(submission_id):
    """Update payload submission dan refresh submitted_at untuk freshness dataset."""
    data = request.get_json(silent=True) or {}
    try:
        submission = SubmissionService().update_submission(
            submission_id,
            payload=data.get('payload'),
            actor=current_actor(),
            refresh_submitted_at=data.get('refresh_submitted_at', True),
        )
        return json_response(True, 'Submission berhasil diupdate.', {'submission': serialize_submission(submission)})
    except ValueError as error:
        return validation_error_response(error)
    except PermissionError as error:
        return authorization_error_response(error)
    except Exception as error:
        db.session.rollback()
        current_app.logger.error(f'Update submission API error: {str(error)}')
        return json_response(False, 'Gagal mengupdate submission.', status=500)


@api_submission_bp.route('/forms/<int:form_id>/submissions', methods=['POST'])
@swag_from(SUBMIT_FORM_DOC)
def submit_form(form_id):
    """Submit payload to a published form version.

    Args:
        form_id (int): ID form yang menerima submission.

    Returns:
        Response: JSON envelope dengan object `submission` dan nomor submission.
    """
    data = request.get_json(silent=True) or {}

    try:
        context = {
            'meta': data.get('meta'),
            'source_type': data.get('source_type') or (data.get('meta') or {}).get('source'),
            'source_ref': data.get('source_ref'),
            'owner_scope': data.get('owner_scope'),
            'scope': data.get('scope'),
            'subject': data.get('subject'),
            'subject_type': data.get('subject_type'),
            'subject_ref_id': parse_optional_int(data.get('subject_ref_id')),
            'subject_ref_uuid': data.get('subject_ref_uuid'),
            'subject_ref_code': data.get('subject_ref_code'),
            'subject_ref_name': data.get('subject_ref_name'),
            'access_policy_key': data.get('access_policy_key'),
        }
        submission = SubmissionService().submit(
            form_id=form_id,
            payload=data.get('payload'),
            actor=current_actor(),
            context=context,
            reporting_year=data.get('reporting_year'),
            reporting_period_id=data.get('reporting_period_id'),
        )

        return json_response(
            True,
            'Submission berhasil dikirim.',
            {
                'submission': serialize_submission(submission),
                'submission_number': submission.submission_number,
            },
            status=201,
        )
    except ValueError as error:
        return validation_error_response(error)
    except PermissionError as error:
        current_app.logger.warning(f'Submit form API authorization error: {str(error)}')
        return authorization_error_response(error)
    except Exception as error:
        db.session.rollback()
        current_app.logger.error(f'Submit form API error: {str(error)}')
        return json_response(False, 'Gagal mengirim submission.', status=500)


@api_submission_bp.route('/submissions/freshness', methods=['GET'])
@swag_from(FRESHNESS_DOC)
def get_submission_freshness():
    """Get source data freshness from submissions.submitted_at.

    Returns:
        Response: JSON envelope berisi timestamp freshness dan filter yang dipakai.
    """
    try:
        freshness = SubmissionService().get_data_freshness(
            form_id=parse_optional_int(request.args.get('form_id')),
            reporting_year=parse_optional_int(request.args.get('reporting_year')),
            reporting_period_id=parse_optional_int(request.args.get('reporting_period_id')),
        )
        return json_response(True, 'Freshness berhasil diambil.', freshness)
    except ValueError as error:
        return validation_error_response(error)
    except Exception as error:
        current_app.logger.error(f'Get submission freshness API error: {str(error)}')
        return json_response(False, 'Gagal mengambil freshness submission.', status=500)

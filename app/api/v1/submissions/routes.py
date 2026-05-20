from flask import Blueprint, current_app, request
from flask_login import current_user

from app.core.extensions import db
from app.core.utils import json_response
from app.modules.submission.services import SubmissionService


api_submission_bp = Blueprint(
    'api_submission_v1',
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


def parse_optional_int(value):
    if value in (None, ''):
        return None
    return int(value)


def serialize_submission(submission):
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
    }


@api_submission_bp.route('/forms/<int:form_id>/submissions', methods=['POST'])
def submit_form(form_id):
    """Submit payload to a published form version."""
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
def get_submission_freshness():
    """Get source data freshness from submissions.submitted_at."""
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

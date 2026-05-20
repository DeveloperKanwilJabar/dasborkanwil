from __future__ import annotations

from typing import Any

from .actor_context import build_actor_context, enrich_scope
from .policy_catalog import ACCESS_POLICY_CATALOG, POLICY_MATRIX

ROLE_ALIASES = {
    'super_admin': 'superadmin',
    'administrator': 'admin_lintas_bagian',
    'admin': 'admin_lintas_bagian',
    'admin-kanwil': 'admin_lintas_bagian',
    'auditor': 'auditor_program_pelaporan',
    'program_pelaporan': 'auditor_program_pelaporan',
    'program-dan-pelaporan': 'auditor_program_pelaporan',
    'program dan pelaporan': 'auditor_program_pelaporan',
    'kepala_divisi': 'kepala_divisi',
    'pegawai': 'pegawai_unit',
    'pegawai-unit': 'pegawai_unit',
    'upt_operator': 'operator_upt',
}

FORM_TO_SUBMISSION_POLICY_MAP = {
    'form.unit_internal': 'submission.unit_owned',
    'form.division_broadcast': 'submission.division_audit',
    'form.kanwil_broadcast': 'submission.kanwil_audit',
    'form.upt_network': 'submission.unit_owned',
    'form.admin_only_authoring': 'submission.kanwil_audit',
}


def normalize_role_name(role: Any) -> str:
    role_name = str(role or '').strip().lower()
    if not role_name:
        return ''
    return ROLE_ALIASES.get(role_name, role_name)


def get_actor_roles(actor: Any) -> list[str]:
    context = build_actor_context(actor)
    normalized = []
    for role in context.get('roles', []):
        name = normalize_role_name(role)
        if name and name not in normalized:
            normalized.append(name)
    return normalized


def get_actor_scope(actor: Any) -> dict[str, Any] | None:
    explicit_scope = getattr(actor, 'scope', None) if actor else None
    if isinstance(explicit_scope, dict):
        return enrich_scope(explicit_scope)
    return build_actor_context(actor).get('scope')


def build_scope_from_resource(resource: Any, prefix: str) -> dict[str, Any] | None:
    if not resource:
        return None

    scope = {
        'type': getattr(resource, f'{prefix}_type', None),
        'code': getattr(resource, f'{prefix}_code', None),
        'name': getattr(resource, f'{prefix}_name', None),
        'path': getattr(resource, f'{prefix}_path', None),
    }
    if not any(scope.values()):
        return None
    return enrich_scope(scope)


def actor_has_role(actor: Any, *expected_roles: str) -> bool:
    roles = set(get_actor_roles(actor))
    return any(role in roles for role in expected_roles)


def actor_allows_action(actor: Any, action: str) -> bool:
    if not actor:
        return False

    roles = get_actor_roles(actor)
    if not roles:
        return False

    for role in roles:
        allowed_actions = POLICY_MATRIX.get(role, {}).get('allowed_actions', [])
        if '*' in allowed_actions or action in allowed_actions:
            return True
    return False


def is_exact_scope_match(actor_scope: dict[str, Any] | None, resource_scope: dict[str, Any] | None) -> bool:
    if not actor_scope or not resource_scope:
        return False
    return (
        actor_scope.get('type') == resource_scope.get('type')
        and actor_scope.get('code') == resource_scope.get('code')
    )


def is_actor_within_resource_scope(actor_scope: dict[str, Any] | None, resource_scope: dict[str, Any] | None) -> bool:
    if not resource_scope:
        return True
    if resource_scope.get('type') == 'global':
        return True
    if not actor_scope:
        return False
    if actor_scope.get('code') == resource_scope.get('code'):
        return True

    actor_path = actor_scope.get('path') or []
    resource_code = resource_scope.get('code')
    return bool(resource_code and resource_code in actor_path)


def is_resource_within_actor_scope(actor_scope: dict[str, Any] | None, resource_scope: dict[str, Any] | None) -> bool:
    if not actor_scope or not resource_scope:
        return False
    if actor_scope.get('type') == 'global':
        return True
    if actor_scope.get('code') == resource_scope.get('code'):
        return True

    resource_path = resource_scope.get('path') or []
    actor_code = actor_scope.get('code')
    return bool(actor_code and actor_code in resource_path)


def shares_same_kanwil(actor_scope: dict[str, Any] | None, resource_scope: dict[str, Any] | None) -> bool:
    if not actor_scope or not resource_scope:
        return False
    actor_path = actor_scope.get('path') or []
    resource_path = resource_scope.get('path') or []
    if not actor_path or not resource_path:
        return False
    return actor_path[0] == resource_path[0]


def derive_submission_policy_key(form: Any = None, context: dict[str, Any] | None = None) -> str:
    context = context or {}
    explicit_policy = context.get('access_policy_key')
    if explicit_policy:
        return explicit_policy

    form_policy = getattr(form, 'access_policy_key', None)
    if form_policy and form_policy.startswith('submission.'):
        return form_policy

    return FORM_TO_SUBMISSION_POLICY_MAP.get(form_policy, 'submission.unit_owned')


def can_create_form(actor: Any) -> bool:
    if actor is None:
        return True
    return actor_allows_action(actor, 'form:create')


def can_update_form(actor: Any, form: Any) -> bool:
    if actor is None:
        return True
    if not actor_allows_action(actor, 'form:update'):
        return False
    return True


def can_archive_form(actor: Any, form: Any) -> bool:
    if actor is None:
        return True
    if not actor_allows_action(actor, 'form:archive'):
        return False
    return True


def can_publish_form(actor: Any, form: Any) -> bool:
    if actor is None:
        return True
    if not actor_allows_action(actor, 'form:publish'):
        return False
    return True


def can_view_form(actor: Any, form: Any) -> bool:
    if actor is None:
        return True
    if not actor_allows_action(actor, 'form:view'):
        return False

    actor_scope = get_actor_scope(actor)
    target_scope = build_scope_from_resource(form, 'target_scope')
    return is_actor_within_resource_scope(actor_scope, target_scope)


def can_submit_form(actor: Any, form: Any) -> bool:
    if actor is None:
        return True
    if not actor_allows_action(actor, 'submission:create'):
        return False

    actor_scope = get_actor_scope(actor)
    target_scope = build_scope_from_resource(form, 'target_scope')
    return is_actor_within_resource_scope(actor_scope, target_scope)


def can_view_submission(actor: Any, submission: Any) -> bool:
    if actor is None:
        return False
    if not actor_allows_action(actor, 'submission:view') and not actor_allows_action(actor, 'submission:detail'):
        return False

    actor_scope = get_actor_scope(actor)
    owner_scope = build_scope_from_resource(submission, 'owner_scope')
    policy_key = getattr(submission, 'access_policy_key', None) or 'submission.unit_owned'

    if actor_has_role(actor, 'superadmin'):
        return True

    if policy_key == 'submission.superadmin_full':
        return False

    if policy_key == 'submission.kanwil_audit':
        return shares_same_kanwil(actor_scope, owner_scope)

    if policy_key == 'submission.division_audit':
        if actor_has_role(actor, 'admin_lintas_bagian', 'auditor_program_pelaporan', 'kakanwil'):
            return shares_same_kanwil(actor_scope, owner_scope)
        if actor_has_role(actor, 'kepala_divisi'):
            return is_resource_within_actor_scope(actor_scope, owner_scope)
        return is_exact_scope_match(actor_scope, owner_scope)

    if policy_key == 'submission.unit_owned':
        if actor_has_role(actor, 'admin_lintas_bagian', 'auditor_program_pelaporan', 'kakanwil'):
            return shares_same_kanwil(actor_scope, owner_scope)
        return is_exact_scope_match(actor_scope, owner_scope)

    return is_resource_within_actor_scope(actor_scope, owner_scope)


def ensure_known_policy(policy_key: str | None) -> bool:
    if not policy_key:
        return False
    return policy_key in ACCESS_POLICY_CATALOG

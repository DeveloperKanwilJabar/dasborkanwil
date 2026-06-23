"""Facade helper akses dan konteks actor.

Modul ini mengekspor fungsi-fungsi yang paling sering dipakai service/domain
agar caller tidak perlu mengingat path file access yang lebih detail.
"""

from .actor_context import (
    build_actor_context,
    build_scope_settings,
    enrich_scope,
    merge_actor_settings,
    normalize_actor_settings,
)
from .evaluator import (
    can_archive_form,
    can_create_form,
    can_publish_form,
    can_submit_form,
    can_update_form,
    can_update_submission,
    can_view_form,
    can_view_submission,
    derive_submission_policy_key,
)
from .policy_catalog import (
    ACCESS_POLICY_CATALOG,
    BOOTSTRAP_SCOPE_REGISTRY,
    ORG_SCOPE_TYPES,
    POLICY_MATRIX,
)

__all__ = [
    'build_actor_context',
    'build_scope_settings',
    'enrich_scope',
    'merge_actor_settings',
    'normalize_actor_settings',
    'ACCESS_POLICY_CATALOG',
    'BOOTSTRAP_SCOPE_REGISTRY',
    'ORG_SCOPE_TYPES',
    'POLICY_MATRIX',
    'can_archive_form',
    'can_create_form',
    'can_publish_form',
    'can_submit_form',
    'can_update_form',
    'can_update_submission',
    'can_view_form',
    'can_view_submission',
    'derive_submission_policy_key',
]

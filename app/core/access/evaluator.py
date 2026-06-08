"""Evaluator akses RBAC/ABAC ringan untuk domain form dan submission.

Modul ini belum menjadi policy engine penuh, tetapi sudah menyediakan helper
praktis untuk memutuskan apakah actor boleh membuat, melihat, mempublikasikan,
atau membaca submission berdasarkan role, action matrix, dan scope resource.
"""

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
    """Normalisasi alias role menjadi nama role kanonis.

    Args:
        role (Any): Nilai role mentah dari user/settings.

    Returns:
        str: Nama role yang telah dinormalisasi ke kamus `ROLE_ALIASES`.

    Example:
        >>> normalize_role_name('admin')
        'admin_lintas_bagian'
    """
    role_name = str(role or '').strip().lower()
    if not role_name:
        return ''
    return ROLE_ALIASES.get(role_name, role_name)


def get_actor_roles(actor: Any) -> list[str]:
    """Ambil daftar role actor dalam bentuk kanonis dan unik.

    Args:
        actor (Any): Object actor aplikasi.

    Returns:
        list[str]: Daftar role actor tanpa duplikasi.

    Example:
        >>> get_actor_roles(actor)
        ['pegawai_unit']
    """
    context = build_actor_context(actor)
    normalized = []
    for role in context.get('roles', []):
        name = normalize_role_name(role)
        if name and name not in normalized:
            normalized.append(name)
    return normalized


def get_actor_scope(actor: Any) -> dict[str, Any] | None:
    """Ambil scope actor yang sudah diperkaya metadata registry.

    Args:
        actor (Any): Object actor aplikasi.

    Returns:
        dict[str, Any] | None: Scope actor hasil enrich, atau `None` jika tidak
        tersedia.

    Example:
        >>> scope = get_actor_scope(actor)
        >>> scope['code'] if scope else None
        'ki'
    """
    explicit_scope = getattr(actor, 'scope', None) if actor else None
    if isinstance(explicit_scope, dict):
        return enrich_scope(explicit_scope)
    return build_actor_context(actor).get('scope')


def build_scope_from_resource(resource: Any, prefix: str) -> dict[str, Any] | None:
    """Bangun dictionary scope dari field resource berpola prefix.

    Contoh prefix yang lazim adalah `owner_scope` atau `target_scope`, sehingga
    fungsi ini akan membaca field seperti `owner_scope_type`, `owner_scope_code`,
    dan seterusnya.

    Args:
        resource (Any): Resource domain seperti `Form` atau `Submission`.
        prefix (str): Prefix nama field scope pada resource.

    Returns:
        dict[str, Any] | None: Scope hasil ekstraksi dan enrich, atau `None` bila
        resource tidak mengandung data scope.

    Example:
        >>> build_scope_from_resource(form, 'target_scope')['type']
        'division'
    """
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
    """Periksa apakah actor memiliki salah satu role yang diharapkan.

    Args:
        actor (Any): Object actor aplikasi.
        *expected_roles (str): Satu atau lebih nama role kanonis.

    Returns:
        bool: `True` jika actor memiliki minimal satu role yang cocok.

    Example:
        >>> actor_has_role(actor, 'superadmin', 'admin_lintas_bagian')
        False
    """
    roles = set(get_actor_roles(actor))
    return any(role in roles for role in expected_roles)


def actor_allows_action(actor: Any, action: str) -> bool:
    """Periksa apakah matrix policy role actor mengizinkan suatu action.

    Args:
        actor (Any): Object actor aplikasi.
        action (str): Action domain seperti `form:view` atau
            `submission:export`.

    Returns:
        bool: `True` jika ada role actor yang mengizinkan action tersebut.

    Example:
        >>> actor_allows_action(actor, 'submission:view')
        True
    """
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
    """Periksa apakah actor dan resource berada tepat pada scope yang sama.

    Returns:
        bool: `True` bila `type` dan `code` kedua scope identik.

    Example:
        >>> is_exact_scope_match({'type': 'unit', 'code': 'ki'}, {'type': 'unit', 'code': 'ki'})
        True
    """
    if not actor_scope or not resource_scope:
        return False
    return (
        actor_scope.get('type') == resource_scope.get('type')
        and actor_scope.get('code') == resource_scope.get('code')
    )


def is_actor_within_resource_scope(actor_scope: dict[str, Any] | None, resource_scope: dict[str, Any] | None) -> bool:
    """Periksa apakah actor berada di dalam jangkauan scope resource.

    Umumnya dipakai untuk menentukan apakah user boleh melihat/mengisi form
    yang menargetkan division, kanwil, atau unit tertentu.

    Returns:
        bool: `True` jika actor berada dalam cakupan resource.

    Example:
        >>> is_actor_within_resource_scope(
        ...     {'code': 'ki', 'path': ['kanwil-jabar', 'divisi-pelayanan-hukum', 'ki']},
        ...     {'code': 'divisi-pelayanan-hukum', 'type': 'division'},
        ... )
        True
    """
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
    """Periksa apakah resource berada dalam jangkauan scope actor.

    Ini berguna untuk membaca submission milik unit di bawah divisi/kanwil actor.

    Returns:
        bool: `True` jika resource masih berada di area tanggung jawab actor.

    Example:
        >>> is_resource_within_actor_scope(
        ...     {'code': 'divisi-p3h', 'path': ['kanwil-jabar', 'divisi-p3h']},
        ...     {'code': 'jdih', 'path': ['kanwil-jabar', 'divisi-p3h', 'jdih']},
        ... )
        True
    """
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
    """Periksa apakah actor dan resource masih berada pada kanwil yang sama.

    Returns:
        bool: `True` jika elemen pertama path scope sama.

    Example:
        >>> shares_same_kanwil(
        ...     {'path': ['kanwil-jabar', 'divisi-p3h']},
        ...     {'path': ['kanwil-jabar', 'bagian-umum-tata-usaha', 'keuangan']},
        ... )
        True
    """
    if not actor_scope or not resource_scope:
        return False
    actor_path = actor_scope.get('path') or []
    resource_path = resource_scope.get('path') or []
    if not actor_path or not resource_path:
        return False
    return actor_path[0] == resource_path[0]


def derive_submission_policy_key(form: Any = None, context: dict[str, Any] | None = None) -> str:
    """Turunkan policy key submission dari form atau context eksplisit.

    Aturan ini menjaga agar submission mewarisi pola akses yang masuk akal dari
    form sumbernya bila caller belum memberikan policy sendiri.

    Args:
        form (Any, optional): Instance form sumber submission.
        context (dict[str, Any] | None, optional): Context override yang boleh
            membawa `access_policy_key` eksplisit.

    Returns:
        str: Policy key submission yang akan dipakai resource baru.

    Example:
        >>> derive_submission_policy_key(context={'access_policy_key': 'submission.kanwil_audit'})
        'submission.kanwil_audit'
    """
    context = context or {}
    explicit_policy = context.get('access_policy_key')
    if explicit_policy:
        return explicit_policy

    form_policy = getattr(form, 'access_policy_key', None)
    if form_policy and form_policy.startswith('submission.'):
        return form_policy

    return FORM_TO_SUBMISSION_POLICY_MAP.get(form_policy, 'submission.unit_owned')


def can_create_form(actor: Any) -> bool:
    """Periksa apakah actor boleh membuat form baru.

    Returns:
        bool: `True` untuk actor anonim pada mode test atau actor yang punya
        action `form:create`.
    """
    if actor is None:
        return True
    return actor_allows_action(actor, 'form:create')


def can_update_form(actor: Any, form: Any) -> bool:
    """Periksa apakah actor boleh mengubah metadata/schema form.

    Args:
        actor (Any): Actor yang melakukan aksi.
        form (Any): Resource form target.

    Returns:
        bool: `True` jika matrix policy actor mengizinkan `form:update`.
    """
    if actor is None:
        return True
    if not actor_allows_action(actor, 'form:update'):
        return False
    return True


def can_archive_form(actor: Any, form: Any) -> bool:
    """Periksa apakah actor boleh mengarsipkan form.

    Returns:
        bool: `True` jika matrix policy actor mengizinkan `form:archive`.
    """
    if actor is None:
        return True
    if not actor_allows_action(actor, 'form:archive'):
        return False
    return True


def can_publish_form(actor: Any, form: Any) -> bool:
    """Periksa apakah actor boleh mempublikasikan form.

    Returns:
        bool: `True` jika matrix policy actor mengizinkan `form:publish`.
    """
    if actor is None:
        return True
    if not actor_allows_action(actor, 'form:publish'):
        return False
    return True


def can_view_form(actor: Any, form: Any) -> bool:
    """Periksa apakah actor boleh melihat form berdasarkan action dan scope.

    Returns:
        bool: `True` jika action `form:view` diizinkan dan actor masih berada
        dalam `target_scope` form.
    """
    if actor is None:
        return True
    if not actor_allows_action(actor, 'form:view'):
        return False

    actor_scope = get_actor_scope(actor)
    target_scope = build_scope_from_resource(form, 'target_scope')
    return is_actor_within_resource_scope(actor_scope, target_scope)


def can_submit_form(actor: Any, form: Any) -> bool:
    """Periksa apakah actor boleh mengirim submission untuk suatu form.

    Returns:
        bool: `True` jika action `submission:create` diizinkan dan actor berada
        dalam jangkauan `target_scope` form.
    """
    if actor is None:
        return True
    if not actor_allows_action(actor, 'submission:create'):
        return False

    actor_scope = get_actor_scope(actor)
    target_scope = build_scope_from_resource(form, 'target_scope')
    return is_actor_within_resource_scope(actor_scope, target_scope)


def can_view_submission(actor: Any, submission: Any) -> bool:
    """Periksa apakah actor boleh membaca detail submission tertentu.

    Evaluasi dilakukan berdasarkan action matrix, owner scope submission, dan
    `access_policy_key` yang menempel pada submission.

    Args:
        actor (Any): Actor yang melakukan akses.
        submission (Any): Resource submission target.

    Returns:
        bool: `True` jika policy access submission mengizinkan actor tersebut.

    Example:
        >>> can_view_submission(actor, submission)
        True
    """
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
    """Periksa apakah policy key terdaftar dalam katalog policy bootstrap.

    Args:
        policy_key (str | None): Policy key yang ingin divalidasi.

    Returns:
        bool: `True` jika policy dikenal oleh `ACCESS_POLICY_CATALOG`.

    Example:
        >>> ensure_known_policy('submission.unit_owned')
        True
    """
    if not policy_key:
        return False
    return policy_key in ACCESS_POLICY_CATALOG

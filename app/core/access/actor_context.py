"""Builder konteks actor untuk kebutuhan RBAC/ABAC ringan.

Modul ini mengubah data user mentah menjadi struktur actor-context yang lebih
stabil dipakai service, evaluator policy, dan route API. Fokusnya adalah
normalisasi role, permission, active year, dan scope organisasi.
"""

from __future__ import annotations

from typing import Any, Iterable

from .policy_catalog import BOOTSTRAP_SCOPE_REGISTRY


def _normalize_list(value: Any) -> list[str]:
    """Normalisasi scalar/iterable menjadi list string unik.

    Nilai kosong dibuang, kapitalisasi tidak dipakai untuk deduplikasi, dan
    urutan kemunculan pertama tetap dipertahankan.
    """
    if value is None:
        return []
    if isinstance(value, str):
        items = [value]
    elif isinstance(value, Iterable):
        items = list(value)
    else:
        items = [value]

    normalized = []
    seen = set()
    for item in items:
        cleaned = str(item or '').strip()
        if not cleaned:
            continue
        lowered = cleaned.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        normalized.append(cleaned)
    return normalized


def enrich_scope(scope: dict[str, Any] | None) -> dict[str, Any] | None:
    """Lengkapi scope mentah dengan metadata dari bootstrap registry.

    Jika `code` scope dikenal oleh `BOOTSTRAP_SCOPE_REGISTRY`, metadata seperti
    `type`, `name`, `path`, atau `parent_code` akan ikut diinjeksikan tanpa
    menimpa nilai eksplisit yang sudah dikirim caller.

    Args:
        scope (dict[str, Any] | None): Scope mentah, misalnya `{'code': 'ki'}`.

    Returns:
        dict[str, Any] | None: Scope yang sudah diperkaya, atau `None` bila
        input bukan dictionary valid.

    Example:
        >>> enrich_scope({'code': 'ki'})['type']
        'unit'
    """
    if not isinstance(scope, dict):
        return None

    code = scope.get('code')
    registry_scope = BOOTSTRAP_SCOPE_REGISTRY.get(code) if code else None
    merged = dict(registry_scope or {})
    merged.update({key: value for key, value in scope.items() if value not in (None, '')})

    scope_type = merged.get('type')
    if not scope_type and code and registry_scope:
        merged['type'] = registry_scope.get('type')

    return merged or None


def normalize_actor_settings(settings: Any) -> dict[str, Any]:
    """Normalisasi `settings` actor agar konsisten dipakai lintas service.

    Fungsi ini menjaga agar field penting seperti `active_year`, `scope`,
    `roles`, dan `permissions` punya bentuk yang lebih terprediksi.

    Args:
        settings (Any): Nilai mentah dari `user.settings` atau sumber serupa.

    Returns:
        dict[str, Any]: Dictionary settings yang telah dibersihkan.

    Example:
        >>> normalize_actor_settings({'active_year': '2026'})['active_year']
        2026
    """
    if not isinstance(settings, dict):
        settings = {}

    normalized: dict[str, Any] = {}

    active_year = settings.get('active_year')
    if active_year not in (None, ''):
        try:
            normalized['active_year'] = int(active_year)
        except (TypeError, ValueError):
            normalized['active_year'] = active_year

    scope = enrich_scope(settings.get('scope'))
    if scope:
        normalized['scope'] = scope

    for key in ('roles', 'access_roles', 'access_role', 'permissions'):
        if key in settings and settings.get(key) not in (None, ''):
            normalized[key] = settings.get(key)

    return normalized


def build_scope_settings(scope_type: str | None = None, scope_code: str | None = None) -> dict[str, Any] | None:
    """Bangun payload settings scope dari pasangan type dan code.

    Args:
        scope_type (str | None, optional): Jenis scope, misalnya `unit` atau
            `division`.
        scope_code (str | None, optional): Kode scope organisasi.

    Returns:
        dict[str, Any] | None: Scope hasil normalisasi, atau `None` jika input
        kosong/tidak valid.

    Example:
        >>> build_scope_settings(scope_code='ki')['code']
        'ki'
    """
    code = str(scope_code or '').strip() or None
    scope_type = str(scope_type or '').strip() or None
    if not code and not scope_type:
        return None

    scope = enrich_scope({'type': scope_type, 'code': code})
    if not scope:
        return None
    return scope


def build_actor_context(actor: Any) -> dict[str, Any]:
    """Bangun actor context standar dari object user/domain actor.

    Context ini dipakai evaluator policy agar service tidak perlu tahu detail
    struktur model user. Jika `settings.scope` belum ada, fungsi ini mencoba
    fallback ke `actor.employee.details.scope`.

    Args:
        actor (Any): Object actor, biasanya instance `User` atau object serupa.

    Returns:
        dict[str, Any]: Struktur actor context dengan key `user_id`,
        `user_uuid`, `roles`, `permissions`, `active_year`, `scope`, dan
        `settings`.

    Example:
        >>> context = build_actor_context(actor)
        >>> 'roles' in context and 'scope' in context
        True
    """
    if actor is None:
        return {
            'user_id': None,
            'user_uuid': None,
            'roles': [],
            'permissions': [],
            'active_year': None,
            'scope': None,
            'settings': {},
        }

    raw_settings = getattr(actor, 'settings', None)
    settings = normalize_actor_settings(raw_settings)

    if 'scope' not in settings:
        employee = getattr(actor, 'employee', None)
        employee_details = getattr(employee, 'details', None)
        if isinstance(employee_details, dict):
            employee_settings = normalize_actor_settings({'scope': employee_details.get('scope')})
            if employee_settings.get('scope'):
                settings['scope'] = employee_settings['scope']

    roles = _normalize_list(
        getattr(actor, 'roles', None)
        or settings.get('roles')
        or settings.get('access_roles')
        or settings.get('access_role')
    )
    permissions = _normalize_list(getattr(actor, 'permissions', None) or settings.get('permissions'))

    return {
        'user_id': getattr(actor, 'id', None),
        'user_uuid': getattr(actor, 'uuid', None),
        'roles': roles,
        'permissions': permissions,
        'active_year': settings.get('active_year'),
        'scope': settings.get('scope'),
        'settings': settings,
    }


def merge_actor_settings(
    existing_settings: Any = None,
    active_year: Any = None,
    scope_type: str | None = None,
    scope_code: str | None = None,
) -> dict[str, Any]:
    """Gabungkan patch settings actor ke payload settings yang sudah ada.

    Helper ini berguna untuk form/profile update agar perubahan tahun aktif dan
    scope actor bisa dilakukan tanpa menulis ulang semua field settings lain.

    Args:
        existing_settings (Any, optional): Settings lama actor.
        active_year (Any, optional): Tahun aktif baru. String numerik akan
            dicoba di-cast ke integer.
        scope_type (str | None, optional): Type scope baru.
        scope_code (str | None, optional): Code scope baru.

    Returns:
        dict[str, Any]: Settings actor hasil merge.

    Example:
        >>> merge_actor_settings({'active_year': 2025}, active_year='2026')['active_year']
        2026
    """
    settings = normalize_actor_settings(existing_settings)

    if active_year not in (None, ''):
        try:
            settings['active_year'] = int(active_year)
        except (TypeError, ValueError):
            settings['active_year'] = active_year
    elif active_year == '':
        settings.pop('active_year', None)

    scope = build_scope_settings(scope_type=scope_type, scope_code=scope_code)
    if scope:
        settings['scope'] = scope
    elif scope_type == '' or scope_code == '':
        settings.pop('scope', None)

    return settings

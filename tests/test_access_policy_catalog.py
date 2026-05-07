from app.core.access import (
    ACCESS_POLICY_CATALOG,
    BOOTSTRAP_SCOPE_REGISTRY,
    ORG_SCOPE_TYPES,
    POLICY_MATRIX,
)


def test_access_policy_catalog_has_expected_bootstrap_keys():
    assert 'unit' in ORG_SCOPE_TYPES
    assert 'division' in ORG_SCOPE_TYPES
    assert 'kanwil-jabar' in BOOTSTRAP_SCOPE_REGISTRY
    assert 'ki' in BOOTSTRAP_SCOPE_REGISTRY
    assert BOOTSTRAP_SCOPE_REGISTRY['ki']['parent_code'] == 'divisi-pelayanan-hukum'


def test_access_policy_catalog_covers_initial_form_and_submission_policies():
    assert 'form.admin_only_authoring' in ACCESS_POLICY_CATALOG
    assert 'form.unit_internal' in ACCESS_POLICY_CATALOG
    assert 'form.division_broadcast' in ACCESS_POLICY_CATALOG
    assert 'form.kanwil_broadcast' in ACCESS_POLICY_CATALOG
    assert 'submission.unit_owned' in ACCESS_POLICY_CATALOG
    assert 'submission.kanwil_audit' in ACCESS_POLICY_CATALOG

    assert ACCESS_POLICY_CATALOG['form.division_broadcast']['default_target_scope_type'] == 'division'
    assert 'submission:create' in ACCESS_POLICY_CATALOG['form.unit_internal']['actions']
    assert 'submission:export' in ACCESS_POLICY_CATALOG['submission.kanwil_audit']['actions']


def test_policy_matrix_maps_initial_roles_to_scopes_and_policies():
    assert POLICY_MATRIX['pegawai_unit']['scope'] == 'unit'
    assert 'submission:create' in POLICY_MATRIX['pegawai_unit']['allowed_actions']
    assert 'submission.kanwil_audit' in POLICY_MATRIX['kakanwil']['recommended_policies']
    assert 'form.admin_only_authoring' in POLICY_MATRIX['admin_lintas_bagian']['recommended_policies']
    assert POLICY_MATRIX['superadmin']['allowed_actions'] == ['*']

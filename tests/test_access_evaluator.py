from pathlib import Path
from types import SimpleNamespace

import pytest

from app.core.access import derive_submission_policy_key
from app.core.access.evaluator import (
    actor_allows_action,
    can_publish_form,
    can_submit_form,
    can_view_submission,
)


@pytest.fixture
def actor_unit_ki():
    return SimpleNamespace(
        roles=['pegawai_unit'],
        settings={
            'scope': {
                'type': 'unit',
                'code': 'ki',
                'name': 'Kekayaan Intelektual',
                'path': ['kanwil-jabar', 'divisi-pelayanan-hukum', 'ki'],
            }
        },
    )


@pytest.fixture
def actor_admin_kanwil():
    return SimpleNamespace(
        roles=['admin_lintas_bagian'],
        settings={
            'scope': {
                'type': 'kanwil',
                'code': 'kanwil-jabar',
                'name': 'Kantor Wilayah Kementerian Hukum Jawa Barat',
                'path': ['kanwil-jabar'],
            }
        },
    )


@pytest.fixture
def actor_kadiv_pelayanan_hukum():
    return SimpleNamespace(
        roles=['kepala_divisi'],
        settings={
            'scope': {
                'type': 'division',
                'code': 'divisi-pelayanan-hukum',
                'name': 'Divisi Pelayanan Hukum',
                'path': ['kanwil-jabar', 'divisi-pelayanan-hukum'],
            }
        },
    )


@pytest.fixture
def actor_unit_jdih():
    return SimpleNamespace(
        roles=['pegawai_unit'],
        settings={
            'scope': {
                'type': 'unit',
                'code': 'jdih',
                'name': 'JDIH',
                'path': ['kanwil-jabar', 'divisi-p3h', 'jdih'],
            }
        },
    )


def test_can_submit_form_allows_unit_actor_inside_target_division(actor_unit_ki):
    form = SimpleNamespace(
        target_scope_type='division',
        target_scope_code='divisi-pelayanan-hukum',
        target_scope_path=['kanwil-jabar', 'divisi-pelayanan-hukum'],
        access_policy_key='form.division_broadcast',
    )

    assert can_submit_form(actor_unit_ki, form) is True


def test_can_submit_form_rejects_actor_outside_target_scope(actor_unit_jdih):
    form = SimpleNamespace(
        target_scope_type='division',
        target_scope_code='divisi-pelayanan-hukum',
        target_scope_path=['kanwil-jabar', 'divisi-pelayanan-hukum'],
        access_policy_key='form.division_broadcast',
    )

    assert can_submit_form(actor_unit_jdih, form) is False


def test_actor_allows_action_honors_explicit_user_permissions():
    actor = SimpleNamespace(roles=['pegawai_unit'], permissions=['submission:update'])

    assert actor_allows_action(actor, 'submission:update') is True


def test_can_publish_form_allows_admin_lintas_bagian(actor_admin_kanwil):
    form = SimpleNamespace(
        owner_scope_type='unit',
        owner_scope_code='ki',
        owner_scope_path=['kanwil-jabar', 'divisi-pelayanan-hukum', 'ki'],
        access_policy_key='form.admin_only_authoring',
    )

    assert can_publish_form(actor_admin_kanwil, form) is True


def test_can_view_submission_allows_kepala_divisi_on_child_unit_submission(actor_kadiv_pelayanan_hukum):
    submission = SimpleNamespace(
        owner_scope_type='unit',
        owner_scope_code='ahu',
        owner_scope_path=['kanwil-jabar', 'divisi-pelayanan-hukum', 'ahu'],
        access_policy_key='submission.division_audit',
    )

    assert can_view_submission(actor_kadiv_pelayanan_hukum, submission) is True


def test_derive_submission_policy_key_maps_form_policy_to_submission_policy():
    form = SimpleNamespace(access_policy_key='form.kanwil_broadcast')

    assert derive_submission_policy_key(form=form, context=None) == 'submission.kanwil_audit'


@pytest.mark.parametrize(
    'path_suffix',
    [
        'id="formBuilderOwnerScopeCode"',
        'id="formBuilderTargetScopeCode"',
        'id="formBuilderAccessPolicyKey"',
    ],
)
def test_form_builder_template_contains_abac_input_controls(path_suffix):
    template_path = Path('app/templates/pages/forms/form_builder.html')
    content = template_path.read_text(encoding='utf-8')

    assert path_suffix in content


def test_form_builder_source_js_collects_abac_payload_fields():
    js_path = Path('app/src/js/pages/form-builder.js')
    content = js_path.read_text(encoding='utf-8')

    assert 'owner_scope' in content
    assert 'target_scope' in content
    assert 'access_policy_key' in content


def test_form_builder_source_js_registers_registry_consumer_preset_controls():
    js_path = Path('app/src/js/pages/form-builder.js')
    content = js_path.read_text(encoding='utf-8')

    assert 'formBuilderInsertWilayahCascadeBtn' in content
    assert 'registryConsumerPresets' in content
    assert 'insertPresetComponents' in content
    assert 'ensureLocalFormioBaseUrl' in content
    assert 'window.Formio.setBaseUrl' in content

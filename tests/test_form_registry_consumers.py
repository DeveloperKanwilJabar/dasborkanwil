from app.modules.form.registry_consumers import FormRegistryConsumerService


def test_registry_consumer_service_builds_wilayah_cascading_select_preset():
    preset = FormRegistryConsumerService().get_builder_preset('wilayah_cascading_select')

    assert preset['key'] == 'wilayah_cascading_select'
    assert preset['label'] == 'Cascading Select Wilayah'
    assert preset['registry_slug'] == 'wilayah.administratif'
    assert [component['key'] for component in preset['components']] == [
        'province_code',
        'city_regency_code',
        'district_code',
        'village_code',
    ]

    province_component = preset['components'][0]
    city_component = preset['components'][1]
    district_component = preset['components'][2]
    village_component = preset['components'][3]

    assert province_component['dataSrc'] == 'url'
    assert province_component['data']['url'].endswith('/api/v1/registry-resources/wilayah.administratif/options?admin_level=province')
    assert province_component['selectValues'] == 'data.items'
    assert province_component['valueProperty'] == 'value'
    assert province_component['template'] == '<span>{{ item.label }}</span>'

    assert city_component['refreshOn'] == 'province_code'
    assert city_component['clearOnRefresh'] is True
    assert 'admin_level=city_regency' in city_component['data']['url']
    assert 'parent_code={{ data.province_code }}' in city_component['data']['url']

    assert district_component['refreshOn'] == 'city_regency_code'
    assert district_component['clearOnRefresh'] is True
    assert 'admin_level=district' in district_component['data']['url']
    assert 'parent_code={{ data.city_regency_code }}' in district_component['data']['url']

    assert village_component['refreshOn'] == 'district_code'
    assert village_component['clearOnRefresh'] is True
    assert 'admin_level=village' in village_component['data']['url']
    assert 'parent_code={{ data.district_code }}' in village_component['data']['url']
    assert village_component['validate']['required'] is False


def test_registry_consumer_service_can_build_absolute_registry_urls_for_formio_runtime():
    preset = FormRegistryConsumerService().get_builder_preset(
        'wilayah_cascading_select',
        base_url='https://example.test',
    )

    province_component = preset['components'][0]
    city_component = preset['components'][1]

    assert province_component['data']['url'] == (
        'https://example.test/api/v1/registry-resources/'
        'wilayah.administratif/options?admin_level=province'
    )
    assert city_component['data']['url'].startswith(
        'https://example.test/api/v1/registry-resources/'
        'wilayah.administratif/options?admin_level=city_regency'
    )
    assert 'parent_code={{ data.province_code }}' in city_component['data']['url']

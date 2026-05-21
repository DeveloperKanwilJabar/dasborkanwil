import os
import uuid

import pytest

from app import create_app
from app.core.extensions import db
from app.modules.data_registry.models import DataRegistry, DataRegistryRecord, DataRegistryVersion


pytestmark = pytest.mark.skipif(
    not os.environ.get('TEST_DATABASE_URI', '').startswith('postgresql'),
    reason='TEST_DATABASE_URI PostgreSQL nyata belum diset.',
)


@pytest.fixture()
def postgres_app():
    app = create_app('testing')
    assert app.config['SQLALCHEMY_DATABASE_URI'].startswith('postgresql')

    with app.app_context():
        db.session.remove()
        db.drop_all()
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def registry_bundle(postgres_app):
    registry = DataRegistry(
        uuid=str(uuid.uuid4()),
        registry_slug='wilayah.administratif',
        registry_code='WILAYAH-ADM',
        name='Wilayah Administratif',
        registry_type='geo',
        category_key='wilayah',
        source_mode='import_file',
        data_shape='hierarchical_geo',
        status='published',
        schema_meta={'source': 'pytest'},
    )
    db.session.add(registry)
    db.session.commit()

    version = DataRegistryVersion(
        uuid=str(uuid.uuid4()),
        registry_id=registry.id,
        version_number=1,
        status='published',
        schema_json={'fields': [{'key': 'kode_wilayah'}]},
        mapping_spec={'source': 'pytest'},
        source_snapshot={'source_name': 'pytest'},
        freshness_status='fresh',
    )
    db.session.add(version)
    db.session.commit()

    return registry, version


def test_postgresql_repository_round_trip_for_registry_hierarchy(postgres_app, registry_bundle):
    from app.modules.data_registry.repositories import (
        DataRegistryRecordRepository,
        DataRegistryRepository,
        DataRegistryVersionRepository,
    )

    registry, version = registry_bundle
    registry_repository = DataRegistryRepository()
    version_repository = DataRegistryVersionRepository()
    record_repository = DataRegistryRecordRepository()

    province = DataRegistryRecord(
        uuid=str(uuid.uuid4()),
        registry_id=registry.id,
        registry_version_id=version.id,
        record_key='province:32',
        record_code='32',
        external_code='32',
        label='Jawa Barat',
        display_label='Jawa Barat',
        normalized_label='jawa barat',
        admin_level='province',
        admin_level_code='PROV',
        province_code='32',
        sort_order=1,
        is_active=True,
        source_snapshot={'source_name': 'pytest'},
        payload={'codes': {'kemendagri': {'province': '32'}}},
    )
    record_repository.save(province)

    city = DataRegistryRecord(
        uuid=str(uuid.uuid4()),
        registry_id=registry.id,
        registry_version_id=version.id,
        parent_record_id=province.id,
        record_key='city_regency:32.01',
        record_code='32.01',
        external_code='3201',
        label='Kab. Bogor',
        display_label='Kab. Bogor',
        normalized_label='kab bogor',
        admin_level='city_regency',
        admin_level_code='KABKOT',
        city_regency_kind='kabupaten',
        province_code='32',
        city_regency_code='32.01',
        sort_order=1,
        is_active=True,
        source_snapshot={'source_name': 'pytest'},
        payload={'codes': {'bps': {'city_regency': '3201'}}},
    )
    record_repository.save(city)

    fetched_registry = registry_repository.get_active_by_slug('wilayah.administratif')
    fetched_version = version_repository.get_published_version(registry.id)
    fetched_province = record_repository.get_by_code(version.id, '32')
    fetched_city = record_repository.get_by_key(version.id, 'city_regency:32.01')
    children = record_repository.list_children(version.id, province.id)
    options = record_repository.list_options(version.id, admin_level='city_regency', parent_record_id=province.id)

    assert fetched_registry.id == registry.id
    assert fetched_version.id == version.id
    assert fetched_province.payload == {'codes': {'kemendagri': {'province': '32'}}}
    assert fetched_city.external_code == '3201'
    assert fetched_city.payload == {'codes': {'bps': {'city_regency': '3201'}}}
    assert [item.record_code for item in children] == ['32.01']
    assert [item.record_code for item in options] == ['32.01']



def test_postgresql_materialization_service_persists_materialized_records(postgres_app, registry_bundle):
    from app.modules.data_registry.repositories import DataRegistryRecordRepository, DataRegistryVersionRepository
    from app.modules.data_registry.services import DataRegistryMaterializationService

    registry, version = registry_bundle
    service = DataRegistryMaterializationService()

    result = service.materialize_wilayah_rows(
        version.id,
        [
            {
                'id': '1',
                'kemendagri_provinsi_kode': '32',
                'kemendagri_kota_kode': '32.01',
                'kemendagri_kecamatan_kode': '32.01.01',
                'kemendagri_kelurahan_kode': '32.01.01.1001',
                'kemendagri_provinsi_nama': 'JAWA BARAT',
                'kemendagri_kota_nama': 'KAB. BOGOR',
                'kemendagri_kecamatan_nama': 'CIBINONG',
                'kemendagri_kelurahan_nama': 'HARAPANJAYA',
                'bps_provinsi_kode': '32.0',
                'bps_kota_kode': '3201.0',
                'bps_kecamatan_kode': '3201010.0',
                'bps_kelurahan_kode': '3201010001.0',
                'bps_provinsi_nama': 'JAWA BARAT',
                'bps_kota_nama': 'KABUPATEN BOGOR',
                'bps_kecamatan_nama': 'CIBINONG',
                'bps_kelurahan_nama': 'HARAPAN JAYA',
                'latitude': '-6.485088',
                'longitude': '106.854729',
                'kode_pos': '16913.0',
                'status_adm': '',
            }
        ],
    )

    record_repository = DataRegistryRecordRepository()
    version_repository = DataRegistryVersionRepository()

    province = record_repository.get_by_code(version.id, '32')
    city = record_repository.get_by_code(version.id, '32.01')
    district = record_repository.get_by_code(version.id, '32.01.01')
    village = record_repository.get_by_code(version.id, '32.01.01.1001')
    refreshed_version = version_repository.get_by_id(version.id)

    assert result['record_count'] == 4
    assert province is not None
    assert city.parent_record_id == province.id
    assert district.parent_record_id == city.id
    assert village.parent_record_id == district.id
    assert village.external_code == '3201010001'
    assert village.payload['postal_code'] == '16913'
    assert village.payload['source_labels']['bps']['village'] == 'HARAPAN JAYA'
    assert village.source_snapshot['source_row']['kemendagri_kelurahan_kode'] == '32.01.01.1001'
    assert refreshed_version.materialized_watermark
    assert refreshed_version.freshness_status == 'fresh'

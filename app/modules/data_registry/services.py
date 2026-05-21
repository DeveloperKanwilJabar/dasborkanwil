import hashlib
import json
import re
import uuid
from decimal import Decimal

from app.core.extensions import db
from app.core.services.base import BaseService
from app.core.utils import now_utc

from .models import DataRegistry, DataRegistryRecord, DataRegistryVersion
from .repositories import (
    DataRegistryRecordRepository,
    DataRegistryRepository,
    DataRegistryVersionRepository,
)


class DataRegistryService(BaseService):
    def __init__(self, registry_repository=None, version_service=None):
        super().__init__(repository=registry_repository or DataRegistryRepository())
        self.version_service = version_service or DataRegistryVersionService()

    def create_registry(self, data, actor=None):
        registry_slug = data.get('registry_slug')
        name = data.get('name')

        if not registry_slug:
            raise ValueError('Registry slug wajib diisi.')
        if not name:
            raise ValueError('Nama registry wajib diisi.')
        if self.repository.get_by_slug(registry_slug):
            raise ValueError('Registry slug sudah digunakan.')

        registry_code = data.get('registry_code')
        if registry_code and self._registry_code_exists(registry_code):
            raise ValueError('Registry code sudah digunakan.')

        registry = DataRegistry(
            uuid=str(uuid.uuid4()),
            registry_slug=registry_slug,
            registry_code=registry_code,
            name=name,
            description=data.get('description'),
            registry_type=data.get('registry_type', 'geo'),
            category_key=data.get('category_key', 'wilayah'),
            source_mode=data.get('source_mode', 'import_file'),
            data_shape=data.get('data_shape', 'hierarchical_geo'),
            is_year_scoped=data.get('is_year_scoped', False),
            status=data.get('status', 'draft'),
            schema_meta=data.get('schema_meta') or {},
        )
        self._apply_actor_audit(registry, actor, action='create')

        try:
            registry = self.repository.save(registry)
            draft_version = None
            initial_schema = data.get('schema_json')
            if initial_schema is not None:
                draft_version = self.version_service.create_draft_version(
                    registry_id=registry.id,
                    schema_json=initial_schema,
                    mapping_spec=data.get('mapping_spec'),
                    source_snapshot=data.get('source_snapshot'),
                    actor=actor,
                )
            return {
                'registry': registry,
                'draft_version': draft_version,
            }
        except Exception:
            db.session.rollback()
            raise

    def publish_registry(self, registry_id, version_id=None, actor=None):
        registry = self.repository.get_by_id(registry_id)
        if not registry:
            raise ValueError('Registry tidak ditemukan.')

        target_version_id = version_id
        if target_version_id is None:
            draft_version = self.version_service.repository.get_draft_version(registry_id)
            if not draft_version:
                raise ValueError('Draft version registry tidak ditemukan.')
            target_version_id = draft_version.id

        published_version = self.version_service.publish_version(target_version_id, actor=actor)
        return {
            'registry': registry,
            'published_version': published_version,
        }

    def get_registry_detail(self, registry_id):
        return self.repository.get_by_id(registry_id)

    def _registry_code_exists(self, registry_code):
        matches = self.repository.find_by(registry_code=registry_code)
        return bool(matches)

    def _apply_actor_audit(self, obj, actor=None, action='create'):
        if not actor:
            return obj

        actor_id = getattr(actor, 'id', None)
        actor_uuid = getattr(actor, 'uuid', None)

        if action == 'create':
            obj.created_by = actor_id
            obj.created_by_uuid = actor_uuid
        obj.updated_by = actor_id
        obj.updated_by_uuid = actor_uuid
        return obj


class DataRegistryVersionService(BaseService):
    def __init__(self, version_repository=None, registry_repository=None):
        super().__init__(repository=version_repository or DataRegistryVersionRepository())
        self.registry_repository = registry_repository or DataRegistryRepository()

    def create_draft_version(
        self,
        registry_id,
        schema_json,
        mapping_spec=None,
        source_snapshot=None,
        actor=None,
        source_version_id=None,
    ):
        registry = self.registry_repository.get_by_id(registry_id)
        if not registry:
            raise ValueError('Registry tidak ditemukan.')

        source_version = None
        if source_version_id is not None:
            source_version = self.repository.get_by_id(source_version_id)
            if not source_version:
                raise ValueError('Source version registry tidak ditemukan.')
            if source_version.registry_id != registry_id:
                raise ValueError('Source version tidak sesuai dengan registry.')
            if schema_json is None:
                schema_json = source_version.schema_json
            if mapping_spec is None:
                mapping_spec = source_version.mapping_spec
            if source_snapshot is None:
                source_snapshot = source_version.source_snapshot

        if not isinstance(schema_json, dict):
            raise ValueError('Schema registry wajib berupa object/dict.')

        draft_version = DataRegistryVersion(
            uuid=str(uuid.uuid4()),
            registry_id=registry_id,
            version_number=self.repository.get_next_version_number(registry_id),
            status='draft',
            schema_json=schema_json,
            mapping_spec=mapping_spec or {},
            source_snapshot=source_snapshot or {},
            publish_notes=(
                f'Cloned from version {source_version.version_number}' if source_version else None
            ),
            freshness_status='unknown',
        )
        self._apply_actor_audit(draft_version, actor, action='create')
        return self.repository.save(draft_version)

    def publish_version(self, version_id, actor=None):
        version = self.repository.get_by_id(version_id)
        if not version:
            raise ValueError('Registry version tidak ditemukan.')
        if version.status != 'draft':
            raise ValueError('Hanya draft version registry yang boleh dipublish.')

        self._validate_schema(version.schema_json)
        self.repository.archive_published_others(version.registry_id, except_version_id=version.id)
        version.status = 'published'
        version.published_at = now_utc()
        version.freshness_status = 'fresh'
        self._apply_actor_audit(version, actor, action='update')
        saved_version = self.repository.save(version)

        registry = self.registry_repository.get_by_id(version.registry_id)
        if registry:
            registry.status = 'published'
            self._apply_actor_audit(registry, actor, action='update')
            self.registry_repository.save(registry)

        return saved_version

    def get_published_version(self, registry_id):
        return self.repository.get_published_version(registry_id)

    def _validate_schema(self, schema_json):
        if not isinstance(schema_json, dict):
            raise ValueError('Schema registry wajib berupa object/dict.')
        if 'fields' not in schema_json:
            raise ValueError('Schema registry wajib memiliki key fields.')
        return True

    def _apply_actor_audit(self, obj, actor=None, action='create'):
        if not actor:
            return obj

        actor_id = getattr(actor, 'id', None)
        actor_uuid = getattr(actor, 'uuid', None)

        if action == 'create':
            obj.created_by = actor_id
            obj.created_by_uuid = actor_uuid
        obj.updated_by = actor_id
        obj.updated_by_uuid = actor_uuid
        return obj


class DataRegistryQueryService:
    def __init__(self, registry_repository=None, version_repository=None, record_repository=None):
        self.registry_repository = registry_repository or DataRegistryRepository()
        self.version_repository = version_repository or DataRegistryVersionRepository()
        self.record_repository = record_repository or DataRegistryRecordRepository()

    def get_option_list(
        self,
        registry_slug,
        version_number=None,
        admin_level=None,
        parent_record_id=None,
        parent_code=None,
        q=None,
        limit=100,
    ):
        registry, version = self._resolve_registry_and_version(registry_slug, version_number=version_number)
        resolved_parent_id = self._resolve_parent_record_id(version.id, parent_record_id, parent_code)
        records = self.record_repository.list_options(
            version.id,
            admin_level=admin_level,
            parent_record_id=resolved_parent_id,
            q=q,
            limit=limit,
        )
        return {
            'registry': registry,
            'version': version,
            'items': [self._serialize_option_item(record) for record in self._active_records(records)],
        }

    def get_lookup(self, registry_slug, record_key=None, record_code=None, version_number=None):
        if not record_key and not record_code:
            raise ValueError('record_key atau record_code wajib diisi.')

        registry, version = self._resolve_registry_and_version(registry_slug, version_number=version_number)
        record = None
        if record_key:
            record = self.record_repository.get_by_key(version.id, record_key)
        elif record_code:
            record = self.record_repository.get_by_code(version.id, record_code)

        if not record or not getattr(record, 'is_active', True):
            raise ValueError('Record registry tidak ditemukan.')

        return {
            'registry': registry,
            'version': version,
            'record': self._serialize_record(record),
        }

    def get_children(self, registry_slug, parent_record_id=None, parent_code=None, admin_level=None, version_number=None):
        if parent_record_id is None and not parent_code:
            raise ValueError('parent_record_id atau parent_code wajib diisi.')

        registry, version = self._resolve_registry_and_version(registry_slug, version_number=version_number)
        resolved_parent_id = self._resolve_parent_record_id(version.id, parent_record_id, parent_code)
        records = self.record_repository.list_children(version.id, resolved_parent_id)
        if admin_level:
            records = [record for record in records if record.admin_level == admin_level]

        return {
            'registry': registry,
            'version': version,
            'items': [self._serialize_tree_node(record, children=[]) for record in self._active_records(records)],
        }

    def get_tree(self, registry_slug, root_level='province', max_depth=4, version_number=None):
        if max_depth < 1:
            raise ValueError('max_depth minimal 1.')

        registry, version = self._resolve_registry_and_version(registry_slug, version_number=version_number)
        roots = self._active_records(self.record_repository.list_by_level(version.id, root_level, parent_record_id=None))
        return {
            'registry': registry,
            'version': version,
            'items': [self._build_tree_node(version.id, record, current_depth=1, max_depth=max_depth) for record in roots],
        }

    def get_feature_collection(self, registry_slug, admin_level=None, parent_code=None, version_number=None):
        registry, version = self._resolve_registry_and_version(registry_slug, version_number=version_number)
        records = self._active_records(
            self.record_repository.list_feature_collection_records(version.id, admin_level=admin_level)
        )

        if parent_code:
            parent = self.record_repository.get_by_code(version.id, parent_code)
            if not parent:
                raise ValueError('Parent record tidak ditemukan.')
            records = [record for record in records if record.parent_record_id == parent.id]

        features = []
        for record in records:
            geometry = self._build_feature_geometry(record)
            if not geometry:
                continue
            features.append(
                {
                    'type': 'Feature',
                    'geometry': geometry,
                    'properties': self._serialize_feature_properties(record),
                }
            )

        return {
            'type': 'FeatureCollection',
            'features': features,
        }

    def _resolve_registry_and_version(self, registry_slug, version_number=None):
        registry = self.registry_repository.get_active_by_slug(registry_slug)
        if not registry:
            raise ValueError('Registry tidak ditemukan.')

        if version_number is None:
            version = self.version_repository.get_published_version(registry.id)
            if not version:
                raise ValueError('Published version registry tidak ditemukan.')
            return registry, version

        versions = self.version_repository.list_versions(registry.id)
        version = next((item for item in versions if item.version_number == version_number), None)
        if not version:
            raise ValueError('Registry version tidak ditemukan.')
        if version.status != 'published':
            raise ValueError('Hanya published version registry yang boleh dikonsumsi.')
        return registry, version

    def _resolve_parent_record_id(self, registry_version_id, parent_record_id=None, parent_code=None):
        if parent_record_id is not None:
            return parent_record_id
        if not parent_code:
            return None

        parent_record = self.record_repository.get_by_code(registry_version_id, parent_code)
        if not parent_record:
            raise ValueError('Parent record tidak ditemukan.')
        return parent_record.id

    def _active_records(self, records):
        return [record for record in records if getattr(record, 'is_active', True)]

    def _serialize_option_item(self, record):
        return {
            'label': getattr(record, 'display_label', None) or record.label,
            'value': record.record_code,
            'meta': {
                'record_key': record.record_key,
                'record_code': record.record_code,
                'admin_level': record.admin_level,
                'parent_record_id': record.parent_record_id,
            },
        }

    def _serialize_record(self, record):
        return {
            'id': record.id,
            'record_key': record.record_key,
            'record_code': record.record_code,
            'label': record.label,
            'display_label': getattr(record, 'display_label', None) or record.label,
            'admin_level': record.admin_level,
            'parent_record_id': record.parent_record_id,
            'centroid': self._serialize_centroid(record),
            'payload': getattr(record, 'payload', None) or {},
        }

    def _serialize_tree_node(self, record, children=None):
        node = self._serialize_record(record)
        node['children'] = children or []
        return node

    def _build_tree_node(self, registry_version_id, record, current_depth, max_depth):
        if current_depth >= max_depth:
            return self._serialize_tree_node(record, children=[])

        children = self._active_records(self.record_repository.list_children(registry_version_id, record.id))
        return self._serialize_tree_node(
            record,
            children=[
                self._build_tree_node(registry_version_id, child, current_depth + 1, max_depth)
                for child in children
            ],
        )

    def _serialize_feature_properties(self, record):
        return {
            'id': record.id,
            'record_key': record.record_key,
            'record_code': record.record_code,
            'label': record.label,
            'display_label': getattr(record, 'display_label', None) or record.label,
            'admin_level': record.admin_level,
            'parent_record_id': record.parent_record_id,
        }

    def _build_feature_geometry(self, record):
        geometry_json = getattr(record, 'geometry_json', None)
        if geometry_json:
            return geometry_json

        centroid = self._serialize_centroid(record)
        if centroid:
            return {
                'type': 'Point',
                'coordinates': [centroid['lng'], centroid['lat']],
            }
        return None

    def _serialize_centroid(self, record):
        lat = self._to_float(getattr(record, 'centroid_lat', None))
        lng = self._to_float(getattr(record, 'centroid_lng', None))
        if lat is None or lng is None:
            return None
        return {
            'lat': lat,
            'lng': lng,
        }

    def _to_float(self, value):
        if value is None:
            return None
        if isinstance(value, Decimal):
            return float(value)
        return float(value)


class DataRegistryMaterializationService:
    LEVEL_META = {
        'province': {
            'admin_level_code': 'PROV',
            'record_key_prefix': 'province',
        },
        'city_regency': {
            'admin_level_code': 'KABKOT',
            'record_key_prefix': 'city_regency',
        },
        'district': {
            'admin_level_code': 'KEC',
            'record_key_prefix': 'district',
        },
        'village': {
            'admin_level_code': 'KEL',
            'record_key_prefix': 'village',
        },
    }

    def __init__(self, registry_repository=None, version_repository=None, record_repository=None):
        self.registry_repository = registry_repository or DataRegistryRepository()
        self.version_repository = version_repository or DataRegistryVersionRepository()
        self.record_repository = record_repository or DataRegistryRecordRepository()

    def materialize_wilayah_rows(self, registry_version_id, source_rows, actor=None):
        version = self.version_repository.get_by_id(registry_version_id)
        if not version:
            raise ValueError('Registry version tidak ditemukan.')

        registry = self.registry_repository.get_by_id(version.registry_id)
        if not registry:
            raise ValueError('Registry tidak ditemukan.')

        rows = list(source_rows or [])
        self.record_repository.delete_by_registry_version(registry_version_id)
        duplicate_external_codes = self._collect_duplicate_external_codes(rows)

        records_by_key = {}
        row_hashes = []
        sort_orders = {
            'province': 0,
            'city_regency': 0,
            'district': 0,
            'village': 0,
        }

        for row_number, raw_row in enumerate(rows, start=1):
            row = self._normalize_source_row(raw_row)
            row_hash = self._build_row_hash(row)
            row_hashes.append(row_hash)

            province = self._get_or_create_record(
                records_by_key=records_by_key,
                level='province',
                registry=registry,
                version=version,
                parent=None,
                row=row,
                row_number=row_number,
                row_hash=row_hash,
                sort_orders=sort_orders,
                duplicate_external_codes=duplicate_external_codes,
                actor=actor,
            )
            city = self._get_or_create_record(
                records_by_key=records_by_key,
                level='city_regency',
                registry=registry,
                version=version,
                parent=province,
                row=row,
                row_number=row_number,
                row_hash=row_hash,
                sort_orders=sort_orders,
                duplicate_external_codes=duplicate_external_codes,
                actor=actor,
            )
            district = self._get_or_create_record(
                records_by_key=records_by_key,
                level='district',
                registry=registry,
                version=version,
                parent=city,
                row=row,
                row_number=row_number,
                row_hash=row_hash,
                sort_orders=sort_orders,
                duplicate_external_codes=duplicate_external_codes,
                actor=actor,
            )
            self._get_or_create_record(
                records_by_key=records_by_key,
                level='village',
                registry=registry,
                version=version,
                parent=district,
                row=row,
                row_number=row_number,
                row_hash=row_hash,
                sort_orders=sort_orders,
                duplicate_external_codes=duplicate_external_codes,
                actor=actor,
            )

        version.materialized_watermark = f'rows:{len(rows)}:{now_utc().isoformat()}'
        version.freshness_signature = self._build_freshness_signature(row_hashes)
        version.freshness_status = 'fresh'
        self._apply_actor_audit(version, actor, action='update')
        self.version_repository.save(version)

        return {
            'registry': registry,
            'version': version,
            'record_count': len(records_by_key),
            'source_row_count': len(rows),
        }

    def _get_or_create_record(
        self,
        *,
        records_by_key,
        level,
        registry,
        version,
        parent,
        row,
        row_number,
        row_hash,
        sort_orders,
        duplicate_external_codes,
        actor,
    ):
        record_code = row['codes']['kemendagri'][level]
        cache_key = (level, record_code)
        if cache_key in records_by_key:
            return records_by_key[cache_key]

        sort_orders[level] += 1
        level_meta = self.LEVEL_META[level]
        record = DataRegistryRecord(
            uuid=str(uuid.uuid4()),
            registry_id=registry.id,
            registry_version_id=version.id,
            parent_record_id=getattr(parent, 'id', None),
            record_key=f"{level_meta['record_key_prefix']}:{record_code}",
            record_code=record_code,
            external_code=self._resolve_external_code(level, row, duplicate_external_codes),
            label=self._humanize_label(row['labels']['kemendagri'][level]),
            display_label=self._humanize_label(row['labels']['kemendagri'][level]),
            normalized_label=self._normalize_label(row['labels']['kemendagri'][level]),
            admin_level=level,
            admin_level_code=level_meta['admin_level_code'],
            city_regency_kind=self._infer_city_regency_kind(row) if level == 'city_regency' else None,
            province_code=row['codes']['kemendagri']['province'],
            city_regency_code=row['codes']['kemendagri']['city_regency'] if level in {'city_regency', 'district', 'village'} else None,
            district_code=row['codes']['kemendagri']['district'] if level in {'district', 'village'} else None,
            village_code=row['codes']['kemendagri']['village'] if level == 'village' else None,
            village_adm_status=self._infer_village_adm_status(row['codes']['kemendagri']['village']) if level == 'village' else None,
            sort_order=sort_orders[level],
            is_active=True,
            centroid_lat=self._to_decimal(row['latitude']) if level == 'village' else None,
            centroid_lng=self._to_decimal(row['longitude']) if level == 'village' else None,
            source_row_number=row_number,
            source_row_hash=row_hash,
            source_snapshot={
                'source_name': 'diskominfo-jabar',
                'source_row': row['raw'],
                'normalized_codes': row['codes'],
            },
            payload={
                'codes': row['codes'],
                'source_labels': row['labels'],
                'postal_code': row['postal_code'],
                'administrative_status': row['administrative_status'],
                'import_row_id': row['import_row_id'],
            },
        )
        self._apply_actor_audit(record, actor, action='create')
        saved_record = self.record_repository.save(record)
        records_by_key[cache_key] = saved_record
        return saved_record

    def _collect_duplicate_external_codes(self, source_rows):
        mappings = {}
        for raw_row in source_rows:
            normalized = self._normalize_source_row(raw_row)
            for level, external_code in (normalized.get('codes') or {}).get('bps', {}).items():
                record_code = (normalized.get('codes') or {}).get('kemendagri', {}).get(level)
                if not external_code or not record_code:
                    continue
                mappings.setdefault((level, external_code), set()).add(record_code)
        return {key for key, record_codes in mappings.items() if len(record_codes) > 1}

    def _resolve_external_code(self, level, row, duplicate_external_codes):
        external_code = row['codes']['bps'][level]
        if not external_code:
            return None
        if (level, external_code) in (duplicate_external_codes or set()):
            return None
        return external_code

    def _normalize_source_row(self, row):
        raw = dict(row or {})
        codes = {
            'kemendagri': {
                'province': self._normalize_code(raw.get('kemendagri_provinsi_kode')),
                'city_regency': self._normalize_code(raw.get('kemendagri_kota_kode')),
                'district': self._normalize_code(raw.get('kemendagri_kecamatan_kode')),
                'village': self._normalize_code(raw.get('kemendagri_kelurahan_kode')),
            },
            'bps': {
                'province': self._normalize_code(raw.get('bps_provinsi_kode')),
                'city_regency': self._normalize_code(raw.get('bps_kota_kode')),
                'district': self._normalize_code(raw.get('bps_kecamatan_kode')),
                'village': self._normalize_code(raw.get('bps_kelurahan_kode')),
            },
        }
        labels = {
            'kemendagri': {
                'province': self._normalize_text(raw.get('kemendagri_provinsi_nama')),
                'city_regency': self._normalize_text(raw.get('kemendagri_kota_nama')),
                'district': self._normalize_text(raw.get('kemendagri_kecamatan_nama')),
                'village': self._normalize_text(raw.get('kemendagri_kelurahan_nama')),
            },
            'bps': {
                'province': self._normalize_text(raw.get('bps_provinsi_nama')),
                'city_regency': self._normalize_text(raw.get('bps_kota_nama')),
                'district': self._normalize_text(raw.get('bps_kecamatan_nama')),
                'village': self._normalize_text(raw.get('bps_kelurahan_nama')),
            },
        }
        return {
            'raw': raw,
            'import_row_id': self._normalize_text(raw.get('id')),
            'codes': codes,
            'labels': labels,
            'postal_code': self._normalize_code(raw.get('kode_pos')),
            'administrative_status': self._normalize_text(raw.get('status_adm')),
            'latitude': self._normalize_text(raw.get('latitude')),
            'longitude': self._normalize_text(raw.get('longitude')),
        }

    def _normalize_code(self, value):
        text = self._normalize_text(value)
        if text is None:
            return None
        if re.fullmatch(r'\d+\.0+', text):
            return text.split('.')[0]
        return text

    def _normalize_text(self, value):
        if value is None:
            return None
        text = str(value).strip()
        if not text:
            return None
        return re.sub(r'\s+', ' ', text)

    def _normalize_label(self, value):
        text = self._normalize_text(value)
        if text is None:
            return None
        return self._humanize_label(text).lower()

    def _humanize_label(self, value):
        text = self._normalize_text(value)
        if text is None:
            return None
        return ' '.join(part.capitalize() for part in text.lower().split(' '))

    def _infer_city_regency_kind(self, row):
        label = row['labels']['kemendagri']['city_regency']
        normalized = (label or '').lower()
        if normalized.startswith('kota'):
            return 'kota'
        return 'kabupaten'

    def _infer_village_adm_status(self, village_code):
        if not village_code:
            return None
        tail = village_code.split('.')[-1]
        if tail.startswith('1'):
            return 'kelurahan'
        if tail.startswith('2'):
            return 'desa'
        return None

    def _build_row_hash(self, row):
        payload = {
            'codes': row['codes'],
            'labels': row['labels'],
            'postal_code': row['postal_code'],
            'administrative_status': row['administrative_status'],
            'latitude': row['latitude'],
            'longitude': row['longitude'],
            'import_row_id': row['import_row_id'],
        }
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        return hashlib.sha256(encoded.encode('utf-8')).hexdigest()

    def _build_freshness_signature(self, row_hashes):
        encoded = json.dumps(sorted(row_hashes), ensure_ascii=False)
        return hashlib.sha256(encoded.encode('utf-8')).hexdigest()

    def _to_decimal(self, value):
        text = self._normalize_text(value)
        if text is None:
            return None
        return Decimal(text)

    def _apply_actor_audit(self, obj, actor=None, action='create'):
        if not actor:
            return obj

        actor_id = getattr(actor, 'id', None)
        actor_uuid = getattr(actor, 'uuid', None)

        if action == 'create':
            obj.created_by = actor_id
            obj.created_by_uuid = actor_uuid
        obj.updated_by = actor_id
        obj.updated_by_uuid = actor_uuid
        return obj

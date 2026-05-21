from app.core.extensions import db
from app.core.repositories.base import BaseRepository

from .models import DataRegistry, DataRegistryRecord, DataRegistryVersion


class DataRegistryRepository(BaseRepository):
    def __init__(self):
        super().__init__(model=DataRegistry)

    def get_by_slug(self, slug):
        return self.find_one_by(registry_slug=slug)

    def get_active_by_slug(self, slug):
        return self.model.query.filter(
            DataRegistry.registry_slug == slug,
            DataRegistry.status.in_(['draft', 'published']),
            DataRegistry.deleted_at == None,
        ).first()

    def list_by_status(self, status):
        return self.find_by(status=status)


class DataRegistryVersionRepository(BaseRepository):
    def __init__(self):
        super().__init__(model=DataRegistryVersion)

    def get_draft_version(self, registry_id):
        return self.model.query.filter(
            DataRegistryVersion.registry_id == registry_id,
            DataRegistryVersion.status == 'draft',
            DataRegistryVersion.deleted_at == None,
        ).order_by(DataRegistryVersion.version_number.desc()).first()

    def get_published_version(self, registry_id):
        return self.model.query.filter(
            DataRegistryVersion.registry_id == registry_id,
            DataRegistryVersion.status == 'published',
            DataRegistryVersion.deleted_at == None,
        ).order_by(DataRegistryVersion.version_number.desc()).first()

    def get_next_version_number(self, registry_id):
        latest = self.model.query.filter(
            DataRegistryVersion.registry_id == registry_id,
            DataRegistryVersion.deleted_at == None,
        ).order_by(DataRegistryVersion.version_number.desc()).first()
        return 1 if not latest else latest.version_number + 1

    def list_versions(self, registry_id, include_deleted=False):
        query = self.model.query.filter(DataRegistryVersion.registry_id == registry_id)
        if not include_deleted:
            query = query.filter(DataRegistryVersion.deleted_at == None)
        return query.order_by(DataRegistryVersion.version_number.desc()).all()

    def archive_published_others(self, registry_id, except_version_id=None):
        query = self.model.query.filter(
            DataRegistryVersion.registry_id == registry_id,
            DataRegistryVersion.status == 'published',
        )
        if except_version_id is not None:
            query = query.filter(DataRegistryVersion.id != except_version_id)

        versions = query.all()
        for version in versions:
            version.status = 'archived'
        return versions


class DataRegistryRecordRepository(BaseRepository):
    def __init__(self):
        super().__init__(model=DataRegistryRecord)

    def get_by_key(self, registry_version_id, record_key):
        return self.model.query.filter(
            DataRegistryRecord.registry_version_id == registry_version_id,
            DataRegistryRecord.record_key == record_key,
            DataRegistryRecord.deleted_at == None,
        ).first()

    def get_by_code(self, registry_version_id, record_code):
        return self.model.query.filter(
            DataRegistryRecord.registry_version_id == registry_version_id,
            DataRegistryRecord.record_code == record_code,
            DataRegistryRecord.deleted_at == None,
        ).first()

    def list_children(self, registry_version_id, parent_record_id):
        return self.model.query.filter(
            DataRegistryRecord.registry_version_id == registry_version_id,
            DataRegistryRecord.parent_record_id == parent_record_id,
            DataRegistryRecord.deleted_at == None,
        ).order_by(DataRegistryRecord.sort_order.asc(), DataRegistryRecord.label.asc()).all()

    def list_by_level(self, registry_version_id, admin_level, parent_record_id=None):
        query = self.model.query.filter(
            DataRegistryRecord.registry_version_id == registry_version_id,
            DataRegistryRecord.admin_level == admin_level,
            DataRegistryRecord.deleted_at == None,
        )
        if parent_record_id is not None:
            query = query.filter(DataRegistryRecord.parent_record_id == parent_record_id)
        return query.order_by(DataRegistryRecord.sort_order.asc(), DataRegistryRecord.label.asc()).all()

    def list_options(self, registry_version_id, admin_level=None, parent_record_id=None, q=None, limit=100):
        query = self.model.query.filter(
            DataRegistryRecord.registry_version_id == registry_version_id,
            DataRegistryRecord.deleted_at == None,
        )
        if admin_level is not None:
            query = query.filter(DataRegistryRecord.admin_level == admin_level)
        if parent_record_id is not None:
            query = query.filter(DataRegistryRecord.parent_record_id == parent_record_id)
        if q:
            query = query.filter(DataRegistryRecord.label.ilike(f'%{q}%'))
        return query.order_by(DataRegistryRecord.sort_order.asc(), DataRegistryRecord.label.asc()).limit(limit).all()

    def list_feature_collection_records(self, registry_version_id, admin_level=None):
        query = self.model.query.filter(
            DataRegistryRecord.registry_version_id == registry_version_id,
            DataRegistryRecord.deleted_at == None,
        )
        if admin_level is not None:
            query = query.filter(DataRegistryRecord.admin_level == admin_level)
        return query.order_by(DataRegistryRecord.sort_order.asc(), DataRegistryRecord.label.asc()).all()

    def delete_by_registry_version(self, registry_version_id):
        self.model.query.filter(
            DataRegistryRecord.registry_version_id == registry_version_id,
        ).delete(synchronize_session=False)
        db.session.commit()
        return True

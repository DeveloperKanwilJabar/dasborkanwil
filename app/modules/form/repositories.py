from app.core.extensions import db
from app.core.repositories.base import BaseRepository

from .models import Form, FormVersion


class FormRepository(BaseRepository):
    def __init__(self):
        super().__init__(model=Form)

    def exists_code(self, code, exclude_form_id=None):
        query = self.model.query.filter(Form.code == code)
        if exclude_form_id is not None:
            query = query.filter(Form.id != exclude_form_id)
        return db.session.query(query.exists()).scalar()

    def exists_slug(self, slug, exclude_form_id=None):
        query = self.model.query.filter(Form.slug == slug)
        if exclude_form_id is not None:
            query = query.filter(Form.id != exclude_form_id)
        return db.session.query(query.exists()).scalar()

    def get_by_slug(self, slug):
        return self.find_one_by(slug=slug)

    def get_active_by_slug(self, slug):
        return self.model.query.filter(
            Form.slug == slug,
            Form.status.in_(['draft', 'published']),
            Form.deleted_at == None,
        ).first()

    def list_by_status(self, status):
        return self.find_by(status=status)


class FormVersionRepository(BaseRepository):
    def __init__(self):
        super().__init__(model=FormVersion)

    def get_latest_version(self, form_id):
        return self.model.query.filter(
            FormVersion.form_id == form_id,
            FormVersion.deleted_at == None,
        ).order_by(FormVersion.version_number.desc()).first()

    def get_next_version_number(self, form_id):
        latest_version = self.get_latest_version(form_id)
        if not latest_version:
            return 1
        return latest_version.version_number + 1

    def get_published_version(self, form_id):
        return self.model.query.filter(
            FormVersion.form_id == form_id,
            FormVersion.is_published == True,
            FormVersion.status == 'published',
            FormVersion.deleted_at == None,
        ).order_by(FormVersion.version_number.desc()).first()

    def get_draft_version(self, form_id):
        return self.model.query.filter(
            FormVersion.form_id == form_id,
            FormVersion.status == 'draft',
            FormVersion.is_published == False,
            FormVersion.deleted_at == None,
        ).order_by(FormVersion.version_number.desc()).first()

    def list_versions(self, form_id, include_deleted=False):
        query = self.model.query.filter(FormVersion.form_id == form_id)
        if not include_deleted:
            query = query.filter(FormVersion.deleted_at == None)
        return query.order_by(FormVersion.version_number.desc()).all()

    def unpublish_others(self, form_id, except_version_id=None):
        query = self.model.query.filter(
            FormVersion.form_id == form_id,
            FormVersion.is_published == True,
        )
        if except_version_id is not None:
            query = query.filter(FormVersion.id != except_version_id)

        versions = query.all()
        for version in versions:
            version.is_published = False
            if version.status == 'published':
                version.status = 'archived'
        return versions

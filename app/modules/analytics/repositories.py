from sqlalchemy import func

from app.core.extensions import db
from app.core.repositories.base import BaseRepository

from .models import (
    AnalyticsIndicatorDefinition,
    AnalyticsIndicatorProgressEntry,
    AnalyticsIndicatorResult,
    AnalyticsIndicatorVersion,
    AnalyticsReportDefinition,
    AnalyticsReportVersion,
    AnalyticsReportVersionIndicator,
)


class AnalyticsReportDefinitionRepository(BaseRepository):
    def __init__(self):
        super().__init__(model=AnalyticsReportDefinition)

    def get_by_key(self, report_key):
        return self.find_one_by(report_key=report_key)

    def list_by_status(self, status):
        return self.find_by(status=status)


class AnalyticsReportVersionRepository(BaseRepository):
    def __init__(self):
        super().__init__(model=AnalyticsReportVersion)

    def get_draft_version(self, report_definition_id):
        return self.model.query.filter(
            AnalyticsReportVersion.report_definition_id == report_definition_id,
            AnalyticsReportVersion.status == AnalyticsReportVersion.STATUS_DRAFT,
            AnalyticsReportVersion.is_current_draft == True,
            AnalyticsReportVersion.deleted_at == None,
        ).order_by(AnalyticsReportVersion.version_number.desc()).first()

    def get_published_version(self, report_definition_id):
        return self.model.query.filter(
            AnalyticsReportVersion.report_definition_id == report_definition_id,
            AnalyticsReportVersion.status == AnalyticsReportVersion.STATUS_PUBLISHED,
            AnalyticsReportVersion.is_current_published == True,
            AnalyticsReportVersion.deleted_at == None,
        ).order_by(AnalyticsReportVersion.version_number.desc()).first()

    def get_next_version_number(self, report_definition_id):
        latest_version_number = self.model.query.filter(
            AnalyticsReportVersion.report_definition_id == report_definition_id,
            AnalyticsReportVersion.deleted_at == None,
        ).with_entities(func.max(AnalyticsReportVersion.version_number)).scalar()
        return (latest_version_number or 0) + 1

    def list_versions(self, report_definition_id):
        return self.model.query.filter(
            AnalyticsReportVersion.report_definition_id == report_definition_id,
            AnalyticsReportVersion.deleted_at == None,
        ).order_by(AnalyticsReportVersion.version_number.desc()).all()

    def archive_published_others(self, report_definition_id, except_version_id=None):
        query = self.model.query.filter(
            AnalyticsReportVersion.report_definition_id == report_definition_id,
            AnalyticsReportVersion.is_current_published == True,
            AnalyticsReportVersion.deleted_at == None,
        )
        if except_version_id is not None:
            query = query.filter(AnalyticsReportVersion.id != except_version_id)

        versions = query.all()
        for version in versions:
            version.is_current_published = False
            version.is_current_draft = False
            if version.status == AnalyticsReportVersion.STATUS_PUBLISHED:
                version.status = AnalyticsReportVersion.STATUS_ARCHIVED
        return versions


class AnalyticsIndicatorDefinitionRepository(BaseRepository):
    def __init__(self):
        super().__init__(model=AnalyticsIndicatorDefinition)

    def get_by_key(self, indicator_key):
        return self.find_one_by(indicator_key=indicator_key)

    def list_by_status(self, status):
        return self.find_by(status=status)


class AnalyticsIndicatorVersionRepository(BaseRepository):
    def __init__(self):
        super().__init__(model=AnalyticsIndicatorVersion)

    def get_draft_version(self, indicator_definition_id):
        return self.model.query.filter(
            AnalyticsIndicatorVersion.indicator_definition_id == indicator_definition_id,
            AnalyticsIndicatorVersion.status == AnalyticsIndicatorVersion.STATUS_DRAFT,
            AnalyticsIndicatorVersion.is_current_draft == True,
            AnalyticsIndicatorVersion.deleted_at == None,
        ).order_by(AnalyticsIndicatorVersion.version_number.desc()).first()

    def get_published_version(self, indicator_definition_id):
        return self.model.query.filter(
            AnalyticsIndicatorVersion.indicator_definition_id == indicator_definition_id,
            AnalyticsIndicatorVersion.status == AnalyticsIndicatorVersion.STATUS_PUBLISHED,
            AnalyticsIndicatorVersion.is_current_published == True,
            AnalyticsIndicatorVersion.deleted_at == None,
        ).order_by(AnalyticsIndicatorVersion.version_number.desc()).first()

    def get_next_version_number(self, indicator_definition_id):
        latest_version_number = self.model.query.filter(
            AnalyticsIndicatorVersion.indicator_definition_id == indicator_definition_id,
            AnalyticsIndicatorVersion.deleted_at == None,
        ).with_entities(func.max(AnalyticsIndicatorVersion.version_number)).scalar()
        return (latest_version_number or 0) + 1

    def list_versions(self, indicator_definition_id):
        return self.model.query.filter(
            AnalyticsIndicatorVersion.indicator_definition_id == indicator_definition_id,
            AnalyticsIndicatorVersion.deleted_at == None,
        ).order_by(AnalyticsIndicatorVersion.version_number.desc()).all()

    def archive_published_others(self, indicator_definition_id, except_version_id=None):
        query = self.model.query.filter(
            AnalyticsIndicatorVersion.indicator_definition_id == indicator_definition_id,
            AnalyticsIndicatorVersion.is_current_published == True,
            AnalyticsIndicatorVersion.deleted_at == None,
        )
        if except_version_id is not None:
            query = query.filter(AnalyticsIndicatorVersion.id != except_version_id)

        versions = query.all()
        for version in versions:
            version.is_current_published = False
            version.is_current_draft = False
            if version.status == AnalyticsIndicatorVersion.STATUS_PUBLISHED:
                version.status = AnalyticsIndicatorVersion.STATUS_ARCHIVED
        return versions


class AnalyticsReportVersionIndicatorRepository(BaseRepository):
    def __init__(self):
        super().__init__(model=AnalyticsReportVersionIndicator)

    def list_by_report_version(self, report_version_id):
        return self.model.query.filter(
            AnalyticsReportVersionIndicator.report_version_id == report_version_id,
            AnalyticsReportVersionIndicator.deleted_at == None,
        ).order_by(AnalyticsReportVersionIndicator.item_order.asc()).all()


class AnalyticsIndicatorResultRepository(BaseRepository):
    def __init__(self):
        super().__init__(model=AnalyticsIndicatorResult)

    def list_by_indicator_version(self, indicator_version_id):
        return self.model.query.filter(
            AnalyticsIndicatorResult.indicator_version_id == indicator_version_id,
            AnalyticsIndicatorResult.deleted_at == None,
        ).order_by(AnalyticsIndicatorResult.created_at.desc()).all()

    def get_latest_for_period(self, indicator_version_id, reporting_year=None, reporting_period_id=None):
        query = self.model.query.filter(
            AnalyticsIndicatorResult.indicator_version_id == indicator_version_id,
            AnalyticsIndicatorResult.deleted_at == None,
        )
        if reporting_year is not None:
            query = query.filter(AnalyticsIndicatorResult.reporting_year == reporting_year)
        if reporting_period_id is not None:
            query = query.filter(AnalyticsIndicatorResult.reporting_period_id == reporting_period_id)
        return query.order_by(
            AnalyticsIndicatorResult.calculated_at.desc(),
            AnalyticsIndicatorResult.created_at.desc(),
        ).first()

    def list_filtered(self, indicator_version_id=None, reporting_year=None, reporting_period_id=None, limit=50):
        query = self.model.query.filter(
            AnalyticsIndicatorResult.deleted_at == None,
        )
        if indicator_version_id is not None:
            query = query.filter(AnalyticsIndicatorResult.indicator_version_id == indicator_version_id)
        if reporting_year is not None:
            query = query.filter(AnalyticsIndicatorResult.reporting_year == reporting_year)
        if reporting_period_id is not None:
            query = query.filter(AnalyticsIndicatorResult.reporting_period_id == reporting_period_id)
        return query.order_by(
            AnalyticsIndicatorResult.calculated_at.desc(),
            AnalyticsIndicatorResult.created_at.desc(),
        ).limit(limit).all()


class AnalyticsIndicatorProgressEntryRepository(BaseRepository):
    def __init__(self):
        super().__init__(model=AnalyticsIndicatorProgressEntry)

    def list_by_indicator_version(self, indicator_version_id):
        return self.model.query.filter(
            AnalyticsIndicatorProgressEntry.indicator_version_id == indicator_version_id,
            AnalyticsIndicatorProgressEntry.deleted_at == None,
        ).order_by(AnalyticsIndicatorProgressEntry.created_at.desc()).all()

    def get_latest_for_period(self, indicator_version_id, reporting_year=None, reporting_period_id=None):
        query = self.model.query.filter(
            AnalyticsIndicatorProgressEntry.indicator_version_id == indicator_version_id,
            AnalyticsIndicatorProgressEntry.deleted_at == None,
        )
        if reporting_year is not None:
            query = query.filter(AnalyticsIndicatorProgressEntry.reporting_year == reporting_year)
        if reporting_period_id is not None:
            query = query.filter(AnalyticsIndicatorProgressEntry.reporting_period_id == reporting_period_id)
        return query.order_by(AnalyticsIndicatorProgressEntry.created_at.desc()).first()

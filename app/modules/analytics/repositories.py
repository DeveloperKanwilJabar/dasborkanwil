"""Repository domain analytics.

Modul ini menyediakan query spesifik untuk dataset, report, indikator, run, result, dan progress analytics."""

from sqlalchemy import func

from app.core.extensions import db
from app.core.repositories.base import BaseRepository

from .models import (
    AnalyticsDataset,
    AnalyticsDatasetRun,
    AnalyticsDatasetVersion,
    AnalyticsIndicatorDefinition,
    AnalyticsIndicatorProgressEntry,
    AnalyticsIndicatorProgressItem,
    AnalyticsIndicatorResult,
    AnalyticsIndicatorVersion,
    AnalyticsReportDefinition,
    AnalyticsReportVersion,
    AnalyticsReportVersionIndicator,
)


class AnalyticsDatasetRepository(BaseRepository):
    """Repository query untuk entity AnalyticsDataset.

    Class ini membungkus query SQLAlchemy yang sering dipakai service
    agar logika akses data tetap terpusat dan konsisten.

    Example:
        >>> obj = AnalyticsDatasetRepository()
    """

    def __init__(self):
        """Inisialisasi object dan dependency dasar yang dibutuhkan class ini.

        Returns:
            Any: Nilai hasil operasi repository/model.

        Example:
            >>> repo = AnalyticsDatasetRepository()
        """

        super().__init__(model=AnalyticsDataset)

    def get_by_key(self, dataset_key):
        """Mengambil entity berdasarkan business key unik.

        Args:
            dataset_key (Any): Business key unik dataset analytics.

        Returns:
            Any | None: Satu object hasil query atau None bila tidak ditemukan.

        Example:
            >>> repo.get_by_key(dataset_key=...)
        """

        return self.find_one_by(dataset_key=dataset_key)

    def list_by_status(self, status):
        """Mengambil daftar entity berdasarkan status bisnisnya.

        Args:
            status (Any): Status bisnis yang dipakai untuk filtering data.

        Returns:
            list[Any]: Daftar object hasil query atau hasil operasi bulk.

        Example:
            >>> repo.list_by_status(status=...)
        """

        return self.find_by(status=status)


class AnalyticsDatasetVersionRepository(BaseRepository):
    """Repository query untuk entity AnalyticsDatasetVersion.

    Class ini membungkus query SQLAlchemy yang sering dipakai service
    agar logika akses data tetap terpusat dan konsisten.

    Example:
        >>> obj = AnalyticsDatasetVersionRepository()
    """

    def __init__(self):
        """Inisialisasi object dan dependency dasar yang dibutuhkan class ini.

        Returns:
            Any: Nilai hasil operasi repository/model.

        Example:
            >>> repo = AnalyticsDatasetVersionRepository()
        """

        super().__init__(model=AnalyticsDatasetVersion)

    def get_draft_version(self, dataset_id):
        """Mengambil draft version aktif untuk entity induk tertentu.

        Args:
            dataset_id (Any): Primary key internal dataset target.

        Returns:
            Any | None: Satu object hasil query atau None bila tidak ditemukan.

        Example:
            >>> repo.get_draft_version(dataset_id=...)
        """

        return self.model.query.filter(
            AnalyticsDatasetVersion.dataset_id == dataset_id,
            AnalyticsDatasetVersion.status == AnalyticsDatasetVersion.STATUS_DRAFT,
            AnalyticsDatasetVersion.is_current_draft == True,
            AnalyticsDatasetVersion.deleted_at == None,
        ).order_by(AnalyticsDatasetVersion.version_number.desc()).first()

    def get_published_version(self, dataset_id):
        """Mengambil version published aktif untuk entity induk tertentu.

        Args:
            dataset_id (Any): Primary key internal dataset target.

        Returns:
            Any | None: Satu object hasil query atau None bila tidak ditemukan.

        Example:
            >>> repo.get_published_version(dataset_id=...)
        """

        return self.model.query.filter(
            AnalyticsDatasetVersion.dataset_id == dataset_id,
            AnalyticsDatasetVersion.status == AnalyticsDatasetVersion.STATUS_PUBLISHED,
            AnalyticsDatasetVersion.is_current_published == True,
            AnalyticsDatasetVersion.deleted_at == None,
        ).order_by(AnalyticsDatasetVersion.version_number.desc()).first()

    def get_next_version_number(self, dataset_id):
        """Menghitung nomor versi berikutnya untuk entity versioned.

        Args:
            dataset_id (Any): Primary key internal dataset target.

        Returns:
            Any | None: Satu object hasil query atau None bila tidak ditemukan.

        Example:
            >>> repo.get_next_version_number(dataset_id=...)
        """

        latest_version_number = self.model.query.filter(
            AnalyticsDatasetVersion.dataset_id == dataset_id,
            AnalyticsDatasetVersion.deleted_at == None,
        ).with_entities(func.max(AnalyticsDatasetVersion.version_number)).scalar()
        return (latest_version_number or 0) + 1

    def list_versions(self, dataset_id):
        """Mengambil seluruh versi entity tertentu secara terurut terbaru ke lama.

        Args:
            dataset_id (Any): Primary key internal dataset target.

        Returns:
            list[Any]: Daftar object hasil query atau hasil operasi bulk.

        Example:
            >>> repo.list_versions(dataset_id=...)
        """

        return self.model.query.filter(
            AnalyticsDatasetVersion.dataset_id == dataset_id,
            AnalyticsDatasetVersion.deleted_at == None,
        ).order_by(AnalyticsDatasetVersion.version_number.desc()).all()

    def archive_published_others(self, dataset_id, except_version_id=None):
        """Mengarsipkan version published lain selain target yang dipertahankan.

        Args:
            dataset_id (Any): Primary key internal dataset target.
            except_version_id (Any): Primary key version yang tidak ikut diubah saat update massal.

        Returns:
            Any: Nilai hasil operasi repository/model.

        Example:
            >>> repo.archive_published_others(dataset_id=..., except_version_id=...)
        """

        query = self.model.query.filter(
            AnalyticsDatasetVersion.dataset_id == dataset_id,
            AnalyticsDatasetVersion.is_current_published == True,
            AnalyticsDatasetVersion.deleted_at == None,
        )
        if except_version_id is not None:
            query = query.filter(AnalyticsDatasetVersion.id != except_version_id)

        versions = query.all()
        for version in versions:
            version.is_current_published = False
            version.is_current_draft = False
            if version.status == AnalyticsDatasetVersion.STATUS_PUBLISHED:
                version.status = AnalyticsDatasetVersion.STATUS_ARCHIVED
        return versions


class AnalyticsDatasetRunRepository(BaseRepository):
    """Repository query untuk entity AnalyticsDatasetRun.

    Class ini membungkus query SQLAlchemy yang sering dipakai service
    agar logika akses data tetap terpusat dan konsisten.

    Example:
        >>> obj = AnalyticsDatasetRunRepository()
    """

    def __init__(self):
        """Inisialisasi object dan dependency dasar yang dibutuhkan class ini.

        Returns:
            Any: Nilai hasil operasi repository/model.

        Example:
            >>> repo = AnalyticsDatasetRunRepository()
        """

        super().__init__(model=AnalyticsDatasetRun)

    def list_by_dataset(self, dataset_id, limit=50):
        """Mengambil daftar run dataset untuk dataset tertentu.

        Args:
            dataset_id (Any): Primary key internal dataset target.
            limit (Any): Batas jumlah row yang dikembalikan query.

        Returns:
            list[Any]: Daftar object hasil query atau hasil operasi bulk.

        Example:
            >>> repo.list_by_dataset(dataset_id=..., limit=...)
        """

        return self.model.query.filter(
            AnalyticsDatasetRun.dataset_id == dataset_id,
            AnalyticsDatasetRun.deleted_at == None,
        ).order_by(AnalyticsDatasetRun.created_at.desc()).limit(limit).all()

    def list_by_dataset_version(self, dataset_version_id, limit=50):
        """Mengambil daftar run berdasarkan dataset version tertentu.

        Args:
            dataset_version_id (Any): Primary key internal dataset version target.
            limit (Any): Batas jumlah row yang dikembalikan query.

        Returns:
            list[Any]: Daftar object hasil query atau hasil operasi bulk.

        Example:
            >>> repo.list_by_dataset_version(dataset_version_id=..., limit=...)
        """

        return self.model.query.filter(
            AnalyticsDatasetRun.dataset_version_id == dataset_version_id,
            AnalyticsDatasetRun.deleted_at == None,
        ).order_by(AnalyticsDatasetRun.created_at.desc()).limit(limit).all()

    def get_latest_for_dataset_version(self, dataset_version_id):
        """Mengambil run terbaru untuk dataset version tertentu.

        Args:
            dataset_version_id (Any): Primary key internal dataset version target.

        Returns:
            Any | None: Satu object hasil query atau None bila tidak ditemukan.

        Example:
            >>> repo.get_latest_for_dataset_version(dataset_version_id=...)
        """

        return self.model.query.filter(
            AnalyticsDatasetRun.dataset_version_id == dataset_version_id,
            AnalyticsDatasetRun.deleted_at == None,
        ).order_by(
            AnalyticsDatasetRun.started_at.desc(),
            AnalyticsDatasetRun.created_at.desc(),
        ).first()


class AnalyticsReportDefinitionRepository(BaseRepository):
    """Repository query untuk entity AnalyticsReportDefinition.

    Class ini membungkus query SQLAlchemy yang sering dipakai service
    agar logika akses data tetap terpusat dan konsisten.

    Example:
        >>> obj = AnalyticsReportDefinitionRepository()
    """

    def __init__(self):
        """Inisialisasi object dan dependency dasar yang dibutuhkan class ini.

        Returns:
            Any: Nilai hasil operasi repository/model.

        Example:
            >>> repo = AnalyticsReportDefinitionRepository()
        """

        super().__init__(model=AnalyticsReportDefinition)

    def get_by_key(self, report_key):
        """Mengambil entity berdasarkan business key unik.

        Args:
            report_key (Any): Business key unik report analytics.

        Returns:
            Any | None: Satu object hasil query atau None bila tidak ditemukan.

        Example:
            >>> repo.get_by_key(report_key=...)
        """

        return self.find_one_by(report_key=report_key)

    def list_by_status(self, status):
        """Mengambil daftar entity berdasarkan status bisnisnya.

        Args:
            status (Any): Status bisnis yang dipakai untuk filtering data.

        Returns:
            list[Any]: Daftar object hasil query atau hasil operasi bulk.

        Example:
            >>> repo.list_by_status(status=...)
        """

        return self.find_by(status=status)


class AnalyticsReportVersionRepository(BaseRepository):
    """Repository query untuk entity AnalyticsReportVersion.

    Class ini membungkus query SQLAlchemy yang sering dipakai service
    agar logika akses data tetap terpusat dan konsisten.

    Example:
        >>> obj = AnalyticsReportVersionRepository()
    """

    def __init__(self):
        """Inisialisasi object dan dependency dasar yang dibutuhkan class ini.

        Returns:
            Any: Nilai hasil operasi repository/model.

        Example:
            >>> repo = AnalyticsReportVersionRepository()
        """

        super().__init__(model=AnalyticsReportVersion)

    def get_draft_version(self, report_definition_id):
        """Mengambil draft version aktif untuk entity induk tertentu.

        Args:
            report_definition_id (Any): Primary key internal definisi report target.

        Returns:
            Any | None: Satu object hasil query atau None bila tidak ditemukan.

        Example:
            >>> repo.get_draft_version(report_definition_id=...)
        """

        return self.model.query.filter(
            AnalyticsReportVersion.report_definition_id == report_definition_id,
            AnalyticsReportVersion.status == AnalyticsReportVersion.STATUS_DRAFT,
            AnalyticsReportVersion.is_current_draft == True,
            AnalyticsReportVersion.deleted_at == None,
        ).order_by(AnalyticsReportVersion.version_number.desc()).first()

    def get_published_version(self, report_definition_id):
        """Mengambil version published aktif untuk entity induk tertentu.

        Args:
            report_definition_id (Any): Primary key internal definisi report target.

        Returns:
            Any | None: Satu object hasil query atau None bila tidak ditemukan.

        Example:
            >>> repo.get_published_version(report_definition_id=...)
        """

        return self.model.query.filter(
            AnalyticsReportVersion.report_definition_id == report_definition_id,
            AnalyticsReportVersion.status == AnalyticsReportVersion.STATUS_PUBLISHED,
            AnalyticsReportVersion.is_current_published == True,
            AnalyticsReportVersion.deleted_at == None,
        ).order_by(AnalyticsReportVersion.version_number.desc()).first()

    def get_next_version_number(self, report_definition_id):
        """Menghitung nomor versi berikutnya untuk entity versioned.

        Args:
            report_definition_id (Any): Primary key internal definisi report target.

        Returns:
            Any | None: Satu object hasil query atau None bila tidak ditemukan.

        Example:
            >>> repo.get_next_version_number(report_definition_id=...)
        """

        latest_version_number = self.model.query.filter(
            AnalyticsReportVersion.report_definition_id == report_definition_id,
            AnalyticsReportVersion.deleted_at == None,
        ).with_entities(func.max(AnalyticsReportVersion.version_number)).scalar()
        return (latest_version_number or 0) + 1

    def list_versions(self, report_definition_id):
        """Mengambil seluruh versi entity tertentu secara terurut terbaru ke lama.

        Args:
            report_definition_id (Any): Primary key internal definisi report target.

        Returns:
            list[Any]: Daftar object hasil query atau hasil operasi bulk.

        Example:
            >>> repo.list_versions(report_definition_id=...)
        """

        return self.model.query.filter(
            AnalyticsReportVersion.report_definition_id == report_definition_id,
            AnalyticsReportVersion.deleted_at == None,
        ).order_by(AnalyticsReportVersion.version_number.desc()).all()

    def archive_published_others(self, report_definition_id, except_version_id=None):
        """Mengarsipkan version published lain selain target yang dipertahankan.

        Args:
            report_definition_id (Any): Primary key internal definisi report target.
            except_version_id (Any): Primary key version yang tidak ikut diubah saat update massal.

        Returns:
            Any: Nilai hasil operasi repository/model.

        Example:
            >>> repo.archive_published_others(report_definition_id=..., except_version_id=...)
        """

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
    """Repository query untuk entity AnalyticsIndicatorDefinition.

    Class ini membungkus query SQLAlchemy yang sering dipakai service
    agar logika akses data tetap terpusat dan konsisten.

    Example:
        >>> obj = AnalyticsIndicatorDefinitionRepository()
    """

    def __init__(self):
        """Inisialisasi object dan dependency dasar yang dibutuhkan class ini.

        Returns:
            Any: Nilai hasil operasi repository/model.

        Example:
            >>> repo = AnalyticsIndicatorDefinitionRepository()
        """

        super().__init__(model=AnalyticsIndicatorDefinition)

    def get_by_key(self, indicator_key):
        """Mengambil entity berdasarkan business key unik.

        Args:
            indicator_key (Any): Business key unik indikator analytics.

        Returns:
            Any | None: Satu object hasil query atau None bila tidak ditemukan.

        Example:
            >>> repo.get_by_key(indicator_key=...)
        """

        return self.find_one_by(indicator_key=indicator_key)

    def list_by_status(self, status):
        """Mengambil daftar entity berdasarkan status bisnisnya.

        Args:
            status (Any): Status bisnis yang dipakai untuk filtering data.

        Returns:
            list[Any]: Daftar object hasil query atau hasil operasi bulk.

        Example:
            >>> repo.list_by_status(status=...)
        """

        return self.find_by(status=status)


class AnalyticsIndicatorVersionRepository(BaseRepository):
    """Repository query untuk entity AnalyticsIndicatorVersion.

    Class ini membungkus query SQLAlchemy yang sering dipakai service
    agar logika akses data tetap terpusat dan konsisten.

    Example:
        >>> obj = AnalyticsIndicatorVersionRepository()
    """

    def __init__(self):
        """Inisialisasi object dan dependency dasar yang dibutuhkan class ini.

        Returns:
            Any: Nilai hasil operasi repository/model.

        Example:
            >>> repo = AnalyticsIndicatorVersionRepository()
        """

        super().__init__(model=AnalyticsIndicatorVersion)

    def get_draft_version(self, indicator_definition_id):
        """Mengambil draft version aktif untuk entity induk tertentu.

        Args:
            indicator_definition_id (Any): Primary key internal definisi indikator target.

        Returns:
            Any | None: Satu object hasil query atau None bila tidak ditemukan.

        Example:
            >>> repo.get_draft_version(indicator_definition_id=...)
        """

        return self.model.query.filter(
            AnalyticsIndicatorVersion.indicator_definition_id == indicator_definition_id,
            AnalyticsIndicatorVersion.status == AnalyticsIndicatorVersion.STATUS_DRAFT,
            AnalyticsIndicatorVersion.is_current_draft == True,
            AnalyticsIndicatorVersion.deleted_at == None,
        ).order_by(AnalyticsIndicatorVersion.version_number.desc()).first()

    def get_published_version(self, indicator_definition_id):
        """Mengambil version published aktif untuk entity induk tertentu.

        Args:
            indicator_definition_id (Any): Primary key internal definisi indikator target.

        Returns:
            Any | None: Satu object hasil query atau None bila tidak ditemukan.

        Example:
            >>> repo.get_published_version(indicator_definition_id=...)
        """

        return self.model.query.filter(
            AnalyticsIndicatorVersion.indicator_definition_id == indicator_definition_id,
            AnalyticsIndicatorVersion.status == AnalyticsIndicatorVersion.STATUS_PUBLISHED,
            AnalyticsIndicatorVersion.is_current_published == True,
            AnalyticsIndicatorVersion.deleted_at == None,
        ).order_by(AnalyticsIndicatorVersion.version_number.desc()).first()

    def get_next_version_number(self, indicator_definition_id):
        """Menghitung nomor versi berikutnya untuk entity versioned.

        Args:
            indicator_definition_id (Any): Primary key internal definisi indikator target.

        Returns:
            Any | None: Satu object hasil query atau None bila tidak ditemukan.

        Example:
            >>> repo.get_next_version_number(indicator_definition_id=...)
        """

        latest_version_number = self.model.query.filter(
            AnalyticsIndicatorVersion.indicator_definition_id == indicator_definition_id,
            AnalyticsIndicatorVersion.deleted_at == None,
        ).with_entities(func.max(AnalyticsIndicatorVersion.version_number)).scalar()
        return (latest_version_number or 0) + 1

    def list_versions(self, indicator_definition_id):
        """Mengambil seluruh versi entity tertentu secara terurut terbaru ke lama.

        Args:
            indicator_definition_id (Any): Primary key internal definisi indikator target.

        Returns:
            list[Any]: Daftar object hasil query atau hasil operasi bulk.

        Example:
            >>> repo.list_versions(indicator_definition_id=...)
        """

        return self.model.query.filter(
            AnalyticsIndicatorVersion.indicator_definition_id == indicator_definition_id,
            AnalyticsIndicatorVersion.deleted_at == None,
        ).order_by(AnalyticsIndicatorVersion.version_number.desc()).all()

    def archive_published_others(self, indicator_definition_id, except_version_id=None):
        """Mengarsipkan version published lain selain target yang dipertahankan.

        Args:
            indicator_definition_id (Any): Primary key internal definisi indikator target.
            except_version_id (Any): Primary key version yang tidak ikut diubah saat update massal.

        Returns:
            Any: Nilai hasil operasi repository/model.

        Example:
            >>> repo.archive_published_others(indicator_definition_id=..., except_version_id=...)
        """

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
    """Repository query untuk mapping indicator-report version.

    Class ini membungkus query SQLAlchemy yang sering dipakai service
    agar logika akses data tetap terpusat dan konsisten.

    Example:
        >>> obj = AnalyticsReportVersionIndicatorRepository()
    """

    def __init__(self):
        """Inisialisasi object dan dependency dasar yang dibutuhkan class ini.

        Returns:
            Any: Nilai hasil operasi repository/model.

        Example:
            >>> repo = AnalyticsReportVersionIndicatorRepository()
        """

        super().__init__(model=AnalyticsReportVersionIndicator)

    def list_by_report_version(self, report_version_id):
        """Mengambil mapping indikator yang terpasang pada report version.

        Args:
            report_version_id (Any): Primary key internal report version target.

        Returns:
            list[Any]: Daftar object hasil query atau hasil operasi bulk.

        Example:
            >>> repo.list_by_report_version(report_version_id=...)
        """

        return self.model.query.filter(
            AnalyticsReportVersionIndicator.report_version_id == report_version_id,
            AnalyticsReportVersionIndicator.deleted_at == None,
        ).order_by(AnalyticsReportVersionIndicator.item_order.asc()).all()


class AnalyticsIndicatorResultRepository(BaseRepository):
    """Repository query untuk hasil indikator analytics.

    Class ini membungkus query SQLAlchemy yang sering dipakai service
    agar logika akses data tetap terpusat dan konsisten.

    Example:
        >>> obj = AnalyticsIndicatorResultRepository()
    """

    def __init__(self):
        """Inisialisasi object dan dependency dasar yang dibutuhkan class ini.

        Returns:
            Any: Nilai hasil operasi repository/model.

        Example:
            >>> repo = AnalyticsIndicatorResultRepository()
        """

        super().__init__(model=AnalyticsIndicatorResult)

    def list_by_indicator_version(self, indicator_version_id):
        """Mengambil result/progress entry untuk indikator version tertentu.

        Args:
            indicator_version_id (Any): Primary key internal indikator version target.

        Returns:
            list[Any]: Daftar object hasil query atau hasil operasi bulk.

        Example:
            >>> repo.list_by_indicator_version(indicator_version_id=...)
        """

        return self.model.query.filter(
            AnalyticsIndicatorResult.indicator_version_id == indicator_version_id,
            AnalyticsIndicatorResult.deleted_at == None,
        ).order_by(AnalyticsIndicatorResult.created_at.desc()).all()

    def get_latest_for_period(self, indicator_version_id, reporting_year=None, reporting_period_id=None):
        """Mengambil record terbaru untuk kombinasi indikator dan periode tertentu.

        Args:
            indicator_version_id (Any): Primary key internal indikator version target.
            reporting_year (Any): Tahun pelaporan yang dipakai untuk filter query.
            reporting_period_id (Any): Primary key internal reporting period target.

        Returns:
            Any | None: Satu object hasil query atau None bila tidak ditemukan.

        Example:
            >>> repo.get_latest_for_period(indicator_version_id=..., reporting_year=..., reporting_period_id=...)
        """

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
        """Mengambil result indikator dengan kombinasi filter opsional.

        Args:
            indicator_version_id (Any): Primary key internal indikator version target.
            reporting_year (Any): Tahun pelaporan yang dipakai untuk filter query.
            reporting_period_id (Any): Primary key internal reporting period target.
            limit (Any): Batas jumlah row yang dikembalikan query.

        Returns:
            list[Any]: Daftar object hasil query atau hasil operasi bulk.

        Example:
            >>> repo.list_filtered(indicator_version_id=..., reporting_year=..., reporting_period_id=...)
        """

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
    """Repository query untuk progress entry indikator.

    Class ini membungkus query SQLAlchemy yang sering dipakai service
    agar logika akses data tetap terpusat dan konsisten.

    Example:
        >>> obj = AnalyticsIndicatorProgressEntryRepository()
    """

    def __init__(self):
        """Inisialisasi object dan dependency dasar yang dibutuhkan class ini.

        Returns:
            Any: Nilai hasil operasi repository/model.

        Example:
            >>> repo = AnalyticsIndicatorProgressEntryRepository()
        """

        super().__init__(model=AnalyticsIndicatorProgressEntry)

    def list_by_indicator_version(self, indicator_version_id):
        """Mengambil result/progress entry untuk indikator version tertentu.

        Args:
            indicator_version_id (Any): Primary key internal indikator version target.

        Returns:
            list[Any]: Daftar object hasil query atau hasil operasi bulk.

        Example:
            >>> repo.list_by_indicator_version(indicator_version_id=...)
        """

        return self.model.query.filter(
            AnalyticsIndicatorProgressEntry.indicator_version_id == indicator_version_id,
            AnalyticsIndicatorProgressEntry.deleted_at == None,
        ).order_by(AnalyticsIndicatorProgressEntry.created_at.desc()).all()

    def get_latest_for_period(self, indicator_version_id, reporting_year=None, reporting_period_id=None):
        """Mengambil record terbaru untuk kombinasi indikator dan periode tertentu.

        Args:
            indicator_version_id (Any): Primary key internal indikator version target.
            reporting_year (Any): Tahun pelaporan yang dipakai untuk filter query.
            reporting_period_id (Any): Primary key internal reporting period target.

        Returns:
            Any | None: Satu object hasil query atau None bila tidak ditemukan.

        Example:
            >>> repo.get_latest_for_period(indicator_version_id=..., reporting_year=..., reporting_period_id=...)
        """

        query = self.model.query.filter(
            AnalyticsIndicatorProgressEntry.indicator_version_id == indicator_version_id,
            AnalyticsIndicatorProgressEntry.deleted_at == None,
        )
        if reporting_year is not None:
            query = query.filter(AnalyticsIndicatorProgressEntry.reporting_year == reporting_year)
        if reporting_period_id is not None:
            query = query.filter(AnalyticsIndicatorProgressEntry.reporting_period_id == reporting_period_id)
        return query.order_by(AnalyticsIndicatorProgressEntry.created_at.desc()).first()

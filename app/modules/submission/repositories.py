"""Repository domain submission.

Modul ini menyediakan query persistence untuk periode pelaporan, submission, event submission, dan kebutuhan freshness analytics."""

from sqlalchemy import func

from app.core.repositories.base import BaseRepository

from .models import ReportingPeriod, Submission, SubmissionEvent


class ReportingPeriodRepository(BaseRepository):
    """Repository query untuk entity ReportingPeriod.

    Class ini membungkus query SQLAlchemy yang sering dipakai service
    agar logika akses data tetap terpusat dan konsisten.

    Example:
        >>> obj = ReportingPeriodRepository()
    """

    def __init__(self):
        """Inisialisasi object dan dependency dasar yang dibutuhkan class ini.

        Returns:
            Any: Nilai hasil operasi repository/model.

        Example:
            >>> repo = ReportingPeriodRepository()
        """

        super().__init__(model=ReportingPeriod)

    def get_active_by_year(self, year=None):
        """Mengambil reporting period aktif untuk tahun tertentu.

        Args:
            year (Any): Parameter `year` untuk operasi get active by year.

        Returns:
            Any | None: Satu object hasil query atau None bila tidak ditemukan.

        Example:
            >>> repo.get_active_by_year(year=...)
        """

        query = self.model.query.filter(
            ReportingPeriod.is_active == True,
            ReportingPeriod.deleted_at == None,
        )
        if year is not None:
            query = query.filter(ReportingPeriod.year == year)
        return query.order_by(ReportingPeriod.starts_at.desc()).first()

    def get_by_code(self, code):
        """Mengambil entity berdasarkan business code unik.

        Args:
            code (Any): Business code unik entity target.

        Returns:
            Any | None: Satu object hasil query atau None bila tidak ditemukan.

        Example:
            >>> repo.get_by_code(code=...)
        """

        return self.find_one_by(code=code)

    def list_by_year(self, year):
        """Mengambil seluruh entity yang berada pada tahun tertentu.

        Args:
            year (Any): Parameter `year` untuk operasi list by year.

        Returns:
            list[Any]: Daftar object hasil query atau hasil operasi bulk.

        Example:
            >>> repo.list_by_year(year=...)
        """

        return self.find_by(year=year)

    def list_by_type(self, period_type, year=None):
        """Mengambil daftar periode pelaporan berdasarkan tipe periode.

        Args:
            period_type (Any): Parameter `period_type` untuk operasi list by type.
            year (Any): Parameter `year` untuk operasi list by type.

        Returns:
            list[Any]: Daftar object hasil query atau hasil operasi bulk.

        Example:
            >>> repo.list_by_type(period_type=..., year=...)
        """

        query = self.model.query.filter(
            ReportingPeriod.period_type == period_type,
            ReportingPeriod.deleted_at == None,
        )
        if year is not None:
            query = query.filter(ReportingPeriod.year == year)
        return query.order_by(ReportingPeriod.starts_at.asc()).all()


class SubmissionRepository(BaseRepository):
    """Repository query untuk entity Submission.

    Class ini membungkus query SQLAlchemy yang sering dipakai service
    agar logika akses data tetap terpusat dan konsisten.

    Example:
        >>> obj = SubmissionRepository()
    """

    def __init__(self):
        """Inisialisasi object dan dependency dasar yang dibutuhkan class ini.

        Returns:
            Any: Nilai hasil operasi repository/model.

        Example:
            >>> repo = SubmissionRepository()
        """

        super().__init__(model=Submission)

    def get_by_number(self, submission_number):
        """Mengambil submission berdasarkan nomor submission unik.

        Args:
            submission_number (Any): Nomor submission unik bisnis.

        Returns:
            Any | None: Satu object hasil query atau None bila tidak ditemukan.

        Example:
            >>> repo.get_by_number(submission_number=...)
        """

        return self.find_one_by(submission_number=submission_number)

    def list_by_form(self, form_id, reporting_year=None):
        """Mengambil submission yang terkait ke form tertentu.

        Args:
            form_id (Any): Primary key internal form target.
            reporting_year (Any): Tahun pelaporan yang dipakai untuk filter query.

        Returns:
            list[Any]: Daftar object hasil query atau hasil operasi bulk.

        Example:
            >>> repo.list_by_form(form_id=..., reporting_year=...)
        """

        query = self.model.query.filter(
            Submission.form_id == form_id,
            Submission.deleted_at == None,
        )
        if reporting_year is not None:
            query = query.filter(Submission.reporting_year == reporting_year)
        return query.order_by(Submission.created_at.desc()).all()

    def list_by_reporting_year(self, reporting_year):
        """Mengambil submission untuk tahun pelaporan tertentu.

        Args:
            reporting_year (Any): Tahun pelaporan yang dipakai untuk filter query.

        Returns:
            list[Any]: Daftar object hasil query atau hasil operasi bulk.

        Example:
            >>> repo.list_by_reporting_year(reporting_year=...)
        """

        return self.model.query.filter(
            Submission.reporting_year == reporting_year,
            Submission.deleted_at == None,
        ).order_by(Submission.created_at.desc()).all()

    def list_filtered(self, form_id=None, reporting_year=None, reporting_period_id=None, statuses=None):
        """Mengambil daftar submission untuk tabel operator dengan filter umum."""
        query = self.model.query.filter(Submission.deleted_at == None)
        if form_id is not None:
            query = query.filter(Submission.form_id == form_id)
        if reporting_year is not None:
            query = query.filter(Submission.reporting_year == reporting_year)
        if reporting_period_id is not None:
            query = query.filter(Submission.reporting_period_id == reporting_period_id)
        if statuses:
            query = query.filter(Submission.status.in_(statuses))
        return query.order_by(Submission.submitted_at.desc(), Submission.created_at.desc()).all()

    def list_by_reporting_period(self, reporting_period_id):
        """Mengambil submission untuk reporting period tertentu.

        Args:
            reporting_period_id (Any): Primary key internal reporting period target.

        Returns:
            list[Any]: Daftar object hasil query atau hasil operasi bulk.

        Example:
            >>> repo.list_by_reporting_period(reporting_period_id=...)
        """

        return self.model.query.filter(
            Submission.reporting_period_id == reporting_period_id,
            Submission.deleted_at == None,
        ).order_by(Submission.created_at.desc()).all()

    def list_for_analytics(self, form_id=None, years=None, period_ids=None):
        """Mengambil submission yang layak dipakai kebutuhan analytics/filtering.

        Args:
            form_id (Any): Primary key internal form target.
            years (Any): Kumpulan tahun pelaporan untuk kebutuhan analytics.
            period_ids (Any): Kumpulan reporting period id untuk kebutuhan analytics.

        Returns:
            list[Any]: Daftar object hasil query atau hasil operasi bulk.

        Example:
            >>> repo.list_for_analytics(form_id=..., years=..., period_ids=...)
        """

        query = self.model.query.filter(Submission.deleted_at == None)

        if form_id is not None:
            query = query.filter(Submission.form_id == form_id)
        if years:
            query = query.filter(Submission.reporting_year.in_(years))
        if period_ids:
            query = query.filter(Submission.reporting_period_id.in_(period_ids))

        return query.order_by(Submission.submitted_at.desc()).all()

    def get_last_submitted_at(
        self,
        form_id=None,
        reporting_year=None,
        reporting_period_id=None,
        statuses=None,
    ):
        """Mengambil timestamp submit resmi terbaru untuk keperluan freshness data.

        Args:
            form_id (Any): Primary key internal form target.
            reporting_year (Any): Tahun pelaporan yang dipakai untuk filter query.
            reporting_period_id (Any): Primary key internal reporting period target.
            statuses (Any): Parameter `statuses` untuk operasi get last submitted at.

        Returns:
            Any | None: Satu object hasil query atau None bila tidak ditemukan.

        Example:
            >>> repo.get_last_submitted_at(form_id=..., reporting_year=..., reporting_period_id=...)
        """

        query = self.model.query.filter(
            Submission.submitted_at != None,
            Submission.deleted_at == None,
        )

        if form_id is not None:
            query = query.filter(Submission.form_id == form_id)
        if reporting_year is not None:
            query = query.filter(Submission.reporting_year == reporting_year)
        if reporting_period_id is not None:
            query = query.filter(Submission.reporting_period_id == reporting_period_id)
        if statuses:
            query = query.filter(Submission.status.in_(statuses))

        return query.with_entities(func.max(Submission.submitted_at)).scalar()


class SubmissionEventRepository(BaseRepository):
    """Repository query untuk entity SubmissionEvent.

    Class ini membungkus query SQLAlchemy yang sering dipakai service
    agar logika akses data tetap terpusat dan konsisten.

    Example:
        >>> obj = SubmissionEventRepository()
    """

    def __init__(self):
        """Inisialisasi object dan dependency dasar yang dibutuhkan class ini.

        Returns:
            Any: Nilai hasil operasi repository/model.

        Example:
            >>> repo = SubmissionEventRepository()
        """

        super().__init__(model=SubmissionEvent)

    def list_by_submission(self, submission_id):
        """Mengambil seluruh event yang terkait ke satu submission.

        Args:
            submission_id (Any): Primary key internal submission target.

        Returns:
            list[Any]: Daftar object hasil query atau hasil operasi bulk.

        Example:
            >>> repo.list_by_submission(submission_id=...)
        """

        return self.model.query.filter(
            SubmissionEvent.submission_id == submission_id,
            SubmissionEvent.deleted_at == None,
        ).order_by(SubmissionEvent.event_at.asc()).all()

    def list_by_event_type(self, event_type):
        """Mengambil event submission berdasarkan jenis event.

        Args:
            event_type (Any): Jenis event submission yang ingin diambil.

        Returns:
            list[Any]: Daftar object hasil query atau hasil operasi bulk.

        Example:
            >>> repo.list_by_event_type(event_type=...)
        """

        return self.model.query.filter(
            SubmissionEvent.event_type == event_type,
            SubmissionEvent.deleted_at == None,
        ).order_by(SubmissionEvent.event_at.desc()).all()

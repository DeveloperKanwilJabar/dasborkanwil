from sqlalchemy import func

from app.core.repositories.base import BaseRepository

from .models import ReportingPeriod, Submission, SubmissionEvent


class ReportingPeriodRepository(BaseRepository):
    def __init__(self):
        super().__init__(model=ReportingPeriod)

    def get_active_by_year(self, year=None):
        query = self.model.query.filter(
            ReportingPeriod.is_active == True,
            ReportingPeriod.deleted_at == None,
        )
        if year is not None:
            query = query.filter(ReportingPeriod.year == year)
        return query.order_by(ReportingPeriod.starts_at.desc()).first()

    def get_by_code(self, code):
        return self.find_one_by(code=code)

    def list_by_year(self, year):
        return self.find_by(year=year)

    def list_by_type(self, period_type, year=None):
        query = self.model.query.filter(
            ReportingPeriod.period_type == period_type,
            ReportingPeriod.deleted_at == None,
        )
        if year is not None:
            query = query.filter(ReportingPeriod.year == year)
        return query.order_by(ReportingPeriod.starts_at.asc()).all()


class SubmissionRepository(BaseRepository):
    def __init__(self):
        super().__init__(model=Submission)

    def get_by_number(self, submission_number):
        return self.find_one_by(submission_number=submission_number)

    def list_by_form(self, form_id, reporting_year=None):
        query = self.model.query.filter(
            Submission.form_id == form_id,
            Submission.deleted_at == None,
        )
        if reporting_year is not None:
            query = query.filter(Submission.reporting_year == reporting_year)
        return query.order_by(Submission.created_at.desc()).all()

    def list_by_reporting_year(self, reporting_year):
        return self.model.query.filter(
            Submission.reporting_year == reporting_year,
            Submission.deleted_at == None,
        ).order_by(Submission.created_at.desc()).all()

    def list_by_reporting_period(self, reporting_period_id):
        return self.model.query.filter(
            Submission.reporting_period_id == reporting_period_id,
            Submission.deleted_at == None,
        ).order_by(Submission.created_at.desc()).all()

    def list_for_analytics(self, form_id=None, years=None, period_ids=None):
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
    def __init__(self):
        super().__init__(model=SubmissionEvent)

    def list_by_submission(self, submission_id):
        return self.model.query.filter(
            SubmissionEvent.submission_id == submission_id,
            SubmissionEvent.deleted_at == None,
        ).order_by(SubmissionEvent.event_at.asc()).all()

    def list_by_event_type(self, event_type):
        return self.model.query.filter(
            SubmissionEvent.event_type == event_type,
            SubmissionEvent.deleted_at == None,
        ).order_by(SubmissionEvent.event_at.desc()).all()

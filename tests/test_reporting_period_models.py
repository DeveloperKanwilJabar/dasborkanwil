from app import create_app
from app.modules.submission.models import ReportingPeriod, Submission


def test_reporting_period_model_has_expected_columns_and_period_types():
    app = create_app('testing')

    with app.app_context():
        columns = ReportingPeriod.__table__.columns

        assert 'uuid' in columns
        assert 'code' in columns
        assert 'name' in columns
        assert 'period_type' in columns
        assert 'year' in columns
        assert 'starts_at' in columns
        assert 'ends_at' in columns
        assert 'input_opens_at' in columns
        assert 'input_closes_at' in columns
        assert 'is_active' in columns
        assert 'status' in columns
        assert 'settings' in columns

        assert ReportingPeriod.PERIOD_TYPE_WEEKLY == 'weekly'
        assert ReportingPeriod.PERIOD_TYPE_MONTHLY == 'monthly'
        assert ReportingPeriod.PERIOD_TYPE_QUARTERLY == 'quarterly'
        assert ReportingPeriod.PERIOD_TYPE_FOUR_MONTHLY == 'four_monthly'
        assert ReportingPeriod.PERIOD_TYPE_SEMESTER == 'semester'
        assert ReportingPeriod.PERIOD_TYPE_YEARLY == 'yearly'
        assert ReportingPeriod.PERIOD_TYPE_FISCAL_YEAR == 'fiscal_year'
        assert ReportingPeriod.PERIOD_TYPE_REPORTING_BATCH == 'reporting_batch'
        assert ReportingPeriod.PERIOD_TYPE_INPUT_WINDOW == 'input_window'


def test_submission_model_has_reporting_year_and_reporting_period_relationship():
    app = create_app('testing')

    with app.app_context():
        columns = Submission.__table__.columns

        assert 'reporting_year' in columns
        assert columns['reporting_year'].nullable is False
        assert 'reporting_period_id' in columns
        assert columns['reporting_period_id'].nullable is True
        assert 'owner_scope_type' in columns
        assert columns['owner_scope_type'].nullable is False
        assert 'owner_scope_code' in columns
        assert 'owner_scope_path' in columns
        assert 'subject_type' in columns
        assert 'subject_ref_id' in columns
        assert 'subject_ref_uuid' in columns
        assert 'subject_ref_code' in columns
        assert 'subject_ref_name' in columns
        assert 'access_policy_key' in columns
        assert columns['access_policy_key'].nullable is False

        foreign_keys = columns['reporting_period_id'].foreign_keys
        assert any(
            foreign_key.target_fullname == 'reporting_periods.id'
            for foreign_key in foreign_keys
        )

        assert Submission.reporting_period.property.mapper.class_ is ReportingPeriod
        assert ReportingPeriod.submissions.property.mapper.class_ is Submission

        period = ReportingPeriod(
            code='2026',
            name='Tahun 2026',
            period_type=ReportingPeriod.PERIOD_TYPE_YEARLY,
            year=2026,
        )
        submission = Submission(
            submission_number='SUB-2026-000001',
            reporting_year=2026,
            reporting_period=period,
            owner_scope_type='unit',
            owner_scope_code='ki',
            owner_scope_path=['kanwil-jabar', 'divisi-pelayanan-hukum', 'ki'],
            access_policy_key='submission.unit_owned',
            payload={},
        )

        assert submission.reporting_year == 2026
        assert submission.reporting_period.code == '2026'
        assert submission.owner_scope_code == 'ki'
        assert period.submissions[0].submission_number == 'SUB-2026-000001'

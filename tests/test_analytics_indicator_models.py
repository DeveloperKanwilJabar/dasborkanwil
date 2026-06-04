from app import create_app
from app.core.extensions import db


EXPECTED_ANALYTICS_INDICATOR_TABLES = {
    'analytics_report_definitions',
    'analytics_report_versions',
    'analytics_indicator_definitions',
    'analytics_indicator_versions',
    'analytics_report_version_indicators',
    'analytics_indicator_results',
    'analytics_indicator_progress_entries',
    'analytics_indicator_progress_items',
}


EXPECTED_ANALYTICS_INDICATOR_CLASS_TABLES = {
    'AnalyticsReportDefinition': 'analytics_report_definitions',
    'AnalyticsReportVersion': 'analytics_report_versions',
    'AnalyticsIndicatorDefinition': 'analytics_indicator_definitions',
    'AnalyticsIndicatorVersion': 'analytics_indicator_versions',
    'AnalyticsReportVersionIndicator': 'analytics_report_version_indicators',
    'AnalyticsIndicatorResult': 'analytics_indicator_results',
    'AnalyticsIndicatorProgressEntry': 'analytics_indicator_progress_entries',
    'AnalyticsIndicatorProgressItem': 'analytics_indicator_progress_items',
}


def test_analytics_indicator_models_are_registered_in_app_metadata():
    app = create_app('testing')

    with app.app_context():
        from app.modules.analytics.models import (
            AnalyticsIndicatorDefinition,
            AnalyticsIndicatorProgressEntry,
            AnalyticsIndicatorProgressItem,
            AnalyticsIndicatorResult,
            AnalyticsIndicatorVersion,
            AnalyticsReportDefinition,
            AnalyticsReportVersion,
            AnalyticsReportVersionIndicator,
        )

        tables = db.metadata.tables
        assert EXPECTED_ANALYTICS_INDICATOR_TABLES.issubset(set(tables.keys()))

        assert AnalyticsReportDefinition.__tablename__ == EXPECTED_ANALYTICS_INDICATOR_CLASS_TABLES['AnalyticsReportDefinition']
        assert AnalyticsReportVersion.__tablename__ == EXPECTED_ANALYTICS_INDICATOR_CLASS_TABLES['AnalyticsReportVersion']
        assert AnalyticsIndicatorDefinition.__tablename__ == EXPECTED_ANALYTICS_INDICATOR_CLASS_TABLES['AnalyticsIndicatorDefinition']
        assert AnalyticsIndicatorVersion.__tablename__ == EXPECTED_ANALYTICS_INDICATOR_CLASS_TABLES['AnalyticsIndicatorVersion']
        assert AnalyticsReportVersionIndicator.__tablename__ == EXPECTED_ANALYTICS_INDICATOR_CLASS_TABLES['AnalyticsReportVersionIndicator']
        assert AnalyticsIndicatorResult.__tablename__ == EXPECTED_ANALYTICS_INDICATOR_CLASS_TABLES['AnalyticsIndicatorResult']
        assert AnalyticsIndicatorProgressEntry.__tablename__ == EXPECTED_ANALYTICS_INDICATOR_CLASS_TABLES['AnalyticsIndicatorProgressEntry']
        assert AnalyticsIndicatorProgressItem.__tablename__ == EXPECTED_ANALYTICS_INDICATOR_CLASS_TABLES['AnalyticsIndicatorProgressItem']


def test_analytics_indicator_definition_layer_has_expected_uniques_indexes_and_columns():
    app = create_app('testing')

    with app.app_context():
        from app.modules.analytics.models import AnalyticsIndicatorVersion, AnalyticsReportVersion

        report_version_table = AnalyticsReportVersion.__table__
        indicator_version_table = AnalyticsIndicatorVersion.__table__

        report_unique_constraints = {
            constraint.name
            for constraint in report_version_table.constraints
            if constraint.__class__.__name__ == 'UniqueConstraint'
        }
        indicator_unique_constraints = {
            constraint.name
            for constraint in indicator_version_table.constraints
            if constraint.__class__.__name__ == 'UniqueConstraint'
        }
        report_index_names = {index.name for index in report_version_table.indexes}
        indicator_index_names = {index.name for index in indicator_version_table.indexes}

        assert 'uq_analytics_report_versions_def_ver_no' in report_unique_constraints
        assert 'uq_analytics_indicator_versions_def_ver_no' in indicator_unique_constraints

        assert 'ux_analytics_report_versions_one_cur_draft_per_def' in report_index_names
        assert 'ux_analytics_report_versions_one_cur_pub_per_def' in report_index_names
        assert 'ux_analytics_indicator_versions_one_cur_draft_per_def' in indicator_index_names
        assert 'ux_analytics_indicator_versions_one_cur_pub_per_def' in indicator_index_names

        for column_name in [
            'dataset_id',
            'dataset_version_id',
            'meta_description',
            'narrative_guidance_json',
        ]:
            assert column_name in indicator_version_table.columns


def test_analytics_indicator_result_and_progress_layer_has_expected_columns_and_foreign_keys():
    app = create_app('testing')

    with app.app_context():
        from app.modules.analytics.models import (
            AnalyticsIndicatorProgressEntry,
            AnalyticsIndicatorProgressItem,
            AnalyticsIndicatorResult,
        )

        result_table = AnalyticsIndicatorResult.__table__
        progress_entry_table = AnalyticsIndicatorProgressEntry.__table__
        progress_item_table = AnalyticsIndicatorProgressItem.__table__

        for column_name in [
            'dataset_run_id',
            'reporting_period_id',
            'qualitative_summary',
            'constraint_notes',
            'narrative_context_json',
        ]:
            assert column_name in result_table.columns

        for column_name in [
            'reporting_period_id',
            'qualitative_summary',
            'constraint_notes',
            'narrative_context_json',
        ]:
            assert column_name in progress_entry_table.columns

        for column_name in [
            'progress_entry_id',
            'status',
            'item_order',
            'narrative_context_json',
        ]:
            assert column_name in progress_item_table.columns

        result_fk_targets = {
            target_fullname
            for constraint in result_table.foreign_key_constraints
            for target_fullname in [next(iter(constraint.elements)).target_fullname]
        }
        progress_entry_fk_targets = {
            target_fullname
            for constraint in progress_entry_table.foreign_key_constraints
            for target_fullname in [next(iter(constraint.elements)).target_fullname]
        }
        progress_item_fk_targets = {
            target_fullname
            for constraint in progress_item_table.foreign_key_constraints
            for target_fullname in [next(iter(constraint.elements)).target_fullname]
        }

        assert 'analytics_dataset_runs.id' in result_fk_targets
        assert 'reporting_periods.id' in result_fk_targets
        assert 'reporting_periods.id' in progress_entry_fk_targets
        assert 'analytics_indicator_progress_entries.id' in progress_item_fk_targets


def test_analytics_indicator_models_have_expected_relationships():
    app = create_app('testing')

    with app.app_context():
        from app.modules.analytics.models import (
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
        from app.modules.submission.models import ReportingPeriod

        assert AnalyticsReportDefinition.versions.property.mapper.class_ is AnalyticsReportVersion
        assert AnalyticsReportVersion.definition.property.mapper.class_ is AnalyticsReportDefinition

        assert AnalyticsIndicatorDefinition.versions.property.mapper.class_ is AnalyticsIndicatorVersion
        assert AnalyticsIndicatorVersion.definition.property.mapper.class_ is AnalyticsIndicatorDefinition

        assert AnalyticsReportVersion.indicator_mappings.property.mapper.class_ is AnalyticsReportVersionIndicator
        assert AnalyticsReportVersionIndicator.report_version.property.mapper.class_ is AnalyticsReportVersion
        assert AnalyticsReportVersionIndicator.indicator_version.property.mapper.class_ is AnalyticsIndicatorVersion

        assert AnalyticsIndicatorVersion.dataset.property.mapper.class_ is AnalyticsDataset
        assert AnalyticsIndicatorVersion.dataset_version.property.mapper.class_ is AnalyticsDatasetVersion
        assert AnalyticsIndicatorVersion.results.property.mapper.class_ is AnalyticsIndicatorResult
        assert AnalyticsIndicatorVersion.progress_entries.property.mapper.class_ is AnalyticsIndicatorProgressEntry

        assert AnalyticsIndicatorResult.indicator_version.property.mapper.class_ is AnalyticsIndicatorVersion
        assert AnalyticsIndicatorResult.dataset_run.property.mapper.class_ is AnalyticsDatasetRun
        assert AnalyticsIndicatorResult.reporting_period.property.mapper.class_ is ReportingPeriod

        assert AnalyticsIndicatorProgressEntry.indicator_version.property.mapper.class_ is AnalyticsIndicatorVersion
        assert AnalyticsIndicatorProgressEntry.reporting_period.property.mapper.class_ is ReportingPeriod
        assert AnalyticsIndicatorProgressEntry.items.property.mapper.class_ is AnalyticsIndicatorProgressItem
        assert AnalyticsIndicatorProgressItem.progress_entry.property.mapper.class_ is AnalyticsIndicatorProgressEntry

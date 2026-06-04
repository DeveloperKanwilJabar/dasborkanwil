from app import create_app


def test_analytics_repository_contract_methods_exist():
    app = create_app('testing')

    with app.app_context():
        from app.modules.analytics.repositories import (
            AnalyticsIndicatorDefinitionRepository,
            AnalyticsIndicatorProgressEntryRepository,
            AnalyticsIndicatorResultRepository,
            AnalyticsIndicatorVersionRepository,
            AnalyticsReportDefinitionRepository,
            AnalyticsReportVersionRepository,
        )

        report_definition_repository = AnalyticsReportDefinitionRepository()
        report_version_repository = AnalyticsReportVersionRepository()
        indicator_definition_repository = AnalyticsIndicatorDefinitionRepository()
        indicator_version_repository = AnalyticsIndicatorVersionRepository()
        indicator_result_repository = AnalyticsIndicatorResultRepository()
        indicator_progress_repository = AnalyticsIndicatorProgressEntryRepository()

        for method_name in [
            'get_by_key',
            'list_by_status',
        ]:
            assert callable(getattr(report_definition_repository, method_name))

        for method_name in [
            'get_draft_version',
            'get_published_version',
            'get_next_version_number',
            'archive_published_others',
        ]:
            assert callable(getattr(report_version_repository, method_name))

        for method_name in [
            'get_by_key',
            'list_by_status',
        ]:
            assert callable(getattr(indicator_definition_repository, method_name))

        for method_name in [
            'get_draft_version',
            'get_published_version',
            'get_next_version_number',
            'archive_published_others',
        ]:
            assert callable(getattr(indicator_version_repository, method_name))

        for method_name in [
            'list_by_indicator_version',
            'get_latest_for_period',
        ]:
            assert callable(getattr(indicator_result_repository, method_name))
            assert callable(getattr(indicator_progress_repository, method_name))


def test_analytics_service_contract_methods_exist():
    app = create_app('testing')

    with app.app_context():
        from app.modules.analytics.services import (
            AnalyticsIndicatorResultService,
            AnalyticsIndicatorService,
            AnalyticsReportService,
        )

        report_service = AnalyticsReportService()
        indicator_service = AnalyticsIndicatorService()
        result_service = AnalyticsIndicatorResultService()

        for method_name in [
            'create_report_definition',
            'create_report_version',
            'publish_report_version',
        ]:
            assert callable(getattr(report_service, method_name))

        for method_name in [
            'create_indicator_definition',
            'create_indicator_version',
            'publish_indicator_version',
            'attach_indicator_to_report_version',
        ]:
            assert callable(getattr(indicator_service, method_name))

        for method_name in [
            'record_result',
            'record_progress_entry',
            'sync_result_from_progress',
        ]:
            assert callable(getattr(result_service, method_name))


def test_analytics_services_accept_injected_repositories():
    app = create_app('testing')

    with app.app_context():
        from app.modules.analytics.services import (
            AnalyticsIndicatorResultService,
            AnalyticsIndicatorService,
            AnalyticsReportService,
        )

        report_definition_repository = object()
        report_version_repository = object()
        indicator_definition_repository = object()
        indicator_version_repository = object()
        report_indicator_repository = object()
        result_repository = object()
        progress_repository = object()

        report_service = AnalyticsReportService(
            report_definition_repository=report_definition_repository,
            report_version_repository=report_version_repository,
        )
        indicator_service = AnalyticsIndicatorService(
            indicator_definition_repository=indicator_definition_repository,
            indicator_version_repository=indicator_version_repository,
            report_version_indicator_repository=report_indicator_repository,
        )
        result_service = AnalyticsIndicatorResultService(
            result_repository=result_repository,
            progress_entry_repository=progress_repository,
        )

        assert report_service.repository is report_definition_repository
        assert report_service.version_repository is report_version_repository
        assert indicator_service.repository is indicator_definition_repository
        assert indicator_service.version_repository is indicator_version_repository
        assert indicator_service.report_version_indicator_repository is report_indicator_repository
        assert result_service.repository is result_repository
        assert result_service.progress_entry_repository is progress_repository

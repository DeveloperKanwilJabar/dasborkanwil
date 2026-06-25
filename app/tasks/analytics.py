"""Celery tasks untuk Domain 5 analytics refresh."""

from app.celery_app import celery_app
from app.modules.analytics.services import AnalyticsDatasetRunService


@celery_app.task(name='analytics.refresh_dataset_run', bind=True, max_retries=2)
def refresh_dataset_run(self, run_id):
    """Eksekusi materialization dataset run yang sudah dibuat dengan status queued."""

    run = AnalyticsDatasetRunService().execute_queued_run(run_id)
    return {
        'run_id': run.id,
        'status': run.status,
        'error_code': getattr(run, 'error_code', None),
    }

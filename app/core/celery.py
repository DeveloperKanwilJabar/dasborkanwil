"""Integrasi Celery untuk background worker aplikasi.

File ini berada di core karena Celery adalah infrastructure adapter lintas domain,
mirip extension/config lain. Business logic task tetap berada di service layer
masing-masing domain.
"""

import os

from app import create_app


def make_celery(app=None):
    """Bangun Celery app yang menjalankan task di dalam Flask app context."""

    try:
        from celery import Celery
    except ImportError as exc:  # pragma: no cover - dipakai saat dependency belum terpasang
        raise RuntimeError('Celery belum terpasang. Jalankan install requirements.txt terlebih dahulu.') from exc

    flask_app = app or create_app(os.environ.get('FLASK_CONFIG', 'default'))
    celery = Celery(
        flask_app.import_name,
        broker=flask_app.config['CELERY_BROKER_URL'],
        backend=flask_app.config['CELERY_RESULT_BACKEND'],
        include=['app.tasks.analytics'],
    )
    celery.conf.update(
        task_ignore_result=flask_app.config.get('CELERY_TASK_IGNORE_RESULT', True),
        broker_connection_retry_on_startup=True,
        timezone=flask_app.config.get('APP_TIMEZONE', 'Asia/Jakarta'),
    )

    class FlaskContextTask(celery.Task):
        """Task base yang memastikan service punya Flask app context."""

        abstract = True

        def __call__(self, *args, **kwargs):
            with flask_app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = FlaskContextTask
    return celery

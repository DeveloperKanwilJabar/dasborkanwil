"""Celery application entrypoint untuk CLI worker.

Tetap disediakan di root package `app` agar command `celery -A app.celery_app.celery_app`
atau import lama `from app.celery_app import celery_app` stabil, sementara factory
infrastrukturnya tinggal di `app.core.celery`.
"""

from app.core.celery import make_celery


celery_app = make_celery()

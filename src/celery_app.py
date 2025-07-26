from celery import Celery
from config import Config


def make_celery():
    celery = Celery(
        "code_review_tasks",
        broker=Config.CELERY_BROKER_URL,
        backend=Config.CELERY_RESULT_BACKEND,
        include=["tasks"],
    )

    celery.conf.update(
        task_serializer="json",
        accept_content=["json"],
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
        task_time_limit=30 * 60,  # 30 minutes
        task_soft_time_limit=25 * 60,  # 25 minutes
        worker_prefetch_multiplier=1,
        worker_max_tasks_per_child=1000,
        # Fix for exception serialization issues
        result_accept_content=["json"],
        result_serializer="json",
        task_ignore_result=False,
        task_store_eager_result=True,
        # Better error handling
        task_reject_on_worker_lost=True,
        task_acks_late=True,
    )

    return celery


celery_app = make_celery()

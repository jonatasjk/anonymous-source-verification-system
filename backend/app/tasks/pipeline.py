"""
Celery Pipeline Tasks
---------------------
Three-stage chained pipeline:
  timestamp_submission → analyze_submission → generate_certificate

Each stage updates submission status in both PostgreSQL and Redis before
passing the submission_id to the next stage.

Failures are retried with exponential back-off (max 3 retries).
"""

import logging

from celery import chain

from app.tasks.celery_app import celery_app
from app.core.database import db_session, set_submission_status
from app.services.timestamping import timestamp_submission
from app.services.analysis import analyse_submission
from app.services.certificate import generate_certificate

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_BACKOFF = 60  # seconds


@celery_app.task(bind=True, max_retries=MAX_RETRIES, default_retry_delay=RETRY_BACKOFF)
def task_timestamp(self, submission_id: str) -> str:
    logger.info("[task_timestamp] submission=%s", submission_id)
    try:
        with db_session() as db:
            timestamp_submission(submission_id, db)
        set_submission_status(submission_id, "TIMESTAMPED")
        return submission_id
    except Exception as exc:
        logger.error("[task_timestamp] failed for %s: %s", submission_id, exc)
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=MAX_RETRIES, default_retry_delay=RETRY_BACKOFF)
def task_analyse(self, submission_id: str) -> str:
    logger.info("[task_analyse] submission=%s", submission_id)
    try:
        with db_session() as db:
            analyse_submission(submission_id, db)
        set_submission_status(submission_id, "ANALYZED")
        return submission_id
    except Exception as exc:
        logger.error("[task_analyse] failed for %s: %s", submission_id, exc)
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=MAX_RETRIES, default_retry_delay=RETRY_BACKOFF)
def task_certify(self, submission_id: str) -> str:
    logger.info("[task_certify] submission=%s", submission_id)
    try:
        with db_session() as db:
            cert_id = generate_certificate(submission_id, db)
        set_submission_status(submission_id, "COMPLETE")
        logger.info("[task_certify] issued %s for submission %s", cert_id, submission_id)
        return cert_id
    except Exception as exc:
        logger.error("[task_certify] failed for %s: %s", submission_id, exc)
        raise self.retry(exc=exc)


def enqueue_pipeline(submission_id: str) -> None:
    """
    Enqueue the three-stage pipeline as a Celery chain.
    Returns immediately; processing is asynchronous.
    """
    pipeline = chain(
        task_timestamp.s(submission_id),
        task_analyse.s(),
        task_certify.s(),
    )
    pipeline.delay()
    logger.info("Pipeline enqueued for submission %s", submission_id)

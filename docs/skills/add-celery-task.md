# Skill: Add a Celery Task

Use this skill when adding a new background task to the pipeline or Beat schedule.

## Rules

- Tasks use `db_session()` (context manager) — **never** FastAPI's `get_db()` dependency.
- Always bind tasks (`bind=True`) so you have access to `self` for retries.
- Use `autoretry_for` + `max_retries` rather than manual `self.retry()` calls where possible.
- Update `submission.status` and commit before returning so the status endpoint reflects progress.
- Log at INFO level on success, WARNING on retryable failure, ERROR on terminal failure.

## Template

```python
from celery import shared_task
from app.core.database import db_session
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def task_my_task(self, submission_id: str) -> None:
    try:
        with db_session() as db:
            # ... do work ...
            db.commit()
            logger.info("task_my_task completed for %s", submission_id)
    except Exception as exc:
        logger.warning("task_my_task failed for %s: %s", submission_id, exc)
        raise self.retry(exc=exc)
```

## Chaining into the pipeline

The main pipeline chain lives in `backend/app/tasks/pipeline.py`:

```python
chain(
    task_timestamp.s(submission_id),
    task_analyse.s(),
    task_certify.s(),
    # add your task here if it belongs in the main pipeline
)
```

## Adding a Beat (scheduled) task

Register in `backend/app/tasks/celery_app.py`:

```python
app.conf.beat_schedule = {
    "my-periodic-task": {
        "task": "app.tasks.my_module.task_my_task",
        "schedule": crontab(minute="*/5"),  # every 5 min
    },
    # … existing entries …
}
```

## Status updates

Use the Redis helper to keep the status endpoint responsive during long tasks:

```python
from app.core.database import set_submission_status
set_submission_status(submission_id, "MY_STAGE")
```

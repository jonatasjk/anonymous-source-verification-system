import uuid
import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db, get_submission_status
from app.models.db import Submission
from app.models.schemas import SubmissionResponse, SubmissionStatusResponse
from app.services.ingestion import ingest_files
from app.tasks.pipeline import enqueue_pipeline

router = APIRouter()
logger = logging.getLogger(__name__)

MAX_FILES = 20
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB per file


@router.post("/submissions", response_model=SubmissionResponse, status_code=202)
def create_submission(
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
):
    """
    Upload an evidence package (1–20 files, max 50 MB each).

    Returns a submission_id immediately. Processing (timestamping → analysis →
    certificate generation) happens asynchronously in the background.

    No source identity is collected: no authentication, no IP logging.
    """
    if not files:
        raise HTTPException(status_code=422, detail="At least one file is required.")
    if len(files) > MAX_FILES:
        raise HTTPException(status_code=422, detail=f"Maximum {MAX_FILES} files per submission.")

    for upload in files:
        # Validate file size
        upload.file.seek(0, 2)
        size = upload.file.tell()
        upload.file.seek(0)
        if size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"File '{upload.filename}' exceeds the 50 MB limit.",
            )

    try:
        submission_id = ingest_files(files, db)
    except Exception as exc:
        logger.error("Ingestion failed: %s", exc)
        raise HTTPException(status_code=500, detail="Ingestion failed.")

    enqueue_pipeline(submission_id)

    submission = db.query(Submission).filter(
        Submission.id == uuid.UUID(submission_id)
    ).first()
    return submission


@router.get("/submissions/{submission_id}/status", response_model=SubmissionStatusResponse)
def get_status(submission_id: str, db: Session = Depends(get_db)):
    """
    Poll submission processing status.

    Status values: INGESTED → TIMESTAMPED → ANALYZED → COMPLETE
    Reads from Redis for sub-millisecond response; falls back to PostgreSQL.
    """
    # Fast path: Redis cache
    cached = get_submission_status(submission_id)
    if cached:
        return SubmissionStatusResponse(
            submission_id=uuid.UUID(submission_id), status=cached
        )

    # Fallback: PostgreSQL
    try:
        sid = uuid.UUID(submission_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid submission_id format.")

    submission = db.query(Submission).filter(Submission.id == sid).first()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found.")

    return SubmissionStatusResponse(submission_id=submission.id, status=submission.status)

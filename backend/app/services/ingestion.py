"""
Ingestion Service
-----------------
Receives uploaded files, hashes them, builds the Merkle tree with proof paths,
encrypts each file at rest, and persists the submission record to PostgreSQL.

No source PII is stored at any point.
"""

import os
import uuid
import logging
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.crypto import sha256_bytes, derive_file_key, encrypt_bytes
from app.core.merkle import build_merkle_tree
from app.models.db import Submission, SubmissionFile

settings = get_settings()
logger = logging.getLogger(__name__)

# Heuristic map from extension to evidence type label
_EXT_TYPE_MAP: dict[str, str] = {
    ".mp3": "audio_recording",
    ".wav": "audio_recording",
    ".m4a": "audio_recording",
    ".pdf": "document",
    ".txt": "document",
    ".docx": "document",
    ".xlsx": "spreadsheet",
    ".csv": "spreadsheet",
    ".png": "image",
    ".jpg": "image",
    ".jpeg": "image",
}

_NAME_TYPE_MAP: dict[str, str] = {
    "email": "email_chain",
    "intake": "journalist_intake",
    "notes": "personal_notes",
    "memo": "analytical_memo",
    "comparison": "analytical_memo",
    "conversation": "audio_recording",
    "recording": "audio_recording",
}


def _detect_file_type(filename: str) -> str:
    lower = filename.lower()
    for keyword, ftype in _NAME_TYPE_MAP.items():
        if keyword in lower:
            return ftype
    ext = Path(filename).suffix.lower()
    return _EXT_TYPE_MAP.get(ext, "document")


def ingest_files(files: list[UploadFile], db: Session) -> str:
    """
    Hash, build Merkle tree, encrypt, and persist an evidence package.

    Returns the submission_id (UUIDv4 string).
    """
    submission_id = str(uuid.uuid4())
    master_key = settings.encryption_key

    storage_dir = Path(settings.storage_path) / submission_id
    storage_dir.mkdir(parents=True, exist_ok=True)

    file_data: list[tuple[str, bytes, str, str, int]] = []  # (filename, data, content_hash, filename_hash, size)

    for upload in files:
        data = upload.file.read()
        content_hash = sha256_bytes(data)
        filename_hash = sha256_bytes((upload.filename or "").encode())
        file_data.append((upload.filename or "", data, content_hash, filename_hash, len(data)))

    # Build Merkle tree from content hashes
    content_hashes = [fd[2] for fd in file_data]
    merkle_root, proof_paths = build_merkle_tree(content_hashes)

    # Persist submission record
    submission = Submission(
        id=uuid.UUID(submission_id),
        merkle_root=merkle_root,
        file_count=len(files),
        status="INGESTED",
    )
    db.add(submission)
    db.flush()

    # Encrypt and store each file; persist file metadata
    for idx, (filename, data, content_hash, filename_hash, size) in enumerate(file_data):
        file_key = derive_file_key(master_key, submission_id, content_hash)
        encrypted = encrypt_bytes(data, file_key)

        enc_path = storage_dir / f"{filename_hash}.enc"
        enc_path.write_bytes(encrypted)

        db_file = SubmissionFile(
            submission_id=uuid.UUID(submission_id),
            filename_hash=filename_hash,
            content_hash=content_hash,
            file_type=_detect_file_type(filename),
            size_bytes=size,
            merkle_proof_path=proof_paths[idx],
            encrypted_path=str(enc_path),
        )
        db.add(db_file)

    db.commit()
    logger.info("Ingested submission %s (%d files, root=%s)", submission_id, len(files), merkle_root)
    return submission_id

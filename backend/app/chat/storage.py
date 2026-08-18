"""
File Storage Abstraction for Chat Attachments.

Handles validation of file types, file size limits, safe file saving,
and file path resolution. Clean abstraction for future S3/Cloud migration.
"""

import os
import uuid
import pathlib
from typing import Tuple
from fastapi import HTTPException, UploadFile, status

# Allowed file extensions & mime types
ALLOWED_EXTENSIONS = {
    ".pdf", ".doc", ".docx", ".ppt", ".pptx",
    ".xls", ".xlsx", ".png", ".jpg", ".jpeg"
}

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-powerpoint",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "image/png",
    "image/jpeg",
    "image/jpg",
}

# 10 MB maximum file size limit
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024

# Base directory for storing attachments locally
STORAGE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads", "chat_attachments")


def init_storage_dir():
    """Ensure the uploads directory exists."""
    os.makedirs(STORAGE_DIR, exist_ok=True)


def save_attachment_file(file: UploadFile) -> Tuple[str, str, int, str]:
    """
    Validate and save an uploaded attachment file.

    Returns:
        (sanitized_original_filename, mime_type, file_size_bytes, storage_reference)
    """
    init_storage_dir()

    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Uploaded file must have a filename.",
        )

    # Sanitize filename & extract extension
    original_filename = os.path.basename(file.filename)
    ext = pathlib.Path(original_filename).suffix.lower()

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid file type '{ext}'. Allowed types: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    mime_type = file.content_type or "application/octet-stream"

    # Read content & check file size
    file_bytes = file.file.read()
    file_size = len(file_bytes)

    if file_size <= 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="File is empty.",
        )

    if file_size > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"File size exceeds maximum limit of {MAX_FILE_SIZE_BYTES // (1024 * 1024)}MB.",
        )

    # Generate unique stored filename to prevent collisions and path traversal
    unique_filename = f"{uuid.uuid4().hex}_{original_filename}"
    file_path = os.path.join(STORAGE_DIR, unique_filename)

    with open(file_path, "wb") as f:
        f.write(file_bytes)

    return original_filename, mime_type, file_size, unique_filename


def get_attachment_path(storage_reference: str) -> str:
    """Return the absolute path of a stored attachment file."""
    # Prevent directory traversal
    safe_reference = os.path.basename(storage_reference)
    full_path = os.path.join(STORAGE_DIR, safe_reference)
    if not os.path.exists(full_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attachment file not found.",
        )
    return full_path

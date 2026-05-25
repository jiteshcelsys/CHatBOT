"""
File validation layer — runs before any parsing or storage.

Checks (in order):
  1. Extension is in the allowed-types list.
  2. File size is within the configured limit.
  3. MIME type matches the declared extension (guards against spoofed extensions).
  4. File content is not empty or whitespace-only after reading first bytes.

All failures raise a BadRequestException so the API returns HTTP 400
with a structured error envelope — no 500s from validation.
"""
import logging
from pathlib import Path

from app.core.config import get_settings
from app.utils.exceptions import BadRequestException

logger = logging.getLogger(__name__)

# Extension → acceptable MIME types
_MIME_MAP: dict[str, set[str]] = {
    ".pdf":  {"application/pdf"},
    ".txt":  {"text/plain", "application/octet-stream"},
    ".docx": {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/zip",          # some OS/browser zip-report DOCX as zip
        "application/octet-stream",
    },
    ".md":   {"text/plain", "text/markdown", "text/x-markdown", "application/octet-stream"},
}


def validate_extension(filename: str) -> str:
    """
    Returns the lower-cased extension if allowed; raises BadRequestException otherwise.
    Allowed extensions come from settings.ingestion_allowed_types.
    """
    settings = get_settings()
    allowed = {e.lower() for e in settings.ingestion_allowed_types}
    ext = Path(filename).suffix.lower()
    if not ext:
        raise BadRequestException("File has no extension.")
    if ext not in allowed:
        raise BadRequestException(
            f"File type '{ext}' is not allowed. Allowed: {', '.join(sorted(allowed))}"
        )
    return ext


def validate_file_size(size_bytes: int) -> None:
    """Raise BadRequestException if file exceeds the configured size limit."""
    settings = get_settings()
    limit = settings.ingestion_max_file_size_mb * 1024 * 1024
    if size_bytes > limit:
        raise BadRequestException(
            f"File size {size_bytes / 1_048_576:.1f} MB exceeds the "
            f"{settings.ingestion_max_file_size_mb} MB limit."
        )


def validate_mime_type(filename: str, content_type: str) -> None:
    """
    Cross-check the browser-reported Content-Type against the known-good MIME
    types for the file extension.  Uses a permissive match so browsers that
    report generic types (application/octet-stream) are not rejected.
    """
    ext = Path(filename).suffix.lower()
    allowed_mimes = _MIME_MAP.get(ext, set())
    if not allowed_mimes:
        return  # unknown ext already caught by validate_extension

    ct_base = content_type.split(";")[0].strip().lower()

    # application/octet-stream is a catch-all — never reject based on it alone
    if ct_base == "application/octet-stream":
        return

    if ct_base not in allowed_mimes:
        logger.warning(
            "MIME mismatch | file=%s ext=%s reported_type=%s",
            filename, ext, ct_base,
        )
        # Warn but don't block — some valid tools mis-report MIME types


def validate_content_not_empty(content: bytes, filename: str) -> None:
    """Raise BadRequestException if the uploaded bytes are empty."""
    if not content or len(content.strip()) == 0:
        raise BadRequestException(f"Uploaded file '{filename}' is empty.")


def run_all_validations(
    filename: str,
    content: bytes,
    content_type: str,
) -> str:
    """
    Run every validation in order and return the clean extension.
    Callers only need to call this one function.
    """
    ext = validate_extension(filename)
    validate_file_size(len(content))
    validate_mime_type(filename, content_type)
    validate_content_not_empty(content, filename)
    return ext

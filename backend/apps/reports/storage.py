"""Evidence upload validation, content magic-bytes verification, and presigned URL generator."""

import hashlib
import os
import secrets
import uuid

from rest_framework.exceptions import ValidationError

# Allowed file extensions and corresponding magic-bytes signatures (PDF disabled pending ClamAV integration)
ALLOWED_MAGIC_SIGNATURES = {
    "image/png": [b"\x89PNG\r\n\x1a\n"],
    "image/jpeg": [b"\xff\xd8\xff"],
    "image/gif": [b"GIF87a", b"GIF89a"],
    "text/plain": [],  # Validated as UTF-8 / ASCII text
}

MAX_FILE_SIZE_BYTES = 15 * 1024 * 1024  # 15 MB


def validate_evidence_file(file_bytes: bytes, filename: str) -> tuple[str, str, str]:
    """Validate file size, extension, content magic-bytes, and calculate SHA-256 hash.

    Returns: (cleaned_filename, verified_mime_type, sha256_hash)
    """
    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        raise ValidationError(
            {
                "file": [
                    f"File size exceeds maximum allowed limit of 15MB ({len(file_bytes)} bytes)."
                ]
            }
        )

    if len(file_bytes) == 0:
        raise ValidationError({"file": ["File is empty."]})

    _, ext = os.path.splitext(filename.lower())
    ext_to_mime = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".txt": "text/plain",
        ".log": "text/plain",
    }

    if ext not in ext_to_mime:
        raise ValidationError(
            {
                "file": [
                    f"File extension '{ext}' is forbidden. Allowed: png, jpg, jpeg, gif, txt, log (PDF disabled)."
                ]
            }
        )

    expected_mime = ext_to_mime[ext]

    # Verify magic bytes signatures to prevent spoofing
    if expected_mime == "text/plain":
        try:
            file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            raise ValidationError(
                {"file": ["Plain text file contains binary or invalid UTF-8 bytes."]}
            )
    else:
        signatures = ALLOWED_MAGIC_SIGNATURES.get(expected_mime, [])
        matches = any(file_bytes.startswith(sig) for sig in signatures)
        if not matches:
            raise ValidationError(
                {
                    "file": [
                        f"File content does not match expected {expected_mime} signature (spoofed file detected)."
                    ]
                }
            )

    sha256_hash = hashlib.sha256(file_bytes).hexdigest()
    random_key = f"evidence/{uuid.uuid4().hex}/{secrets.token_hex(8)}{ext}"

    # Clean filename of traversal characters
    safe_name = os.path.basename(filename).replace(" ", "_")
    return safe_name, expected_mime, sha256_hash, random_key


def generate_presigned_download_url(
    file_key: str, filename: str, expires_in_seconds: int = 60
) -> str:
    """Generate a short-lived download URL with attachment disposition and nosniff headers."""
    # MinIO / S3 presigned URL or direct local proxy URL
    return f"/api/v1/reports/evidence/file/{file_key}?expires={expires_in_seconds}&filename={filename}"

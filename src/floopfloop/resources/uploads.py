"""``client.uploads.create()`` — presign + S3 PUT for refine attachments."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

import httpx

from ..errors import FloopError

if TYPE_CHECKING:
    from .._client import FloopClient

EXT_TO_MIME: dict[str, str] = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".svg": "image/svg+xml",
    ".webp": "image/webp",
    ".ico": "image/x-icon",
    ".pdf": "application/pdf",
    ".txt": "text/plain",
    ".csv": "text/csv",
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}

MAX_BYTES = 5 * 1024 * 1024


def guess_mime_type(file_name: str) -> str | None:
    """Return the backend-allowlisted mime type for ``file_name`` or ``None``."""
    dot = file_name.lower().rfind(".")
    if dot < 0:
        return None
    return EXT_TO_MIME.get(file_name[dot:].lower())


class Uploads:
    def __init__(self, client: FloopClient) -> None:
        self._client = client

    def create(
        self,
        *,
        file_name: str,
        content: bytes | None = None,
        path: str | Path | None = None,
        file_type: str | None = None,
    ) -> dict[str, Any]:
        """Presign the upload, PUT the bytes, return the attachment descriptor.

        Pass exactly one of ``content`` (bytes) or ``path`` (on-disk file).
        ``file_type`` overrides the extension-based mime guess; it must still
        be on the backend allowlist.
        """
        if (content is None) == (path is None):
            raise TypeError(
                "Uploads.create: pass exactly one of `content` or `path`"
            )

        if content is None:
            assert path is not None
            content = Path(path).read_bytes()

        mime = file_type or guess_mime_type(file_name)
        if mime is None or mime not in EXT_TO_MIME.values():
            raise FloopError(
                code="VALIDATION_ERROR",
                message=(
                    f"Unsupported file type for {file_name}. "
                    "Allowed: png, jpg, gif, svg, webp, ico, pdf, txt, csv, doc, docx."
                ),
                status=0,
            )

        size = len(content)
        if size > MAX_BYTES:
            raise FloopError(
                code="VALIDATION_ERROR",
                message=f"{file_name} is {size // (1024 * 1024)} MB — the upload limit is 5 MB.",
                status=0,
            )

        presign: dict[str, Any] = self._client._request(
            "POST",
            "/api/v1/uploads",
            json={"fileName": file_name, "fileType": mime, "fileSize": size},
        )

        try:
            put = self._client._http.put(
                presign["uploadUrl"],
                content=content,
                headers={"Content-Type": mime},
            )
        except httpx.HTTPError as err:
            raise FloopError(
                code="NETWORK_ERROR",
                message=f"S3 upload failed ({err})",
                status=0,
            ) from err

        if put.status_code >= 400:
            raise FloopError(
                code="UNKNOWN",
                message=f"S3 upload failed ({put.status_code} {put.reason_phrase})",
                status=put.status_code,
            )

        return {
            "key": presign["key"],
            "fileName": file_name,
            "fileType": mime,
            "fileSize": size,
        }

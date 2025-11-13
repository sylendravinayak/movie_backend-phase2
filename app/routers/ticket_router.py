from typing import Dict, Any, Optional
import uuid

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Response, status
from pydantic import BaseModel

router = APIRouter(prefix="/tickets", tags=["Tickets"])

# In-memory storage: ticket_id -> {filename, content_type, data, size, title}
_storage: Dict[str, Dict[str, Any]] = {}

# Allowed types and limits
ALLOWED_CONTENT_TYPES = {"application/pdf", "image/pdf", "image/jpeg", "image/png"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB (change as needed)


class TicketResponse(BaseModel):
    id: str
    filename: str
    content_type: str
    size: int
    download_url: str
    title: Optional[str] = None


def _check_magic_bytes(content: bytes, content_type: str) -> bool:
    # Minimal magic-bytes checks for extra safety
    if content_type in ("application/pdf", "image/pdf"):
        return content.startswith(b"%PDF")
    if content_type == "image/jpeg":
        return content.startswith(b"\xff\xd8\xff")
    if content_type == "image/png":
        return content.startswith(b"\x89PNG") or content.startswith(b"\x89PNG\r\n\x1a\n")
    return False


@router.post("/", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
async def upload_ticket(file: UploadFile = File(...), title: Optional[str] = Form(None)):
    """
    Upload a ticket file (multipart/form-data).
    - Allowed content types: application/pdf, image/jpeg, image/png
    - Max file size: MAX_FILE_SIZE
    Returns ticket id and download URL.
    """
    content_type = file.content_type or ""
    if content_type.lower() not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type: {content_type}. Allowed: PDF, JPEG, PNG.",
        )

    data = await file.read()
    size = len(data)

    if size == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file uploaded.")

    if size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Max allowed size is {MAX_FILE_SIZE} bytes.",
        )

    # Magic byte check
    if not _check_magic_bytes(data, content_type.lower()):
        # allow a fallback: check by file extension if magic bytes fail might be overly strict
        # but for security prefer rejecting mismatched types
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="File content does not match declared content type.",
        )

    ticket_id = str(uuid.uuid4())
    _storage[ticket_id] = {
        "filename": file.filename,
        "content_type": content_type,
        "data": data,
        "size": size,
        "title": title,
    }

    download_url = f"/tickets/{ticket_id}/download"

    return TicketResponse(
        id=ticket_id,
        filename=file.filename,
        content_type=content_type,
        size=size,
        download_url=download_url,
        title=title,
    )


@router.get("/{ticket_id}/download")
async def download_ticket(ticket_id: str):
    """
    Download ticket bytes with proper content headers.
    Returns 404 if ticket_id not found.
    """
    item = _storage.get(ticket_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found.")

    headers = {
        "Content-Disposition": f'attachment; filename="{item["filename"]}"'
    }
    return Response(content=item["data"], media_type=item["content_type"], headers=headers)


@router.get("/{ticket_id}")
async def ticket_metadata(ticket_id: str):
    """
    Get ticket metadata (no file content).
    """
    item = _storage.get(ticket_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found.")
    return {
        "id": ticket_id,
        "filename": item["filename"],
        "content_type": item["content_type"],
        "size": item["size"],
        "title": item.get("title"),
    }
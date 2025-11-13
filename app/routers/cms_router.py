from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from fastapi.responses import JSONResponse, StreamingResponse
from typing import Any, Dict
from uuid import uuid4
from pathlib import Path
import re

from schemas.cms_schema import LandingContent, LandingContentUpdate
from utils.auth.jwt_bearer import getcurrent_user
from crud.cms import read_content, write_content, store_file, get_file

router = APIRouter(prefix="/cms", tags=["CMS"])

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg"}
MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MiB


def _sanitize_filename(name: str) -> str:
    base = name.split("/")[-1].split("\\")[-1]
    base = re.sub(r"\s+", "_", base)
    base = "".join(ch for ch in base if ch.isalnum() or ch in {".", "-", "_"})
    return base or f"file_{uuid4().hex}"


def _deep_merge(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    for k, v in b.items():
        if isinstance(v, dict) and isinstance(a.get(k), dict):
            _deep_merge(a[k], v)
        else:
            a[k] = v
    return a


@router.get("/landing", response_model=LandingContent, summary="Public landing content")
async def get_landing():
    content = await read_content()
    return content


@router.get("/admin/landing", response_model=LandingContent, summary="Get landing content (admin)")
async def admin_get_landing(user: str = Depends(getcurrent_user)):
    return await read_content()


@router.put("/admin/landing", response_model=LandingContent, summary="Update landing content (admin)")
async def admin_update_landing(
    payload: LandingContentUpdate,
    user: str = Depends(getcurrent_user),
    expected_version: int | None = None
):
    current = await read_content()
    update_data = payload.dict(exclude_unset=True)
    _deep_merge(current, update_data)

    try:
        saved = await write_content(current, expected_version=expected_version)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(ve))
    return saved


@router.post("/admin/upload", summary="Upload image/file (admin)")
async def admin_upload_file(
    file: UploadFile = File(...),
    user: str = Depends(getcurrent_user)
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    sanitized = _sanitize_filename(file.filename)
    suffix = Path(sanitized).suffix.lower()

    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{suffix}'. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )

    data = await file.read()
    if len(data) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds max size {MAX_FILE_SIZE_BYTES} bytes"
        )

    unique_name = f"{sanitized.rsplit('.', 1)[0]}-{uuid4().hex}{suffix}"
    file_id = await store_file(
        filename=unique_name,
        content_type=file.content_type or "application/octet-stream",
        data=data,
        metadata={"original_name": file.filename}
    )
    url = f"/cms/file/{file_id}"
    return JSONResponse({"url": url, "id": file_id, "filename": unique_name})


@router.get("/file/{file_id}", summary="Fetch an uploaded file")
async def get_uploaded_file(file_id: str):
    stream, filename, content_type = await get_file(file_id)
    if stream is None:
        raise HTTPException(status_code=404, detail="File not found")

    async def iterator():
        while True:
            chunk = await stream.readchunk()
            if not chunk:
                break
            yield chunk

    headers = {"Content-Disposition": f'inline; filename="{filename}"'}
    return StreamingResponse(iterator(), media_type=content_type, headers=headers)


@router.get("/admin/raw", summary="Return raw JSON content (admin)")
async def admin_raw(user: str = Depends(getcurrent_user)):
    content = await read_content()
    return JSONResponse(content)
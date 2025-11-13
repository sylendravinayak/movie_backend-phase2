from datetime import datetime
from typing import Dict, Any, Optional
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorGridFSBucket

from model.cms import CMSContent
from database import get_mongo_db  # ADD THIS IMPORT

BUCKET_NAME = "cms_uploads"


def _deep_merge(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    for k, v in b.items():
        if isinstance(v, dict) and isinstance(a.get(k), dict):
            _deep_merge(a[k], v)
        else:
            a[k] = v
    return a


async def _ensure_content() -> CMSContent:
    doc = await CMSContent.find_one(CMSContent.id == "landing")
    if not doc:
        doc = CMSContent()
        await doc.insert()
    return doc


async def read_content() -> Dict[str, Any]:
    doc = await _ensure_content()
    data = doc.to_public_dict()
    if isinstance(data.get("updated_at"), datetime):
        data["updated_at"] = data["updated_at"].isoformat()
    return data


async def write_content(updated: Dict[str, Any], expected_version: Optional[int] = None) -> Dict[str, Any]:
    doc = await _ensure_content()

    if expected_version is not None and expected_version != doc.version:
        raise ValueError(f"Version mismatch: expected {expected_version}, found {doc.version}")

    current = doc.to_public_dict()
    _deep_merge(current, updated)

    doc.title = current["title"]
    doc.subtitle = current["subtitle"]
    doc.hero_image = current["hero_image"]
    doc.sections = current["sections"]
    doc.ctas = current["ctas"]
    doc.featured_movies = current["featured_movies"]
    doc.seo = current["seo"]
    doc.updated_at = datetime.utcnow()
    doc.version = doc.version + 1

    await doc.replace()

    out = doc.to_public_dict()
    out["updated_at"] = doc.updated_at.isoformat()
    return out


def get_gridfs_bucket() -> AsyncIOMotorGridFSBucket:
    mongo_db = get_mongo_db()
    return AsyncIOMotorGridFSBucket(mongo_db, bucket_name=BUCKET_NAME)


async def store_file(filename: str, content_type: str, data: bytes, metadata: Dict[str, Any]) -> str:
    bucket = get_gridfs_bucket()
    file_id = await bucket.upload_from_stream(
        filename,
        data,
        metadata={"content_type": content_type, **metadata},
    )
    return str(file_id)


async def get_file(file_id: str):
    bucket = get_gridfs_bucket()
    try:
        oid = ObjectId(file_id)
    except Exception:
        return None, None, None
    try:
        stream = await bucket.open_download_stream(oid)
    except Exception:
        return None, None, None
    return stream, stream.filename, stream.metadata.get("content_type", "application/octet-stream")
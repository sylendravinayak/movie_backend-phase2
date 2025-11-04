from __future__ import annotations

from motor.motor_asyncio import AsyncIOMotorDatabase
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from datetime import datetime
from bson import ObjectId
from typing import List, Optional, Tuple
import subprocess
import os
import requests
import base64
import shutil

# Project settings
from utils.config import Settings
settings = Settings()

# Use the existing SQLAlchemy URL from app.database
try:
    # Import lazily so this file can be imported in tooling contexts too
    from database import SQLALCHEMY_DATABASE_URL as PG_URL  # e.g. postgresql://user:pass@host/db
except Exception:
    PG_URL = os.getenv("DATABASE_URL", "")

# Max allowed by GitHub Content API (base64 ~ 33% overhead). We keep a conservative 90MB raw limit.
MAX_FILE_SIZE = 90 * 1024 * 1024


class BackupService:
    def __init__(self, db: AsyncIOMotorDatabase, postgres_db: Session | None = None):
        # Raw motor collections (simple, no schema coupling)
        self.backups_collection = db.backups
        self.restores_collection = db.restores

        self.postgres_db = postgres_db

        # GitHub config: set via environment (recommended)
        # GITHUB_BACKUP_TOKEN: a classic PAT or fine-grained PAT with contents:write
        # GITHUB_BACKUP_OWNER: org or username
        # GITHUB_BACKUP_REPO: repo name
        self.github_token = "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"
        self.github_repo = "backup"
        self.github_owner = "sylendravinayak"
        self.github_branch = "main"

        # Mongo config
        self.mongo_url = settings.MONGODB_URL
        # Prefer db.name; otherwise allow explicit env or default
        self.mongo_db_name = getattr(db, "name", None) or os.getenv("MONGO_DB", "mydb")

    def _generate_operation_id(self, op_type: str = "backup") -> str:
        prefix = "BKUP" if op_type == "backup" else "REST"
        return f"{prefix}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

    async def create_postgres_backup(self, tables: Optional[List[str]] = None) -> Tuple[str, str, int]:
        """
        Uses pg_dump with --dbname="{PG_URL}" so you don't need to split host/user/etc.
        Requires pg_dump in PATH. Consider using the existing project helper if you prefer auto-discovery.
        """
        if not PG_URL:
            raise HTTPException(status_code=500, detail="DATABASE_URL / SQLALCHEMY_DATABASE_URL not configured")

        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        filename = f"postgres_backup_{timestamp}.sql"
        backups_dir = os.path.join("backups")
        filepath = os.path.join(backups_dir, filename)

        os.makedirs(backups_dir, exist_ok=True)

        # Build pg_dump command
        base = ['pg_dump', f'--dbname={PG_URL}', '--clean', '--if-exists', f'-f', filepath]
        if tables:
            for t in tables:
                base.extend(['-t', t])

        result = subprocess.run(base, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"PostgreSQL backup failed: {result.stderr}")

        size = os.path.getsize(filepath)
        return filepath, filename, size

    async def create_mongodb_backup(self, collections: Optional[List[str]] = None) -> Tuple[str, str, int]:
        """
        Uses mongodump with the configured Mongo URI and db name.
        Requires mongodump in PATH.
        """
        if not self.mongo_url:
            raise HTTPException(status_code=500, detail="MONGODB_URL not configured")

        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        backups_dir = os.path.join("backups")
        os.makedirs(backups_dir, exist_ok=True)

        filename = f"mongodb_{timestamp}.archive.gz"
        archive_file = os.path.join(backups_dir, filename)

        base = ['mongodump', f'--uri={self.mongo_url}', f'--db={self.mongo_db_name}', f'--archive={archive_file}', '--gzip']
        if collections:
            for c in collections:
                base.append(f'--collection={c}')

        result = subprocess.run(base, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"MongoDB backup failed: {result.stderr}")

        size = os.path.getsize(archive_file)
        return archive_file, filename, size

    async def upload_to_github(self, filepath: str, filename: str) -> str:
        """
        Uploads a file via GitHub Contents API to the configured repo/branch.
        """
        if not (self.github_token and self.github_owner and self.github_repo):
            raise HTTPException(status_code=500, detail="GitHub backup env not set (GITHUB_BACKUP_TOKEN/OWNER/REPO)")

        file_size = os.path.getsize(filepath)
        if file_size > MAX_FILE_SIZE:
            raise Exception(
                f"File too large for GitHub: {file_size / 1024 / 1024:.2f} MB. "
                f"Maximum allowed: {MAX_FILE_SIZE / 1024 / 1024:.0f} MB. "
                f"Consider using S3 or Backblaze B2 for large backups."
            )

        with open(filepath, 'rb') as f:
            content = base64.b64encode(f.read()).decode()

        url = f"https://api.github.com/repos/{self.github_owner}/{self.github_repo}/contents/{filename}"

        headers = {
            "Authorization": f"token {self.github_token}",
            "Accept": "application/vnd.github.v3+json"
        }

        data = {
            "message": f"Backup: {filename}",
            "content": content,
            "branch": self.github_branch
        }

        response = requests.put(url, headers=headers, json=data)
        if response.status_code not in (200, 201):
            try:
                detail = response.json()
            except Exception:
                detail = response.text
            raise Exception(f"GitHub upload failed: {detail}")

        return response.json()['content']['html_url']

    async def download_from_github(self, github_url: str, filename: str) -> str:
        """
        Downloads a raw file from GitHub (given the html_url returned by upload).
        """
        if not self.github_token:
            raise HTTPException(status_code=500, detail="GITHUB_BACKUP_TOKEN not configured")

        raw_url = github_url.replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")

        headers = {"Authorization": f"token {self.github_token}"}
        response = requests.get(raw_url, headers=headers)
        if response.status_code != 200:
            raise Exception(f"GitHub download failed: {response.status_code}")

        restores_dir = os.path.join("restores")
        os.makedirs(restores_dir, exist_ok=True)
        filepath = os.path.join(restores_dir, filename)

        with open(filepath, 'wb') as f:
            f.write(response.content)

        return filepath

    async def restore_postgres(self, filepath: str) -> bool:
        """
        Restores using psql --dbname=URL -f filepath
        """
        if not PG_URL:
            raise HTTPException(status_code=500, detail="DATABASE_URL / SQLALCHEMY_DATABASE_URL not configured")

        cmd = ['psql', f'--dbname={PG_URL}', '-f', filepath]
        result = subprocess.run(cmd, capture_output=True, text=True)
        # psql may return 0 even with NOTICEs; fail if ERROR appears
        if result.returncode != 0 or "ERROR" in (result.stderr or ""):
            raise Exception(f"PostgreSQL restore failed: {result.stderr}")
        return True

    async def restore_mongodb(self, filepath: str) -> bool:
        """
        Restores using mongorestore to the configured db.
        """
        if not self.mongo_url:
            raise HTTPException(status_code=500, detail="MONGODB_URL not configured")

        print(f"Restoring MongoDB from: {filepath}")
        print(f"Target database: {self.mongo_db_name}")

        cmd = [
            'mongorestore',
            f'--uri={self.mongo_url}',
            f'--nsInclude={self.mongo_db_name}.*',
            f'--archive={filepath}',
            '--gzip',
            '--drop',
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        print(f"Restore output:\n{result.stderr}")

        if result.returncode != 0 and "successfully" not in (result.stderr or "").lower():
            raise Exception(f"MongoDB restore failed: {result.stderr}")

        return True

    async def create_backup(self, data, admin_id: int):
        """
        data must have:
          - backupType: 'postgres' | 'mongodb' | 'both'
          - tables: Optional[List[str]]
          - notes: Optional[str]
        Persists a document in Mongo 'backups' collection.
        """
        operation_id = self._generate_operation_id("backup")

        backup_doc = {
            "operationId": operation_id,
            "backupType": getattr(data.backupType, "value", str(data.backupType)),
            "status": "in_progress",
            "url": None,
            "filePath": None,
            "size": None,
            "tables": getattr(data, "tables", None),
            "performedBy": admin_id,
            "startedAt": datetime.utcnow(),
            "completedAt": None,
            "errorMessage": None,
            "notes": getattr(data, "notes", None),
        }

        result = await self.backups_collection.insert_one(backup_doc)
        backup_id = str(result.inserted_id)

        try:
            # Create artifacts
            if str(data.backupType) in ("postgres",) or getattr(data.backupType, "value", "") == "postgres":
                filepath, filename, size = await self.create_postgres_backup(getattr(data, "tables", None))
            elif str(data.backupType) in ("mongodb",) or getattr(data.backupType, "value", "") == "mongodb":
                filepath, filename, size = await self.create_mongodb_backup(getattr(data, "tables", None))
            else:
                # both
                pg_path, pg_name, pg_size = await self.create_postgres_backup()
                mongo_path, mongo_name, mongo_size = await self.create_mongodb_backup()
                filepath = [pg_path, mongo_path]
                filename = [pg_name, mongo_name]
                size = pg_size + mongo_size

            # Upload to GitHub
            if isinstance(filepath, list):
                github_urls = []
                for fp, fn in zip(filepath, filename):
                    github_url = await self.upload_to_github(fp, fn)
                    github_urls.append(github_url)
                    # Clean local file
                    try:
                        os.remove(fp)
                    except Exception:
                        pass
                github_url = ", ".join(github_urls)
                file_path_field = filename
            else:
                github_url = await self.upload_to_github(filepath, filename)
                try:
                    os.remove(filepath)
                except Exception:
                    pass
                file_path_field = filename

            await self.backups_collection.update_one(
                {"_id": ObjectId(backup_id)},
                {"$set": {
                    "status": "completed",
                    "url": github_url,
                    "filePath": file_path_field,
                    "size": size,
                    "completedAt": datetime.utcnow(),
                }}
            )

        except Exception as e:
            await self.backups_collection.update_one(
                {"_id": ObjectId(backup_id)},
                {"$set": {
                    "status": "failed",
                    "errorMessage": f"{type(e).__name__}: {str(e)}",
                    "completedAt": datetime.utcnow()
                }}
            )
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

        backup = await self.backups_collection.find_one({"_id": ObjectId(backup_id)})
        backup['id'] = str(backup.pop('_id'))
        return backup  # dict compatible with your existing responses

    async def restore_backup(self, data, admin_id: int):
        """
        data must have:
          - backupId: str (ObjectId)
          - restoreType: 'postgres' | 'mongodb' | 'both'
          - notes: Optional[str]
        Persists a document in Mongo 'restores' collection.
        """
        if not ObjectId.is_valid(data.backupId):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid backup ID")

        backup = await self.backups_collection.find_one({"_id": ObjectId(data.backupId)})
        if not backup:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Backup not found")
        if backup.get('status') != "completed":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Backup is not completed")

        operation_id = self._generate_operation_id("restore")

        restore_doc = {
            "operationId": operation_id,
            "backupType": getattr(data.restoreType, "value", str(data.restoreType)),
            "status": "in_progress",
            "sourceBackupId": data.backupId,
            "sourceUrl": backup.get('url'),
            "performedBy": admin_id,
            "startedAt": datetime.utcnow(),
            "completedAt": None,
            "errorMessage": None,
            "notes": getattr(data, "notes", None),
        }

        result = await self.restores_collection.insert_one(restore_doc)
        restore_id = str(result.inserted_id)

        try:
            urls = backup['url'].split(", ") if ", " in backup['url'] else [backup['url']]
            filenames = backup['filePath'] if isinstance(backup['filePath'], list) else [backup['filePath']]

            if str(data.restoreType) in ("postgres",) or getattr(data.restoreType, "value", "") == "postgres":
                filepath = await self.download_from_github(urls[0], filenames[0])
                await self.restore_postgres(filepath)
                try:
                    os.remove(filepath)
                except Exception:
                    pass

            elif str(data.restoreType) in ("mongodb",) or getattr(data.restoreType, "value", "") == "mongodb":
                idx = 1 if len(urls) > 1 else 0
                filepath = await self.download_from_github(urls[idx], filenames[idx])
                await self.restore_mongodb(filepath)
                try:
                    os.remove(filepath)
                except Exception:
                    pass

            else:
                # both
                for url, filename in zip(urls, filenames):
                    filepath = await self.download_from_github(url, filename)
                    if filename.endswith('.sql'):
                        await self.restore_postgres(filepath)
                    else:
                        await self.restore_mongodb(filepath)
                    try:
                        os.remove(filepath)
                    except Exception:
                        pass

            await self.restores_collection.update_one(
                {"_id": ObjectId(restore_id)},
                {"$set": {
                    "status": "completed",
                    "completedAt": datetime.utcnow()
                }}
            )

        except Exception as e:
            await self.restores_collection.update_one(
                {"_id": ObjectId(restore_id)},
                {"$set": {
                    "status": "failed",
                    "errorMessage": f"{type(e).__name__}: {str(e)}",
                    "completedAt": datetime.utcnow()
                }}
            )
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

        restore = await self.restores_collection.find_one({"_id": ObjectId(restore_id)})
        restore['id'] = str(restore.pop('_id'))
        return restore

    async def list_backups(self, limit: int = 50) -> List[dict]:
        cursor = self.backups_collection.find().sort("startedAt", -1).limit(limit)
        out: List[dict] = []
        async for backup in cursor:
            backup['id'] = str(backup.pop('_id'))
            out.append(backup)
        return out

    async def list_restores(self, limit: int = 50) -> List[dict]:
        cursor = self.restores_collection.find().sort("startedAt", -1).limit(limit)
        out: List[dict] = []
        async for restore in cursor:
            restore['id'] = str(restore.pop('_id'))
            out.append(restore)
        return out

    async def get_backup(self, backup_id: str) -> dict:
        if not ObjectId.is_valid(backup_id):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid backup ID")
        backup = await self.backups_collection.find_one({"_id": ObjectId(backup_id)})
        if not backup:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Backup not found")
        backup['id'] = str(backup.pop('_id'))
        return backup

    async def delete_backup(self, backup_id: str) -> dict:
        if not ObjectId.is_valid(backup_id):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid backup ID")
        await self.backups_collection.delete_one({"_id": ObjectId(backup_id)})
        return {"message": "Backup deleted"}
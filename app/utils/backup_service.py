import asyncio
import os
import sys
import gzip
import json
import shutil
import hashlib
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
import subprocess
import glob
import platform

BACKUPS_ROOT = Path(os.getenv("BACKUPS_ROOT", "backups")).resolve()

def _get_pg_url() -> str:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from app.database import SQLALCHEMY_DATABASE_URL  # type: ignore
    return SQLALCHEMY_DATABASE_URL

def _get_mongo_uri_and_db() -> tuple[str, str]:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from app.database import db as motor_db  # type: ignore
    mongo_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    return (mongo_uri, str(motor_db.name))

def _candidate_paths_windows(exe: str, family: str) -> List[Path]:
    exe_with_ext = exe if exe.lower().endswith(".exe") else exe + ".exe"
    candidates: List[Path] = []
    if family == "postgres":
        roots = [
            Path("C:/Program Files/PostgreSQL"),
            Path("C:/Program Files (x86)/PostgreSQL"),
        ]
        for root in roots:
            if root.exists():
                for version_dir in root.iterdir():
                    bin_dir = version_dir / "bin"
                    candidate = bin_dir / exe_with_ext
                    if candidate.exists():
                        candidates.append(candidate)
    elif family == "mongo":
        # MongoDB Database Tools default path
        roots = [
            Path("C:/Program Files/MongoDB/Tools"),
            Path("C:/Program Files/MongoDB/Server"),
        ]
        for root in roots:
            if root.exists():
                # search all version/bin combinations
                for version_dir in root.rglob("bin"):
                    candidate = version_dir / exe_with_ext
                    if candidate.exists():
                        candidates.append(candidate)
    return candidates

def _resolve_exe(exe_name: str, bin_env: Optional[str], family: Optional[str]) -> str:
    """
    Resolve path to executable, honoring BIN env overrides, PATH, and common Windows install locations.
    """
    # 1) BIN env (e.g., PG_BIN, MONGO_BIN)
    if bin_env:
        bin_dir = os.getenv(bin_env, "")
        if bin_dir:
            p = Path(bin_dir) / exe_name
            if os.name == "nt" and not p.suffix:
                p = p.with_suffix(".exe")
            if p.exists():
                return str(p)

    # 2) PATH
    which = shutil.which(exe_name)
    if which:
        return which

    # 3) Windows common install paths
    if os.name == "nt" and family:
        candidates = _candidate_paths_windows(exe_name, family)
        if candidates:
            # pick the latest (by version dir name sorting)
            # sort by parent directory name length+lex to favor numeric versions
            candidates.sort(key=lambda p: (len(str(p.parent.parent.name)), str(p.parent.parent.name)))
            return str(candidates[-1])

    # 4) Not found
    hint = ""
    if family == "postgres":
        hint = (
            "Install PostgreSQL client tools or set PG_BIN to the bin directory, e.g.:\n"
            '  $env:PG_BIN = "C:\\\\Program Files\\\\PostgreSQL\\\\16\\\\bin"\n'
            "Make sure pg_dump and psql exist there."
        )
    elif family == "mongo":
        hint = (
            "Install MongoDB Database Tools or set MONGO_BIN to the tools bin directory, e.g.:\n"
            '  $env:MONGO_BIN = "C:\\\\Program Files\\\\MongoDB\\\\Tools\\\\100\\\\bin"\n'
            "Make sure mongodump/mongorestore exist there."
        )
    raise FileNotFoundError(f"Executable '{exe_name}' not found. {hint}")

async def _run_subprocess(args: List[str], cwd: Optional[Path] = None, input_bytes: Optional[bytes] = None) -> subprocess.CompletedProcess:
    def _run():
        return subprocess.run(
            args,
            cwd=str(cwd) if cwd else None,
            input=input_bytes,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    proc = await asyncio.to_thread(_run)
    if proc.returncode != 0:
        raise RuntimeError(
            f"Command failed ({' '.join(args)}):\n"
            f"STDERR:\n{proc.stderr.decode(errors='ignore')}\n"
            f"STDOUT:\n{proc.stdout.decode(errors='ignore')}"
        )
    return proc

def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

async def backup_postgres(out_dir: Path) -> Dict[str, Any]:
    pg_dump = _resolve_exe("pg_dump", "PG_BIN", "postgres")
    url = _get_pg_url()
    sql_path = out_dir / "postgres.sql"
    sql_gz_path = out_dir / "postgres.sql.gz"

    # Dump to plain SQL, then gzip
    args = [pg_dump, f"--dbname={url}"]
    proc = await _run_subprocess(args)
    sql_path.write_bytes(proc.stdout)

    with sql_path.open("rb") as fin, gzip.open(sql_gz_path, "wb") as fout:
        shutil.copyfileobj(fin, fout)
    sql_path.unlink(missing_ok=True)

    return {
        "component": "postgres",
        "file": str(sql_gz_path),
        "size": sql_gz_path.stat().st_size,
        "sha256": _sha256(sql_gz_path),
    }

async def restore_postgres(from_sql_gz: Path, drop_schema: bool = True) -> Dict[str, Any]:
    psql = _resolve_exe("psql", "PG_BIN", "postgres")
    url = _get_pg_url()

    if drop_schema:
        for cmd in [
            psql, f"--dbname={url}", "-v", "ON_ERROR_STOP=1", "-c", "DROP SCHEMA IF EXISTS public CASCADE;"
        ], [
            psql, f"--dbname={url}", "-v", "ON_ERROR_STOP=1", "-c", "CREATE SCHEMA public;"
        ]:
            await _run_subprocess(cmd)

    with tempfile.TemporaryDirectory() as td:
        sql_path = Path(td) / "restore.sql"
        with gzip.open(from_sql_gz, "rb") as fin, sql_path.open("wb") as fout:
            shutil.copyfileobj(fin, fout)

        args = [psql, f"--dbname={url}", "-v", "ON_ERROR_STOP=1", "-f", str(sql_path)]
        await _run_subprocess(args)

    return {"component": "postgres", "restored_from": str(from_sql_gz)}

async def backup_mongo(out_dir: Path) -> Dict[str, Any]:
    mongodump = _resolve_exe("mongodump", "MONGO_BIN", "mongo")
    uri, dbname = _get_mongo_uri_and_db()
    archive_path = out_dir / "mongo.archive.gz"

    args = [mongodump, f"--uri={uri}", f"--db={dbname}", f"--archive={archive_path}", "--gzip"]
    await _run_subprocess(args)

    return {
        "component": "mongo",
        "file": str(archive_path),
        "size": archive_path.stat().st_size,
        "sha256": _sha256(archive_path),
        "db": dbname,
    }

async def restore_mongo(from_archive: Path, drop_first: bool = True) -> Dict[str, Any]:
    mongorestore = _resolve_exe("mongorestore", "MONGO_BIN", "mongo")
    uri, _dbname = _get_mongo_uri_and_db()
    args = [mongorestore, f"--uri={uri}", f"--archive={from_archive}", "--gzip"]
    if drop_first:
        args.append("--drop")
    await _run_subprocess(args)
    return {"component": "mongo", "restored_from": str(from_archive)}

async def create_backup(
    include_postgres: bool = True,
    include_mongo: bool = True,
    label: Optional[str] = None,
) -> Dict[str, Any]:
    BACKUPS_ROOT.mkdir(parents=True, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    folder_name = f"{ts}{('-' + label) if label else ''}"
    out_dir = BACKUPS_ROOT / folder_name
    out_dir.mkdir(parents=True, exist_ok=False)

    manifest: Dict[str, Any] = {
        "created_at": ts,
        "label": label,
        "artifacts": [],
        "version": 1,
        "platform": platform.platform(),
        "python": sys.version,
    }

    try:
        if include_postgres:
            pg_meta = await backup_postgres(out_dir)
            manifest["artifacts"].append(pg_meta)

        if include_mongo:
            mongo_meta = await backup_mongo(out_dir)
            manifest["artifacts"].append(mongo_meta)

        (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
        return {"backup_path": str(out_dir), **manifest}
    except Exception:
        shutil.rmtree(out_dir, ignore_errors=True)
        raise

async def restore_backup(
    backup_path: str,
    only_postgres: bool = False,
    only_mongo: bool = False,
    drop_pg_schema: bool = True,
    drop_mongo: bool = True,
) -> Dict[str, Any]:
    in_dir = Path(backup_path)
    if not in_dir.exists() or not in_dir.is_dir():
        raise FileNotFoundError(f"Backup folder not found: {backup_path}")

    manifest_path = in_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}

    results: List[Dict[str, Any]] = []

    if not only_mongo:
        pg_sql_gz = in_dir / "postgres.sql.gz"
        if pg_sql_gz.exists():
            res = await restore_postgres(pg_sql_gz, drop_schema=drop_pg_schema)
            results.append(res)

    if not only_postgres:
        mongo_archive = in_dir / "mongo.archive.gz"
        if mongo_archive.exists():
            res = await restore_mongo(mongo_archive, drop_first=drop_mongo)
            results.append(res)

    return {
        "restored_from": backup_path,
        "results": results,
        "manifest": manifest,
    }
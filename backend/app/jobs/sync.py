"""
Week 2: Filesystem sync job.

Scans allowed paths, detects changes, updates FileMetadata table.
"""

import hashlib
import os
from datetime import datetime
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from app.mcp.servers import FileSystemMCPServer
from app.db.models import FileMetadata, SyncRun


def compute_file_hash(filepath: str, block_size: int = 65536) -> str:
    """
    Compute SHA256 hash of file for change detection.
    
    Only used for files < 10MB to avoid blocking.
    """
    hasher = hashlib.sha256()
    try:
        with open(filepath, "rb") as f:
            while chunk := f.read(block_size):
                hasher.update(chunk)
        return hasher.hexdigest()
    except Exception:
        return ""


def scan_filesystem(
    db: Session,
    mcp_server: FileSystemMCPServer,
    allowed_paths: List[str],
) -> Dict[str, int]:
    """
    Scan filesystem and update FileMetadata table.
    
    Returns stats: {new, changed, deleted, unchanged}
    """
    stats = {
        "files_new": 0,
        "files_changed": 0,
        "files_deleted": 0,
        "files_unchanged": 0,
        "files_scanned": 0,
    }
    
    # Track paths we see now
    current_paths = set()
    
    for root_path in allowed_paths:
        # Scan the root itself (includes files in the root path) and recurse.
        stats = scan_directory_recursive(
            db=db,
            mcp_server=mcp_server,
            dir_path=root_path,
            stats=stats,
            current_paths=current_paths,
        )
    
    # Detect deleted files
    deleted_files = (
        db.query(FileMetadata)
        .filter(~FileMetadata.path.in_(current_paths))
        .all()
    )
    
    for file in deleted_files:
        file.needs_sync = True
        stats["files_deleted"] += 1
    
    db.commit()
    return stats


def scan_directory_recursive(
    db: Session,
    mcp_server: FileSystemMCPServer,
    dir_path: str,
    stats: Dict[str, int],
    current_paths: set,
) -> Dict[str, int]:
    """Recursively scan directory."""
    
    # List this directory
    result = mcp_server.list_files(dir_path)
    if result.get("error"):
        return stats
    
    # Track files
    for file_info in result.get("files", []):
        filepath = file_info["path"]
        current_paths.add(filepath)
        stats["files_scanned"] += 1
        
        # Get existing record
        existing = (
            db.query(FileMetadata)
            .filter(FileMetadata.path == filepath)
            .first()
        )
        
        needs_sync = False
        record = existing
        
        # New file
        if not existing:
            record = FileMetadata(
                path=filepath,
                size=file_info["size"],
                modified=datetime.fromisoformat(file_info["modified"]),
            )
            db.add(record)
            stats["files_new"] += 1
            needs_sync = True
        else:
            # Changed? (size or modified timestamp)
            if (
                existing.size != file_info["size"]
                or existing.modified != datetime.fromisoformat(file_info["modified"])
            ):
                existing.size = file_info["size"]
                existing.modified = datetime.fromisoformat(file_info["modified"])
                stats["files_changed"] += 1
                needs_sync = True
            else:
                stats["files_unchanged"] += 1
        
        # Update sync state
        if needs_sync:
            record.needs_sync = True
    
    # Recurse into subdirectories
    for dir_info in result.get("directories", []):
        stats = scan_directory_recursive(
            db, mcp_server, dir_info["path"], stats, current_paths
        )
    
    return stats


def run_sync(db: Session, allowed_paths: List[str]) -> Dict[str, Any]:
    """
    Full sync operation.
    
    1. Create SyncRun record
    2. Scan filesystem
    3. Update stats
    4. Commit
    """
    if not allowed_paths:
        raise ValueError("allowed_paths must be a non-empty list of paths")
    
    # Create sync run
    sync_run = SyncRun(started_at=datetime.now())
    db.add(sync_run)
    db.flush()  # Get ID
    
    mcp_server = FileSystemMCPServer(allowed_paths=allowed_paths)
    
    try:
        start_time = sync_run.started_at
        
        # Scan
        stats = scan_filesystem(db, mcp_server, allowed_paths)
        
        # Update sync run
        sync_run.completed_at = datetime.now()
        sync_run.duration_ms = int(
            (sync_run.completed_at - start_time).total_seconds() * 1000
        )
        sync_run.files_scanned = stats["files_scanned"]
        sync_run.files_new = stats["files_new"]
        sync_run.files_changed = stats["files_changed"]
        sync_run.files_deleted = stats["files_deleted"]
        sync_run.files_unchanged = stats["files_unchanged"]
        sync_run.status = "completed"
        
        db.commit()
        
        print(
            f"Sync completed: {sync_run.files_scanned} scanned, "
            f"{sync_run.files_changed} changed"
        )
        
        return {
            "sync_run_id": sync_run.id,
            "status": "completed",
            "duration_ms": sync_run.duration_ms,
            "stats": stats,
        }
        
    except Exception as e:
        sync_run.status = "failed"
        sync_run.error_message = str(e)
        db.commit()
        raise


def get_sync_stats(db: Session) -> Dict[str, Any]:
    """Get latest sync status + summary stats."""
    
    latest_run = (
        db.query(SyncRun)
        .order_by(SyncRun.started_at.desc())
        .first()
    )
    
    total_files = db.query(FileMetadata).count()
    needs_sync = (
        db.query(FileMetadata)
        .filter(FileMetadata.needs_sync.is_(True))
        .count()
    )
    
    return {
        "latest_sync": {
            "id": latest_run.id if latest_run else None,
            "started_at": latest_run.started_at.isoformat() if latest_run else None,
            "status": latest_run.status if latest_run else None,
            "files_scanned": latest_run.files_scanned if latest_run else 0,
        } if latest_run
        else {"status": "never_run"},
        "total_files": total_files,
        "files_needing_sync": needs_sync,
    }

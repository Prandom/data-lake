"""
Week 2: SQLAlchemy models for file metadata and sync state.

Tables:
- FileMetadata: tracks individual files (path, size, modified, last_synced)
- SyncRun: tracks sync operations (when, how many files changed)
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, func
from sqlalchemy.orm import declarative_base


Base = declarative_base()


class FileMetadata(Base):
    """
    Tracks individual files that have been discovered.
    
    Key fields for change detection:
    - size + modified → detect changes
    - hash → detect content changes (optional)
    """
    
    __tablename__ = "file_metadata"
    
    id = Column(Integer, primary_key=True, index=True)
    path = Column(String(1000), unique=True, index=True, nullable=False)
    
    # File attributes for change detection
    size = Column(Integer, nullable=False)
    modified = Column(DateTime(timezone=True), nullable=False)
    hash_value = Column(String(64), nullable=True)  # SHA256 later
    
    # Sync state
    last_synced = Column(DateTime(timezone=True), nullable=True)
    needs_sync = Column(Boolean, default=True)
    
    # Audit
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
    
    def __repr__(self):
        return f"<FileMetadata(path='{self.path}', size={self.size}, needs_sync={self.needs_sync})>"


class SyncRun(Base):
    """
    Tracks each sync operation.
    
    Used for observability and scheduling decisions.
    """
    
    __tablename__ = "sync_runs"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Timing
    started_at = Column(DateTime(timezone=True), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    duration_ms = Column(Integer, nullable=True)
    
    # Stats
    files_scanned = Column(Integer, default=0)
    files_new = Column(Integer, default=0)
    files_changed = Column(Integer, default=0)
    files_deleted = Column(Integer, default=0)
    files_unchanged = Column(Integer, default=0)
    
    # Status
    status = Column(
        String(20),
        default="running",
        comment="running|completed|failed",
    )
    error_message = Column(String(1000))
    
    # Audit
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<SyncRun(id={self.id}, started={self.started_at}, status={self.status})>"

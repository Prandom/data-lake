"""
SQLAlchemy models for file metadata, sync state, and vector search.

Tables:
- FileMetadata: tracks individual files (path, size, modified, last_synced)
- SyncRun: tracks sync operations (when, how many files changed)
- ChunkMetadata: stores text chunks alongside FAISS vector IDs (Week 3)
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, func
from sqlalchemy.orm import declarative_base


Base = declarative_base()


class User(Base):
    """
    User account — keyed by Firebase UID.

    The Firebase UID is used directly as the primary key (no auto-increment).
    This simplifies the mapping between Firebase Auth and our database.

    Fields:
    - id: Firebase UID (string, primary key)
    - email: user's email from Firebase
    - display_name: user's display name
    - created_at: when the record was first created
    - updated_at: last time the record was updated
    """

    __tablename__ = "users"

    id = Column(String(128), primary_key=True)  # Firebase UID
    email = Column(String(255), nullable=False, index=True)
    display_name = Column(String(255), nullable=True)

    # Audit
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    def __repr__(self):
        return f"<User(id='{self.id}', email='{self.email}')>"


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


class ChunkMetadata(Base):
    """
    Stores chunk text + metadata alongside FAISS vector IDs.

    FAISS only stores vectors and returns integer IDs.
    This table maps those IDs back to actual content.

    The `faiss_id` column corresponds to the row position in the FAISS index.
    """

    __tablename__ = "chunk_metadata"

    id = Column(Integer, primary_key=True, index=True)
    faiss_id = Column(Integer, unique=True, index=True, nullable=False)
    path = Column(String(1000), index=True, nullable=False)
    chunk_id = Column(Integer, nullable=False)  # chunk index within the file
    content = Column(Text, nullable=False)
    tokens = Column(Integer, nullable=True)

    # Audit
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<ChunkMetadata(faiss_id={self.faiss_id}, path='{self.path}', chunk={self.chunk_id})>"

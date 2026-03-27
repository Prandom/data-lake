"""
Test database models (Week 2).

Tests:
- FileMetadata model creation and queries
- SyncRun model tracking
- Relationships and constraints
"""

import pytest
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.db.models import FileMetadata, SyncRun


class TestFileMetadata:
    """Tests for FileMetadata model."""
    
    def test_create_file_metadata(self, test_db: Session):
        """Test creating a FileMetadata record."""
        file = FileMetadata(
            path="/home/user/file.txt",
            size=1024,
            modified=datetime.now(),
        )
        test_db.add(file)
        test_db.commit()
        
        # Verify it was saved
        retrieved = test_db.query(FileMetadata).filter_by(path="/home/user/file.txt").first()
        assert retrieved is not None
        assert retrieved.size == 1024
        assert retrieved.needs_sync is True  # Default
    
    def test_file_metadata_unique_path(self, test_db: Session):
        """Test that file paths must be unique."""
        file1 = FileMetadata(
            path="/home/user/file.txt",
            size=100,
            modified=datetime.now(),
        )
        file2 = FileMetadata(
            path="/home/user/file.txt",  # Same path
            size=200,
            modified=datetime.now(),
        )
        test_db.add(file1)
        test_db.commit()
        
        test_db.add(file2)
        with pytest.raises(IntegrityError):
            test_db.commit()
    
    def test_file_metadata_timestamps(self, test_db: Session):
        """Test that created_at and updated_at are set."""
        file = FileMetadata(
            path="/home/user/file.txt",
            size=1024,
            modified=datetime.now(),
        )
        test_db.add(file)
        test_db.commit()
        
        assert file.created_at is not None
        assert file.updated_at is not None
    
    def test_mark_needs_sync(self, test_db: Session):
        """Test marking file for sync."""
        file = FileMetadata(
            path="/home/user/file.txt",
            size=1024,
            modified=datetime.now(),
            needs_sync=False,
        )
        test_db.add(file)
        test_db.commit()
        
        # Update
        file.needs_sync = True
        test_db.commit()
        
        retrieved = test_db.query(FileMetadata).filter_by(path="/home/user/file.txt").first()
        assert retrieved.needs_sync is True


class TestSyncRun:
    """Tests for SyncRun model."""
    
    def test_create_sync_run(self, test_db: Session):
        """Test creating a SyncRun record."""
        sync = SyncRun(
            started_at=datetime.now(),
            files_scanned=100,
            files_new=10,
            files_changed=5,
        )
        test_db.add(sync)
        test_db.commit()
        
        assert sync.id is not None
        assert sync.status == "running"  # Default
    
    def test_sync_run_completion(self, test_db: Session):
        """Test marking sync as complete."""
        sync = SyncRun(started_at=datetime.now())
        test_db.add(sync)
        test_db.commit()
        
        # Update to completed
        sync.completed_at = datetime.now()
        sync.duration_ms = 500
        sync.status = "completed"
        test_db.commit()
        
        retrieved = test_db.query(SyncRun).filter_by(id=sync.id).first()
        assert retrieved.status == "completed"
        assert retrieved.duration_ms == 500
    
    def test_sync_run_failure(self, test_db: Session):
        """Test marking sync as failed."""
        sync = SyncRun(started_at=datetime.now())
        test_db.add(sync)
        test_db.commit()
        
        # Mark as failed
        sync.status = "failed"
        sync.error_message = "Permission denied"
        test_db.commit()
        
        retrieved = test_db.query(SyncRun).filter_by(id=sync.id).first()
        assert retrieved.status == "failed"
        assert "Permission denied" in retrieved.error_message


class TestQueries:
    """Test common database queries."""
    
    def test_find_files_needing_sync(self, test_db: Session):
        """Test query for files that need syncing."""
        # Create files
        file1 = FileMetadata(path="/a.txt", size=100, modified=datetime.now(), needs_sync=True)
        file2 = FileMetadata(path="/b.txt", size=200, modified=datetime.now(), needs_sync=False)
        file3 = FileMetadata(path="/c.txt", size=300, modified=datetime.now(), needs_sync=True)
        
        test_db.add_all([file1, file2, file3])
        test_db.commit()
        
        # Query for files needing sync
        need_sync = (
            test_db.query(FileMetadata)
            .filter(FileMetadata.needs_sync.is_(True))
            .all()
        )
        
        assert len(need_sync) == 2
        assert file1 in need_sync
        assert file3 in need_sync
    
    def test_get_latest_sync_run(self, test_db: Session):
        """Test getting the most recent sync run."""
        sync1 = SyncRun(started_at=datetime(2026, 1, 1))
        sync2 = SyncRun(started_at=datetime(2026, 1, 2))
        sync3 = SyncRun(started_at=datetime(2026, 1, 3))
        
        test_db.add_all([sync1, sync2, sync3])
        test_db.commit()
        
        latest = test_db.query(SyncRun).order_by(SyncRun.started_at.desc()).first()
        
        assert latest.id == sync3.id

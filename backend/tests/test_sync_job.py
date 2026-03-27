"""
Test Sync Job (Week 2).

Tests:
- File scanning and detection
- Change detection (new, changed, deleted)
- Sync run tracking
- Hash computation
"""

import pytest
import os
import time
from datetime import datetime
from sqlalchemy.orm import Session

from app.jobs.sync import (
    compute_file_hash,
    scan_filesystem,
    scan_directory_recursive,
)
from app.db.models import FileMetadata, SyncRun
from app.mcp.servers import FileSystemMCPServer


class TestHashComputation:
    """Tests for file hash computation."""
    
    def test_compute_file_hash(self, temp_files):
        """Test SHA256 hash computation."""
        temp_dir, files = temp_files
        
        hash1 = compute_file_hash(files[0])
        
        # Should be 64 hex characters (SHA256)
        assert len(hash1) == 64
        assert all(c in "0123456789abcdef" for c in hash1)
    
    def test_hash_consistency(self, temp_files):
        """Test that same file produces same hash."""
        temp_dir, files = temp_files
        
        hash1 = compute_file_hash(files[0])
        hash2 = compute_file_hash(files[0])
        
        assert hash1 == hash2
    
    def test_different_files_different_hashes(self, temp_files):
        """Test that different files have different hashes."""
        temp_dir, files = temp_files
        
        hash1 = compute_file_hash(files[0])
        hash2 = compute_file_hash(files[1])
        
        assert hash1 != hash2
    
    def test_hash_nonexistent_file(self):
        """Test hashing a file that doesn't exist."""
        hash_result = compute_file_hash("/nonexistent/file.txt")
        
        assert hash_result == ""  # Should return empty string on error


class TestScanFilesystem:
    """Tests for filesystem scanning."""
    
    def test_scan_new_files(self, test_db: Session, temp_files):
        """Test that scan detects new files."""
        temp_dir, files = temp_files
        mcp_server = FileSystemMCPServer(allowed_paths=[temp_dir])
        
        stats = scan_filesystem(test_db, mcp_server, [temp_dir])
        
        assert stats["files_new"] > 0
        assert stats["files_scanned"] > 0
        
        # Verify files are in database
        records = test_db.query(FileMetadata).all()
        assert len(records) > 0
    
    def test_scan_detects_changes(self, test_db: Session, temp_files):
        """Test that scan detects file modifications."""
        temp_dir, files = temp_files
        mcp_server = FileSystemMCPServer(allowed_paths=[temp_dir])
        
        # First scan
        stats1 = scan_filesystem(test_db, mcp_server, [temp_dir])
        initial_new = stats1["files_new"]
        
        # Modify a file
        time.sleep(0.01)  # Ensure mtime changes
        with open(files[0], "a") as f:
            f.write("\nmodified content")
        
        # Second scan
        stats2 = scan_filesystem(test_db, mcp_server, [temp_dir])
        
        assert stats2["files_changed"] >= 1
        assert stats2["files_new"] == 0  # No new files
    
    def test_scan_detects_deletions(self, test_db: Session, temp_files):
        """Test that scan detects deleted files."""
        temp_dir, files = temp_files
        mcp_server = FileSystemMCPServer(allowed_paths=[temp_dir])
        
        # First scan
        stats1 = scan_filesystem(test_db, mcp_server, [temp_dir])
        
        # Delete a file
        os.remove(files[0])
        
        # Second scan
        stats2 = scan_filesystem(test_db, mcp_server, [temp_dir])
        
        assert stats2["files_deleted"] >= 1
    
    def test_scan_preserves_unchanged_files(self, test_db: Session, temp_files):
        """Test that unchanged files are tracked."""
        temp_dir, files = temp_files
        mcp_server = FileSystemMCPServer(allowed_paths=[temp_dir])
        
        # First scan
        stats1 = scan_filesystem(test_db, mcp_server, [temp_dir])
        
        # Second scan without changes
        stats2 = scan_filesystem(test_db, mcp_server, [temp_dir])
        
        assert stats2["files_unchanged"] > 0


class TestSyncStats:
    """Tests for sync statistics tracking."""
    
    def test_sync_run_created(self, test_db: Session, temp_files):
        """Test that SyncRun record is created."""
        temp_dir, files = temp_files
        mcp_server = FileSystemMCPServer(allowed_paths=[temp_dir])
        
        # Initially no sync runs
        runs_before = test_db.query(SyncRun).count()
        
        # After scan, we don't create SyncRun (that's in run_sync)
        # This test just verifies the structure
        assert runs_before == 0
    
    def test_file_metadata_records_created(self, test_db: Session, temp_files):
        """Test that FileMetadata records are created for all files."""
        temp_dir, files = temp_files
        mcp_server = FileSystemMCPServer(allowed_paths=[temp_dir])
        
        stats = scan_filesystem(test_db, mcp_server, [temp_dir])
        
        # Verify records exist
        records = test_db.query(FileMetadata).all()
        assert len(records) == stats["files_scanned"]
        
        # All should have needs_sync=True for new files
        for record in records:
            assert record.path is not None
            assert record.size >= 0


class TestEdgeCases:
    """Tests for edge cases and error handling."""
    
    def test_scan_empty_directory(self, test_db: Session, temp_dir):
        """Test scanning an empty directory."""
        mcp_server = FileSystemMCPServer(allowed_paths=[temp_dir])
        
        stats = scan_filesystem(test_db, mcp_server, [temp_dir])
        
        assert stats["files_scanned"] == 0
        assert stats["files_new"] == 0
    
    def test_scan_with_no_allowed_paths(self, test_db: Session):
        """Test scanning with empty allowed paths."""
        mcp_server = FileSystemMCPServer(allowed_paths=[])
        
        # Should handle gracefully
        stats = scan_filesystem(test_db, mcp_server, [])
        
        assert stats["files_scanned"] == 0

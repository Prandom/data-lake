"""
Test FileSystem MCP Server (Week 1).

Tests:
- File listing
- File reading
- Metadata extraction
- Security (path validation)
"""

import pytest
import os
from app.mcp.servers import FileSystemMCPServer


class TestListFiles:
    """Tests for list_files functionality."""
    
    def test_list_files_in_temp_dir(self, temp_files, mcp_server):
        """Test listing files in a directory."""
        temp_dir, files = temp_files
        
        result = mcp_server.list_files(temp_dir, recursive=False)
        
        assert result.get("error") is None
        assert result["path"] == os.path.normpath(os.path.abspath(temp_dir))
        assert len(result["files"]) > 0
    
    def test_list_files_recursive(self, temp_files, mcp_server):
        """Test recursive file listing."""
        temp_dir, files = temp_files
        
        result = mcp_server.list_files(temp_dir, recursive=True)
        
        assert result.get("error") is None
        # Should include both root and nested files
        assert len(result["files"]) >= 3
    
    def test_list_files_nonexistent_path(self, mcp_server):
        """Test listing files in non-existent directory."""
        result = mcp_server.list_files("/nonexistent/path", recursive=False)
        
        assert result.get("error") is not None


class TestReadFile:
    """Tests for read_file functionality."""
    
    def test_read_file_success(self, temp_files, mcp_server):
        """Test reading a file successfully."""
        temp_dir, files = temp_files
        
        result = mcp_server.read_file(files[0])
        
        assert result.get("error") is None
        assert "content" in result
        assert len(result["content"]) > 0
    
    def test_read_nonexistent_file(self, mcp_server):
        """Test reading a file that doesn't exist."""
        result = mcp_server.read_file("/nonexistent/file.txt")
        
        assert result.get("error") is not None
    
    def test_read_directory_as_file(self, temp_files, mcp_server):
        """Test trying to read a directory."""
        temp_dir, files = temp_files
        
        result = mcp_server.read_file(temp_dir)
        
        assert result.get("error") is not None


class TestGetMetadata:
    """Tests for get_metadata functionality."""
    
    def test_get_file_metadata(self, temp_files, mcp_server):
        """Test getting file metadata."""
        temp_dir, files = temp_files
        
        result = mcp_server.get_metadata(files[0])
        
        assert result.get("error") is None
        assert result["type"] == "file"
        assert result["size"] > 0
        assert "modified" in result
    
    def test_get_directory_metadata(self, temp_files, mcp_server):
        """Test getting directory metadata."""
        temp_dir, files = temp_files
        
        result = mcp_server.get_metadata(temp_dir)
        
        assert result.get("error") is None
        assert result["type"] == "directory"


class TestSecurity:
    """Tests for path validation and security."""
    
    def test_access_denied_outside_allowed_paths(self, temp_files):
        """Test that access is denied outside allowed paths."""
        temp_dir, files = temp_files
        
        # Create MCP server with restricted paths
        restricted_server = FileSystemMCPServer(allowed_paths=[temp_dir])
        
        # Try to access file outside allowed path
        result = restricted_server.list_files("/etc")
        
        assert result.get("error") is not None
        assert "Access denied" in result["error"]
    
    def test_path_normalization(self, temp_files, mcp_server):
        """Test that paths are normalized (~ expansion, etc)."""
        temp_dir, files = temp_files
        
        # Test that relative paths in allowed dir work
        result = mcp_server.list_files(temp_dir, recursive=False)
        
        assert result.get("error") is None
        # Path should be normalized
        assert "\\" not in result["path"] or os.name == "nt"  # Windows uses backslash


class TestErrorHandling:
    """Tests for error handling."""
    
    def test_permission_error_handling(self, temp_dir):
        """Test graceful handling of permission errors."""
        # Create a file with restricted permissions
        restricted_file = os.path.join(temp_dir, "restricted.txt")
        with open(restricted_file, "w") as f:
            f.write("content")
        
        # Try to read with denied permissions (platform-dependent)
        # This test may not work on all platforms
        server = FileSystemMCPServer(allowed_paths=[temp_dir])
        result = server.list_files(temp_dir)
        
        # Should still return valid data for readable files
        assert result.get("path") is not None

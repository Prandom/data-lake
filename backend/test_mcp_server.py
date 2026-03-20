"""
Week 1: Test FileSystemMCPServer directly.

Run with: python backend/test_mcp_server.py
"""

import os
import json
from pathlib import Path

from app.mcp.servers import FileSystemMCPServer


def test_mcp_server():
    """Test the FileSystemMCPServer class directly."""
    
    # Initialize with your home directory as allowed
    allowed = [os.path.expanduser("~")]
    srv = FileSystemMCPServer(allowed_paths=allowed)
    
    print("✅ FileSystemMCPServer initialized")
    print(f"   Allowed paths: {allowed}\n")
    
    # Test 1: List home directory
    print("=== 1) list_files('~') ===")
    result = srv.list_files("~")
    print(f"Files found: {result.get('total', 0)}")
    print(json.dumps(result, indent=2)[:1000] + "..." if len(json.dumps(result)) > 1000 else json.dumps(result, indent=2))
    print()
    
    # Test 2: Get metadata of home directory
    print("=== 2) get_metadata('~') ===")
    result = srv.get_metadata("~")
    print(json.dumps(result, indent=2))
    print()
    
    # Test 3: List current directory
    print("=== 3) list_files('.') ===")
    result = srv.list_files(".")
    print(f"Files in current dir: {result.get('total', 0)}")
    print(json.dumps(result, indent=2))
    print()
    
    # Test 4: Try to read requirements.txt
    req_path = "requirements.txt"
    print(f"=== 4) read_file('{req_path}') ===")
    result = srv.read_file(req_path)
    if result.get("error"):
        print(f"❌ Error: {result['error']}")
    else:
        print(f"✅ Read {len(result['content'])} chars")
        print("First 200 chars:", repr(result['content'][:200]))
    print()
    
    # Test 5: Invalid path (security)
    print("=== 5) Invalid path test (should fail) ===")
    result = srv.read_file("/etc/passwd")  # Should be blocked
    print("Expected error:", "PermissionError" in result.get("error", ""))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    test_mcp_server()

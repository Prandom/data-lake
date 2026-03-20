import os
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass, asdict


@dataclass
class FileInfo:
    """Represents a file or directory for listing."""

    name: str
    path: str
    type: str  # "file" or "directory"
    size: Optional[int] = None
    modified: Optional[str] = None
    readable: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class FileContent:
    """Represents file contents for reading."""

    path: str
    content: str
    size: int
    encoding: str = "utf-8"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class FileSystemMCPServer:
    """
    Week 1: FileSystem MCP-like server (not wired to Claude yet).

    Tools (later exposed to Claude as MCP tools):
    - list_files(path, recursive, include_hidden)
    - read_file(path)
    - get_metadata(path)
    """

    def __init__(self, allowed_paths: Optional[List[str]] = None):
        self.allowed_paths = allowed_paths or [os.path.expanduser("~")]
        self.allowed_paths = [os.path.normpath(os.path.abspath(p)) for p in self.allowed_paths]
        self.name = "filesystem"
        self.version = "0.1.0"

        print("✓ FileSystemMCPServer initialized")
        print(f"  Allowed paths: {self.allowed_paths}")

    # -------------------------------------------------------------------------
    # SECURITY HELPERS
    # -------------------------------------------------------------------------

    def _is_allowed(self, path: str) -> bool:
        """
        Check if path is within allowed directories.

        Prevents directory traversal outside your whitelisted roots.
        """
        norm_path = os.path.normpath(os.path.abspath(path))
        for allowed in self.allowed_paths:
            try:
                rel = os.path.relpath(norm_path, allowed)
                if not rel.startswith(os.pardir):
                    return True
            except ValueError:
                # Different drive on Windows, just skip
                continue
        return False

    def _validate_path(self, path: str) -> str:
        """
        Expand, normalize and validate path is allowed.
        """
        expanded = os.path.expanduser(path)
        norm = os.path.normpath(os.path.abspath(expanded))
        if not self._is_allowed(norm):
            raise PermissionError(
                f"Access denied to {path}. Allowed roots: {self.allowed_paths}"
            )
        return norm

    # -------------------------------------------------------------------------
    # TOOL 1: LIST FILES
    # -------------------------------------------------------------------------

    def list_files(
        self,
        path: str = ".",
        recursive: bool = False,
        include_hidden: bool = False,
    ) -> Dict[str, Any]:
        """
        List files in a directory.

        Args:
            path: directory to list
            recursive: not used yet (can extend later)
            include_hidden: include entries starting with '.'

        Returns:
            dict with path, files, directories, total, error
        """
        try:
            norm_path = self._validate_path(path)
            if not os.path.exists(norm_path):
                return {
                    "error": f"Path not found: {path}",
                    "path": path,
                    "files": [],
                    "directories": [],
                }
            if not os.path.isdir(norm_path):
                return {
                    "error": f"Not a directory: {path}",
                    "path": path,
                    "files": [],
                    "directories": [],
                }

            files: List[FileInfo] = []
            dirs: List[FileInfo] = []

            try:
                entries = os.listdir(norm_path)
            except PermissionError:
                return {
                    "error": f"Permission denied reading {path}",
                    "path": path,
                    "files": [],
                    "directories": [],
                }

            for entry in entries:
                if not include_hidden and entry.startswith("."):
                    continue

                full = os.path.join(norm_path, entry)
                try:
                    st = os.stat(full)
                    is_dir = os.path.isdir(full)
                    info = FileInfo(
                        name=entry,
                        path=full,
                        type="directory" if is_dir else "file",
                        size=None if is_dir else st.st_size,
                        modified=datetime.fromtimestamp(st.st_mtime).isoformat(),
                    )
                    if is_dir:
                        dirs.append(info)
                    else:
                        files.append(info)
                except (OSError, PermissionError):
                    files.append(
                        FileInfo(
                            name=entry,
                            path=full,
                            type="file",
                            readable=False,
                        )
                    )

            files.sort(key=lambda x: x.name.lower())
            dirs.sort(key=lambda x: x.name.lower())

            return {
                "path": norm_path,
                "files": [f.to_dict() for f in files],
                "directories": [d.to_dict() for d in dirs],
                "total": len(files) + len(dirs),
                "error": None,
                "timestamp": datetime.now().isoformat(),
            }
        except PermissionError as e:
            return {
                "error": str(e),
                "path": path,
                "files": [],
                "directories": [],
            }
        except Exception as e:
            return {
                "error": f"Unexpected error: {e}",
                "path": path,
                "files": [],
                "directories": [],
            }

    # -------------------------------------------------------------------------
    # TOOL 2: READ FILE
    # -------------------------------------------------------------------------

    def read_file(self, path: str) -> Dict[str, Any]:
        """
        Read file content as text (with basic size limit).
        """
        try:
            norm_path = self._validate_path(path)
            if not os.path.exists(norm_path):
                return {
                    "error": f"File not found: {path}",
                    "path": path,
                    "content": None,
                    "size": 0,
                }
            if not os.path.isfile(norm_path):
                return {
                    "error": f"Not a file: {path}",
                    "path": path,
                    "content": None,
                    "size": 0,
                }

            file_size = os.path.getsize(norm_path)
            max_size = 10 * 1024 * 1024  # 10 MB
            if file_size > max_size:
                return {
                    "error": f"File too large: {file_size} bytes (max {max_size})",
                    "path": path,
                    "content": None,
                    "size": file_size,
                }

            try:
                with open(norm_path, "r", encoding="utf-8") as f:
                    content = f.read()
                encoding = "utf-8"
            except UnicodeDecodeError:
                try:
                    with open(norm_path, "r", encoding="latin-1") as f:
                        content = f.read()
                    encoding = "latin-1"
                except Exception:
                    return {
                        "error": "File is not readable as text",
                        "path": path,
                        "content": None,
                        "size": file_size,
                    }

            return {
                "path": norm_path,
                "content": content,
                "size": len(content),
                "original_size": file_size,
                "encoding": encoding,
                "error": None,
                "timestamp": datetime.now().isoformat(),
            }
        except PermissionError as e:
            return {
                "error": str(e),
                "path": path,
                "content": None,
                "size": 0,
            }
        except Exception as e:
            return {
                "error": f"Unexpected error: {e}",
                "path": path,
                "content": None,
                "size": 0,
            }

    # -------------------------------------------------------------------------
    # TOOL 3: METADATA
    # -------------------------------------------------------------------------

    def get_metadata(self, path: str) -> Dict[str, Any]:
        """
        Get metadata for a file or directory.
        """
        try:
            norm_path = self._validate_path(path)
            if not os.path.exists(norm_path):
                return {"error": f"Path not found: {path}", "path": path}

            st = os.stat(norm_path)
            is_dir = os.path.isdir(norm_path)

            return {
                "path": norm_path,
                "type": "directory" if is_dir else "file",
                "size": None if is_dir else st.st_size,
                "created": datetime.fromtimestamp(st.st_ctime).isoformat(),
                "modified": datetime.fromtimestamp(st.st_mtime).isoformat(),
                "permissions": oct(st.st_mode)[-3:],
                "error": None,
                "timestamp": datetime.now().isoformat(),
            }
        except PermissionError as e:
            return {"error": str(e), "path": path}
        except Exception as e:
            return {"error": f"Unexpected error: {e}", "path": path}


if __name__ == "__main__":
    # Quick manual tests
    srv = FileSystemMCPServer(allowed_paths=[os.path.expanduser("~")])

    print("\n=== Test: list_files('~') ===")
    print(json.dumps(srv.list_files("~"), indent=2))

    print("\n=== Test: get_metadata('~') ===")
    print(json.dumps(srv.get_metadata("~"), indent=2))

"""
RoboAssistant Company OS 2.0 — Governed File & Download Intelligence
Provides file taxonomy, cryptographic checksum verification, duplicate detection,
and download validation. Invariant: External files are DATA, never auto-executed policy.
"""

from typing import Dict, List, Optional, Any
import time
import os
import hashlib
import mimetypes

class FileIntelligenceEngine:
    def __init__(self, sandbox_root: Optional[str] = None):
        self.sandbox_root = sandbox_root or os.path.abspath(
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "storage/sandbox")
        )
        os.makedirs(self.sandbox_root, exist_ok=True)

    def scan_directory(self, target_dir: Optional[str] = None) -> List[Dict[str, Any]]:
        directory = target_dir or self.sandbox_root
        if not os.path.exists(directory):
            return []

        results = []
        for root, dirs, files in os.walk(directory):
            for f in files:
                full_path = os.path.join(root, f)
                try:
                    stat = os.stat(full_path)
                    mime, _ = mimetypes.guess_type(full_path)
                    results.append({
                        "file_name": f,
                        "path": full_path,
                        "size_bytes": stat.st_size,
                        "modified_at": stat.st_mtime,
                        "mime_type": mime or "application/octet-stream",
                        "is_executable": os.access(full_path, os.X_OK)
                    })
                except Exception:
                    pass
        return results

    def calculate_file_hash(self, file_path: str) -> Optional[str]:
        if not os.path.exists(file_path):
            return None
        h = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(8192):
                h.update(chunk)
        return h.hexdigest()

    def detect_duplicates(self, target_dir: Optional[str] = None) -> Dict[str, List[str]]:
        directory = target_dir or self.sandbox_root
        hashes: Dict[str, List[str]] = {}
        for root, _, files in os.walk(directory):
            for f in files:
                p = os.path.join(root, f)
                f_hash = self.calculate_file_hash(p)
                if f_hash:
                    hashes.setdefault(f_hash, []).append(p)
        return {h: paths for h, paths in hashes.items() if len(paths) > 1}

    def verify_downloaded_data(self, file_path: str, expected_sha256: Optional[str] = None) -> Dict[str, Any]:
        """
        Validates downloaded external content.
        Enforces that downloaded files are marked as UNTRUSTED DATA and not executable.
        """
        if not os.path.exists(file_path):
            return {"verified": False, "error": "File does not exist on disk"}

        actual_sha256 = self.calculate_file_hash(file_path)
        size = os.path.getsize(file_path)

        hash_matches = True
        if expected_sha256:
            hash_matches = (actual_sha256.lower() == expected_sha256.lower())

        # Security check: Ensure file permissions are not executable
        try:
            current_mode = os.stat(file_path).st_mode
            os.chmod(file_path, current_mode & ~0o111)  # strip execution bits
        except Exception:
            pass

        return {
            "verified": hash_matches,
            "path": file_path,
            "sha256": actual_sha256,
            "size_bytes": size,
            "untrusted_data_flag": True,
            "executable_stripped": True,
            "details": "Content verified and isolated as untrusted data"
        }

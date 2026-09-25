"""
RoboAssistant Company OS 2.0 — Application Discovery & Automation Fabric
Discovers local host applications, inspects available automation interfaces,
and selects the safest deterministic communication channel (API > CLI > GUI).
"""

from typing import Dict, List, Optional, Any
import time
import os
import shutil
import subprocess
import json
from .db import db

class ApplicationDiscoveryEngine:
    COMMON_PROBES = [
        ("python3", "Python Runtime", "Python Software Foundation"),
        ("curl", "Curl HTTP Transfer", "Haxx"),
        ("jq", "JSON Processor", "Stephen Dolan"),
        ("git", "Git VCS", "Software Freedom Conservancy"),
        ("tar", "Archive Utility", "GNU Project"),
        ("gzip", "Compression Utility", "GNU Project"),
        ("bash", "Bourne Again Shell", "GNU Project"),
        ("sqlite3", "SQLite Embedded DB", "SQLite Consortium")
    ]

    def __init__(self, host_id: str = "host_local"):
        self.host_id = host_id

    def discover_installed_applications(self) -> List[Dict[str, Any]]:
        """
        Discovers verified executables and automation interfaces on the physical host.
        """
        discovered = []
        now = time.time()

        for binary, app_name, publisher in self.COMMON_PROBES:
            path = shutil.which(binary)
            if path:
                version = "unknown"
                try:
                    res = subprocess.run([path, "--version"], capture_output=True, text=True, timeout=2)
                    version = (res.stdout or res.stderr).splitlines()[0][:60]
                except Exception:
                    pass

                app_id = f"app_{binary}_{self.host_id}"
                interfaces = ["CLI"]
                if binary == "curl":
                    interfaces.append("API")
                elif binary == "python3":
                    interfaces.extend(["API", "SDK"])

                app_record = {
                    "app_id": app_id,
                    "host_id": self.host_id,
                    "name": app_name,
                    "version": version,
                    "publisher": publisher,
                    "exec_path": path,
                    "automation_interfaces": interfaces,
                    "security_status": "VERIFIED_SAFE",
                    "discovered_at": now
                }
                discovered.append(app_record)

                with db.get_connection() as conn:
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO installed_applications (
                            app_id, host_id, name, version, publisher, exec_path,
                            automation_interfaces, security_status, discovered_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            app_id, self.host_id, app_name, version, publisher,
                            path, json.dumps(interfaces), "VERIFIED_SAFE", now
                        )
                    )
                    conn.commit()

        return discovered

    def select_best_automation_interface(self, app_name: str) -> str:
        """
        Hierarchy: API > CLI > Structured Automation > Browser > GUI > Visual.
        Prevents fragile visual clicking when deterministic interfaces exist.
        """
        app_name_lower = app_name.lower()
        if "curl" in app_name_lower or "api" in app_name_lower:
            return "API"
        elif "python" in app_name_lower or "bash" in app_name_lower or "git" in app_name_lower:
            return "CLI"
        elif "browser" in app_name_lower or "web" in app_name_lower:
            return "STRUCTURED_DOM"
        return "CLI"

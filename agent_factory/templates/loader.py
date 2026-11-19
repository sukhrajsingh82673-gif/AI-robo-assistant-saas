"""ZONATA Agent Factory - Template Loader and Resolver.

Loads, validates, and instantiates Agent Templates (zonata.template/v1).
"""

import os
import re
from typing import Any, Dict, List, Optional
import yaml


class TemplateManifest:
    def __init__(self, data: Dict[str, Any], file_path: Optional[str] = None):
        self.raw = data
        self.file_path = file_path
        self.api_version = data.get("apiVersion")
        self.kind = data.get("kind")
        self.metadata = data.get("metadata", {})
        self.name = self.metadata.get("name", "")
        self.version = self.metadata.get("version", "1.0.0")
        self.category = self.metadata.get("category", "custom")
        self.default_risk_tier = self.metadata.get("default_risk_tier", "R1")
        self.parameters = data.get("parameters", {})
        self.base_spec = data.get("base_spec", {})
        self.security_requirements = data.get("security_requirements", {})
        self.test_pack = data.get("test_pack", {})

    def to_dict(self) -> Dict[str, Any]:
        return self.raw

    def instantiate(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Merge base_spec with provided parameters to create a candidate zonata.agent/v1 spec."""
        spec = {
            "apiVersion": "zonata.agent/v1",
            "kind": "Agent",
            "metadata": {
                "name": params.get("name", f"{self.name}-inst"),
                "display_name": params.get("display_name", f"{self.name.replace('-', ' ').title()}"),
                "version": params.get("version", "1.0.0"),
                "category": self.category,
                "risk_tier": self.default_risk_tier,
                "template": f"{self.name}@{self.version}"
            },
            "identity": {
                "principal_kind": "agent",
                "tenant_bound": True,
                "may_use_employees": False
            },
            "role": {
                "title": params.get("role_title", self.base_spec.get("role", {}).get("title", self.name)),
                "mission": params.get("mission", self.base_spec.get("role", {}).get("mission", "Perform assigned tasks")),
                "responsibilities": self.base_spec.get("role", {}).get("responsibilities", ["Execute domain workflows"]),
                "out_of_scope": self.base_spec.get("role", {}).get("out_of_scope", ["Direct production DB writes", "Employee command"]),
                "success_criteria": self.base_spec.get("role", {}).get("success_criteria", ["All outputs pass schema and evidence verification"]),
                "instructions": self.base_spec.get("role", {}).get("instructions", "Follow standard operational protocols.")
            },
            "model": self.base_spec.get("model", {
                "requirements": {
                    "complexity": "medium",
                    "privacy": "internal"
                }
            }),
            "capabilities": self.base_spec.get("capabilities", {"requested": []}),
            "permissions": self.base_spec.get("permissions", {
                "requested": {
                    "tools": [],
                    "network": {"external": False, "allowed_hosts": []},
                    "writes": False
                }
            }),
            "workflow": self.base_spec.get("workflow", {"type": "sequential"}),
            "memory": self.base_spec.get("memory", {
                "conversation": {"enabled": True, "max_messages": 50},
                "pii_policy": "redact"
            }),
            "limits": self.base_spec.get("limits", {
                "max_steps": 30,
                "timeout_seconds": 900,
                "max_cost_usd_per_task": 1.0
            }),
            "io": self.base_spec.get("io", {
                "input_schema": {"type": "object"},
                "output_schema": {"type": "object"}
            }),
            "observability": {
                "trace": True,
                "capture_content": "redacted"
            },
            "tests": self.base_spec.get("tests", {
                "author_cases": [
                    {"id": "smoke_01", "input": {"ping": "pong"}, "expect": {"status": "ok"}, "mandatory": True}
                ],
                "dataset_refs": [f"{self.name}-eval@1.0.0"]
            })
        }
        return spec


class TemplateLoader:
    def __init__(self, starter_dir: Optional[str] = None):
        if starter_dir is None:
            starter_dir = os.path.join(os.path.dirname(__file__), "starter")
        self.starter_dir = starter_dir
        self._templates: Dict[str, Dict[str, TemplateManifest]] = {}  # name -> {version -> Manifest}
        self.load_all()

    def load_all(self) -> None:
        if not os.path.isdir(self.starter_dir):
            return
        for fname in sorted(os.listdir(self.starter_dir)):
            if fname.endswith(".yaml") or fname.endswith(".yml"):
                fpath = os.path.join(self.starter_dir, fname)
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        data = yaml.safe_load(f)
                    if isinstance(data, dict) and data.get("kind") == "AgentTemplate":
                        manifest = TemplateManifest(data, fpath)
                        name = manifest.name
                        ver = manifest.version
                        if name not in self._templates:
                            self._templates[name] = {}
                        self._templates[name][ver] = manifest
                except Exception as e:
                    # Ignore or record error
                    pass

    def list_templates(self) -> List[Dict[str, Any]]:
        results = []
        for name, versions in sorted(self._templates.items()):
            latest_ver = sorted(versions.keys(), reverse=True)[0]
            manifest = versions[latest_ver]
            results.append({
                "name": name,
                "latest_version": latest_ver,
                "versions": sorted(list(versions.keys())),
                "category": manifest.category,
                "risk_tier": manifest.default_risk_tier,
                "description": manifest.metadata.get("description", "")
            })
        return results

    def resolve(self, template_ref: str) -> Optional[TemplateManifest]:
        """Resolve 'name@semver' or 'name' (returns latest)."""
        if "@" in template_ref:
            name, ver = template_ref.split("@", 1)
            return self._templates.get(name, {}).get(ver)
        else:
            versions = self._templates.get(template_ref, {})
            if not versions:
                return None
            latest_ver = sorted(versions.keys(), reverse=True)[0]
            return versions[latest_ver]

    def register(self, manifest: TemplateManifest) -> None:
        name = manifest.name
        ver = manifest.version
        if name not in self._templates:
            self._templates[name] = {}
        self._templates[name][ver] = manifest

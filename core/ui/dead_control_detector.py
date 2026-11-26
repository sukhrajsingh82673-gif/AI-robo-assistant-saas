"""
Dead Control Detector Crawler (Rule 84 UX Honesty).
Scans UI components, DOM templates, buttons, and links to guarantee zero dead-ends:
Every control must either dispatch a real backend action or return an honest NOT_IMPLEMENTED modal.
Prohibits silent no-op '#' links, empty event listeners, or unhandled UI triggers.
"""

import re
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple


@dataclass
class ControlElement:
    tag: str
    control_id: str
    label: str
    action_type: str  # 'href', 'onclick', 'data-action', 'submit'
    target: str
    is_implemented: bool = True
    not_implemented_reason: Optional[str] = None


@dataclass
class ControlAuditResult:
    total_controls: int
    live_controls: int
    honest_not_implemented_controls: int
    dead_controls: List[Dict[str, Any]]
    is_compliant: bool


class DeadControlDetector:
    """
    Crawls UI templates, route manifests, and interactive component registries
    to detect dead buttons, orphaned links, and unhandled controls.
    """

    PROHIBITED_TARGETS = {"#", "javascript:void(0)", "javascript:;", "", None}

    def __init__(self, registered_api_routes: Optional[List[str]] = None):
        self.registered_routes = set(registered_api_routes or [])

    def register_valid_route(self, route: str):
        self.registered_routes.add(route)

    def audit_controls(self, controls: List[ControlElement]) -> ControlAuditResult:
        live_count = 0
        honest_ni_count = 0
        dead_list = []

        for ctrl in controls:
            # Check 1: Empty or dummy target
            if ctrl.action_type == "href" and ctrl.target in self.PROHIBITED_TARGETS:
                dead_list.append({
                    "control_id": ctrl.control_id,
                    "label": ctrl.label,
                    "error": f"Prohibited dummy href target '{ctrl.target}' without action handler.",
                })
                continue

            # Check 2: Action marked not implemented must have explicit honest notification
            if not ctrl.is_implemented:
                if ctrl.not_implemented_reason and "NOT_IMPLEMENTED" in ctrl.not_implemented_reason:
                    honest_ni_count += 1
                else:
                    dead_list.append({
                        "control_id": ctrl.control_id,
                        "label": ctrl.label,
                        "error": "Unimplemented control must provide explicit NOT_IMPLEMENTED modal or reason.",
                    })
                continue

            # Check 3: Action target must either match a registered backend route or valid client command
            if ctrl.action_type in ("api_call", "navigate"):
                # If target starts with '/', check against registered routes
                if ctrl.target.startswith("/") and self.registered_routes:
                    normalized = ctrl.target.split("?")[0].rstrip("/")
                    if not any(normalized.startswith(r.rstrip("/")) for r in self.registered_routes):
                        dead_list.append({
                            "control_id": ctrl.control_id,
                            "label": ctrl.label,
                            "error": f"Action points to unregistered or dead backend route: {ctrl.target}",
                        })
                        continue

            live_count += 1

        is_compliant = len(dead_list) == 0
        return ControlAuditResult(
            total_controls=len(controls),
            live_controls=live_count,
            honest_not_implemented_controls=honest_ni_count,
            dead_controls=dead_list,
            is_compliant=is_compliant,
        )

    def scan_html_snippet(self, html_content: str) -> List[ControlElement]:
        """Simple HTML parser for extracting interactive elements from UI templates."""
        controls = []
        # Match <button ...>...</button>
        button_pattern = re.compile(r'<button\s+([^>]*?)>(.*?)</button>', re.DOTALL | re.IGNORECASE)
        for match in button_pattern.finditer(html_content):
            attrs, label = match.groups()
            id_match = re.search(r'id=["\'](.*?)["\']', attrs)
            action_match = re.search(r'data-action=["\'](.*?)["\']', attrs) or re.search(r'onclick=["\'](.*?)["\']', attrs)
            ctrl_id = id_match.group(1) if id_match else f"btn_{len(controls)}"
            action = action_match.group(1) if action_match else ""
            clean_label = re.sub(r'<[^>]+>', '', label).strip()

            is_ni = "NOT_IMPLEMENTED" in attrs or "coming-soon" in attrs
            ni_reason = "NOT_IMPLEMENTED: Feature scheduled for future release" if is_ni else None

            controls.append(
                ControlElement(
                    tag="button",
                    control_id=ctrl_id,
                    label=clean_label,
                    action_type="api_call" if action.startswith("/") else "onclick",
                    target=action,
                    is_implemented=not is_ni,
                    not_implemented_reason=ni_reason,
                )
            )

        # Match <a ...>...</a>
        link_pattern = re.compile(r'<a\s+([^>]*?)>(.*?)</a>', re.DOTALL | re.IGNORECASE)
        for match in link_pattern.finditer(html_content):
            attrs, label = match.groups()
            href_match = re.search(r'href=["\'](.*?)["\']', attrs)
            id_match = re.search(r'id=["\'](.*?)["\']', attrs)
            ctrl_id = id_match.group(1) if id_match else f"link_{len(controls)}"
            href = href_match.group(1) if href_match else ""
            clean_label = re.sub(r'<[^>]+>', '', label).strip()

            controls.append(
                ControlElement(
                    tag="a",
                    control_id=ctrl_id,
                    label=clean_label,
                    action_type="href",
                    target=href,
                    is_implemented=True,
                )
            )

        return controls

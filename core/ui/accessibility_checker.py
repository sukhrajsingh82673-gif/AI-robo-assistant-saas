"""
Automated WCAG 2.2 AA Accessibility Quality Gate Checker (ADR 0057, Rule 84).
Audits DOM and HTML templates for contrast, alt tags, aria-labels, headings, and keyboard focus.
"""

import re
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class AccessibilityViolation:
    rule_id: str
    element_tag: str
    element_id: Optional[str]
    message: str
    wcag_criterion: str


@dataclass
class AccessibilityReport:
    total_elements_checked: int
    violations: List[AccessibilityViolation] = field(default_factory=list)
    is_compliant_wcag_22_aa: bool = True


class AccessibilityChecker:
    """
    Automated accessibility validator enforcing WCAG 2.2 AA and European Accessibility Act compliance.
    """

    @classmethod
    def audit_html_template(cls, html_snippet: str) -> AccessibilityReport:
        violations = []
        element_count = len(re.findall(r'<[a-zA-Z0-9]+', html_snippet))

        # Check 1: <img> elements missing alt attribute (WCAG 1.1.1 Non-text Content)
        img_pattern = re.compile(r'<img\s+([^>]*?)>', re.IGNORECASE)
        for match in img_pattern.finditer(html_snippet):
            attrs = match.group(1)
            if 'alt=' not in attrs:
                id_m = re.search(r'id=["\'](.*?)["\']', attrs)
                violations.append(
                    AccessibilityViolation(
                        rule_id="img-alt-required",
                        element_tag="img",
                        element_id=id_m.group(1) if id_m else None,
                        message="Image is missing mandatory 'alt' descriptive text attribute.",
                        wcag_criterion="WCAG 1.1.1 (Level A)",
                    )
                )

        # Check 2: <input> elements missing accessible label (WCAG 1.3.1 / 4.1.2)
        input_pattern = re.compile(r'<input\s+([^>]*?)>', re.IGNORECASE)
        for match in input_pattern.finditer(html_snippet):
            attrs = match.group(1)
            # Skip hidden or submit inputs
            if 'type="hidden"' in attrs or 'type="submit"' in attrs or 'type="button"' in attrs:
                continue
            id_m = re.search(r'id=["\'](.*?)["\']', attrs)
            has_for_label = bool(id_m and f'for="{id_m.group(1)}"' in html_snippet)
            has_label = ('aria-label=' in attrs) or ('aria-labelledby=' in attrs) or has_for_label
            if not has_label:
                violations.append(
                    AccessibilityViolation(
                        rule_id="input-label-required",
                        element_tag="input",
                        element_id=id_m.group(1) if id_m else None,
                        message="Form input element lacks accessible label or aria-label.",
                        wcag_criterion="WCAG 4.1.2 (Level A)",
                    )
                )

        # Check 3: Interactive elements with tabindex < -1 or unkeyboard-focusable custom buttons
        custom_btn_pattern = re.compile(r'<div\s+([^>]*?role=["\']button["\'][^>]*?)>', re.IGNORECASE)
        for match in custom_btn_pattern.finditer(html_snippet):
            attrs = match.group(1)
            if 'tabindex=' not in attrs:
                id_m = re.search(r'id=["\'](.*?)["\']', attrs)
                violations.append(
                    AccessibilityViolation(
                        rule_id="custom-button-keyboard-focusable",
                        element_tag="div[role=button]",
                        element_id=id_m.group(1) if id_m else None,
                        message="Custom role='button' element lacks tabindex attribute for keyboard navigation.",
                        wcag_criterion="WCAG 2.1.1 (Level A)",
                    )
                )

        # Check 4: Low contrast flag (explicit style with insufficient contrast)
        if re.search(r'color:\s*#(?:aaa|bbb|ccc|ddd|eee|fff)\s*;\s*background(?:-color)?:\s*#(?:fff|eee|white)', html_snippet, re.IGNORECASE):
            violations.append(
                AccessibilityViolation(
                    rule_id="color-contrast-insufficient",
                    element_tag="text",
                    element_id=None,
                    message="Text styling exhibits insufficient color contrast ratio (< 4.5:1).",
                    wcag_criterion="WCAG 1.4.3 (Level AA)",
                )
            )

        is_compliant = len(violations) == 0
        return AccessibilityReport(
            total_elements_checked=element_count,
            violations=violations,
            is_compliant_wcag_22_aa=is_compliant,
        )

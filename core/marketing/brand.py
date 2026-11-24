"""
Brand Guidelines Validator
==========================
Adheres to:
- Rule 44: No "better than human" or superhuman claims.
- Banned superlatives ('fastest', 'cheapest', 'only', etc.)
- Disallowed misleading terminology.
"""

import os
import json
import re
from typing import List, Dict, Tuple, Any, Optional
from pydantic import BaseModel, Field

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BRAND_GUIDELINES_PATH = os.path.join(REPO_ROOT, "packs", "brand", "brand_guidelines.json")


class BrandViolation(BaseModel):
    category: str  # 'disallowed_term', 'forbidden_superlative', 'rule_44_claim'
    matched_text: str
    message: str


class BrandValidationResult(BaseModel):
    is_compliant: bool
    violations: List[BrandViolation] = Field(default_factory=list)
    word_count: int


class BrandGuidelinesValidator:
    """Validates marketing copy against structured brand rules."""

    def __init__(self, guidelines_path: Optional[str] = None):
        path = guidelines_path or BRAND_GUIDELINES_PATH
        with open(path, "r", encoding="utf-8") as f:
            self.guidelines = json.load(f)

    def validate_copy(self, text: str) -> BrandValidationResult:
        violations: List[BrandViolation] = []
        lower_text = text.lower()
        words = re.findall(r"\b\w+\b", lower_text)

        # 1. Check Rule 44 violations (no 'better than human' or replacement claims)
        for phrase in self.guidelines.get("rule_44_banned_phrases", []):
            if phrase in lower_text:
                violations.append(BrandViolation(
                    category="rule_44_claim",
                    matched_text=phrase,
                    message=f"Rule 44 Violation: '{phrase}' makes an ungrounded or superhuman claim"
                ))

        # 2. Check forbidden superlatives
        for sup in self.guidelines.get("forbidden_superlatives", []):
            pattern = rf"\b{re.escape(sup)}\b"
            if re.search(pattern, lower_text):
                violations.append(BrandViolation(
                    category="forbidden_superlative",
                    matched_text=sup,
                    message=f"Forbidden superlative: '{sup}' is banned without independent third-party certification"
                ))

        # 3. Check disallowed terms
        for term in self.guidelines.get("disallowed_terms", []):
            pattern = rf"\b{re.escape(term)}\b"
            if re.search(pattern, lower_text):
                violations.append(BrandViolation(
                    category="disallowed_term",
                    matched_text=term,
                    message=f"Disallowed brand term: '{term}' violates voice guidelines"
                ))

        return BrandValidationResult(
            is_compliant=len(violations) == 0,
            violations=violations,
            word_count=len(words)
        )

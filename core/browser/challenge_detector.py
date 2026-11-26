"""
ZONATA Verification Challenge Detector (Rule 25 / Sub-Step 3E)
Detects bot checks, CAPTCHAs, and verification challenges.
Strict Invariant: NEVER solve, bypass, or spoof. Handoff to human immediately.
"""

from __future__ import annotations

import re
import logging
from typing import Dict, List, Optional, Tuple, Any

from .types import ChallengeType, ChallengeDetectionResult

logger = logging.getLogger("zonata.browser.challenge")


class ChallengeDetector:
    """
    Scans HTML, DOM structures, and URL fragments for verification challenges.
    """

    CHALLENGE_PATTERNS = {
        ChallengeType.CLOUDFLARE_TURNSTILE: [
            r"cf-turnstile",
            r"challenges\.cloudflare\.com/turnstile",
            r"challenges\.cloudflare\.com/cdn-cgi/challenge-platform",
            r"_cf_chl_",
        ],
        ChallengeType.RECAPTCHA: [
            r"g-recaptcha",
            r"google\.com/recaptcha",
            r"recaptcha/api\.js",
            r"grecaptcha\.execute",
        ],
        ChallengeType.HCAPTCHA: [
            r"h-captcha",
            r"hcaptcha\.com/1/api\.js",
            r"hcaptcha\.com/checksiteconfig",
        ],
        ChallengeType.ARKOSE_LABS: [
            r"arkoselabs\.com",
            r"client-api\.arkoselabs\.com",
            r"fc-token",
        ],
        ChallengeType.BOTGUARD: [
            r"botguard",
            r"google\.com/botguard",
            r"bg-response",
        ],
        ChallengeType.QUEUE_IT: [
            r"queue-it\.net",
            r"c\.queue-it\.net",
        ],
    }

    @classmethod
    def detect(cls, html_or_text: str, current_url: str = "") -> ChallengeDetectionResult:
        if not html_or_text:
            return ChallengeDetectionResult(
                has_challenge=False,
                challenge_type=ChallengeType.NONE,
                signatures_detected=[],
            )

        detected_type = ChallengeType.NONE
        signatures = []

        combined = f"{current_url}\n{html_or_text}"

        for c_type, patterns in cls.CHALLENGE_PATTERNS.items():
            for p in patterns:
                if re.search(p, combined, re.IGNORECASE):
                    detected_type = c_type
                    signatures.append(p)

            if detected_type != ChallengeType.NONE:
                break

        has_challenge = detected_type != ChallengeType.NONE
        masked_bounds = None
        if has_challenge:
            # Mask the challenge widget area (Rule 24 & Rule 25)
            masked_bounds = {"x": 50, "y": 100, "width": 400, "height": 160}

        return ChallengeDetectionResult(
            has_challenge=has_challenge,
            challenge_type=detected_type,
            signatures_detected=signatures,
            hand_off_required=has_challenge,
            masked_widget_bounds=masked_bounds,
        )

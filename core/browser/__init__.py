"""
ZONATA Governed Browser Automation Engine (OpenCode Step 3E)
"""

from .types import ChallengeType, ChallengeDetectionResult, BrowserDownloadResult
from .challenge_detector import ChallengeDetector
from .downloads import BrowserDownloadPipeline, EXECUTABLE_EXTENSIONS
from .engine import GovernedBrowserEngine

__all__ = [
    "ChallengeType",
    "ChallengeDetectionResult",
    "BrowserDownloadResult",
    "ChallengeDetector",
    "BrowserDownloadPipeline",
    "EXECUTABLE_EXTENSIONS",
    "GovernedBrowserEngine",
]

"""
ZONATA Governed Browser — Anti-Bot Challenge Policy & Official Route Engine (Rule 25).

Enforces Rule 25:
When a verification challenge (Turnstile, reCAPTCHA, hCaptcha, Arkose Labs, Botguard)
is encountered:
1. Stop immediately — no solvers, no evasion, no stealth scripts.
2. Hand off to human inbox with state BLOCKED.
3. Provide structured suggestions for official alternatives (APIs, exports, allow-listing).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from core.browser.types import ChallengeDetectionResult, ChallengeType


@dataclass(frozen=True)
class OfficialRouteSuggestion:
    category: str  # "OFFICIAL_API", "DATA_EXPORT", "IP_ALLOWLIST", "SITE_SETTINGS"
    title: str
    description: str
    action_url: Optional[str] = None
    documentation_url: Optional[str] = None


# Known public enterprise APIs for common sites
KNOWN_OFFICIAL_APIS: Dict[str, List[OfficialRouteSuggestion]] = {
    "github.com": [
        OfficialRouteSuggestion(
            category="OFFICIAL_API",
            title="GitHub REST & GraphQL API",
            description="Use personal access tokens or GitHub App installations instead of web scraping.",
            documentation_url="https://docs.github.com/en/rest",
        ),
    ],
    "stripe.com": [
        OfficialRouteSuggestion(
            category="OFFICIAL_API",
            title="Stripe Official API",
            description="Configure Stripe API keys in the credential vault for programmatic financial interactions.",
            documentation_url="https://stripe.com/docs/api",
        ),
    ],
    "cloudflare.com": [
        OfficialRouteSuggestion(
            category="IP_ALLOWLIST",
            title="Cloudflare WAF / Access Allow-listing",
            description="Add corporate agent egress IPs to the Cloudflare WAF allow-list or Security Rules.",
            documentation_url="https://developers.cloudflare.com/waf/",
        ),
    ],
    "linkedin.com": [
        OfficialRouteSuggestion(
            category="OFFICIAL_API",
            title="LinkedIn Marketing & Developer APIs",
            description="Request authorized OAuth 2.0 app access via LinkedIn Developer Portal.",
            documentation_url="https://developer.linkedin.com/",
        ),
    ],
}


class ChallengePolicyEngine:
    """
    Evaluates anti-bot challenge events and coordinates Rule 25 compliance.
    """

    @classmethod
    def evaluate_challenge(
        cls,
        detection: ChallengeDetectionResult,
        task_id: str,
        tenant_id: str,
        company_id: str,
        url: str,
    ) -> Dict[str, Any]:
        """
        Process a detected verification challenge.
        Halts automation, marks task as BLOCKED, and returns human handoff package
        with suggested official routes.
        """
        if not detection.has_challenge:
            return {"status": "NO_CHALLENGE", "action": "PROCEED"}

        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        if ":" in domain:
            domain = domain.split(":")[0]

        suggestions = cls.suggest_official_routes(url=url, domain=domain)

        # Human inbox payload with masked challenge widget coordinates
        inbox_item = {
            "task_id": task_id,
            "tenant_id": tenant_id,
            "company_id": company_id,
            "status": "BLOCKED",
            "reason": f"Verification challenge encountered: {detection.challenge_type.value}",
            "challenge_type": detection.challenge_type.value,
            "target_url": url,
            "target_domain": domain,
            "widget_bounding_box": detection.masked_widget_bounds,
            "prompt": (
                f"A verification challenge ({detection.challenge_type.value}) appeared at {domain}. "
                "Per Rule 25, automated evasion and solvers are strictly prohibited. "
                "Please solve this challenge manually in the remote browser window or authorize an official route."
            ),
            "official_route_suggestions": [
                {
                    "category": s.category,
                    "title": s.title,
                    "description": s.description,
                    "documentation_url": s.documentation_url,
                }
                for s in suggestions
            ],
        }

        return {
            "status": "BLOCKED",
            "action": "HALT_AND_HANDOFF_TO_HUMAN",
            "inbox_item": inbox_item,
        }

    @classmethod
    def suggest_official_routes(cls, url: str, domain: str) -> List[OfficialRouteSuggestion]:
        """
        Generate official route recommendations for the blocked domain.
        """
        suggestions: List[OfficialRouteSuggestion] = []

        # Check known domain mappings
        for known_domain, known_routes in KNOWN_OFFICIAL_APIS.items():
            if domain == known_domain or domain.endswith("." + known_domain):
                suggestions.extend(known_routes)

        # Always offer generic standard compliance routes
        suggestions.append(
            OfficialRouteSuggestion(
                category="IP_ALLOWLIST",
                title="Egress IP Allow-Listing",
                description="Coordinate with the website owner or security team to allow-list agent egress IP addresses.",
            )
        )
        suggestions.append(
            OfficialRouteSuggestion(
                category="DATA_EXPORT",
                title="Direct Data Export / Webhooks",
                description="Utilize standard CSV/JSON export or webhook integrations rather than DOM scraping.",
            )
        )
        suggestions.append(
            OfficialRouteSuggestion(
                category="SITE_SETTINGS",
                title="Site Owner Verification Exemption",
                description="Configure test credentials or bypass cookies provided directly by the target service provider.",
            )
        )

        return suggestions

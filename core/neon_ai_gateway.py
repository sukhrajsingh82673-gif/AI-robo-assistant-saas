"""
ZONATA Enterprise SaaS — Neon AI Gateway Client
Provides model routing, chat completions, and text embeddings via Databricks-backed
Neon AI Gateway, scoped to the active Neon database branch.
"""

import os
import sys
import json
import urllib.request
import urllib.error
from typing import Optional, Dict, Any, List

from core.neon_env import get_neon_ai_gateway_base_url, get_neon_ai_gateway_token


class NeonAIGatewayClient:
    """Client for routing frontier LLM and embedding requests through Neon AI Gateway."""

    def __init__(self):
        pass

    @property
    def base_url(self) -> str:
        return get_neon_ai_gateway_base_url()

    @property
    def token(self) -> str:
        return get_neon_ai_gateway_token()

    def is_configured(self) -> bool:
        return bool(self.base_url and self.token)

    def get_status(self) -> Dict[str, Any]:
        """Return diagnostic status of AI Gateway integration."""
        configured = self.is_configured()
        return {
            "configured": configured,
            "provider": "Neon AI Gateway (Databricks)",
            "base_url": self.base_url if configured else None,
            "tier_support": "Neon Paid Plans (Pro, Scale, Enterprise)",
            "free_tier_status": "Disabled on Free plan. Requires upgrading organization billing to provision on branch.",
            "supported_models": [
                "claude-sonnet-4-6",
                "gpt-5-mini",
                "gemini-3-flash",
                "databricks-meta-llama-3-3-70b-instruct"
            ]
        }

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = "gpt-5-mini",
        temperature: float = 0.7,
        max_tokens: int = 1024
    ) -> Dict[str, Any]:
        """Send chat completion request through Neon AI Gateway OpenAI-compatible endpoint."""
        if not self.is_configured():
            return {
                "success": False,
                "error": "Neon AI Gateway is not provisioned on this Free plan branch (requires paid upgrade).",
                "status": self.get_status()
            }

        url = f"{self.base_url.rstrip('/')}/v1/chat/completions"
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "User-Agent": "ZONATA-Enterprise/1.0"
        }
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=45) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return {"success": True, "data": data}
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8") if e.fp else str(e)
            return {"success": False, "status_code": e.code, "error": err_body}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def embeddings(self, input_text: str, model: str = "text-embedding-3-small") -> Dict[str, Any]:
        """Generate text embeddings through Neon AI Gateway."""
        if not self.is_configured():
            return {
                "success": False,
                "error": "Neon AI Gateway is not provisioned on this Free plan branch (requires paid upgrade).",
                "status": self.get_status()
            }

        url = f"{self.base_url.rstrip('/')}/v1/embeddings"
        payload = {"model": model, "input": input_text}
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "User-Agent": "ZONATA-Enterprise/1.0"
        }
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return {"success": True, "data": data}
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8") if e.fp else str(e)
            return {"success": False, "status_code": e.code, "error": err_body}
        except Exception as e:
            return {"success": False, "error": str(e)}


# Singleton instance
neon_ai_gateway = NeonAIGatewayClient()

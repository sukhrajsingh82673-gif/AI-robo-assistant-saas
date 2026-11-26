"""
Developer Portal and Sandbox Interactive Documentation (ADR 0051).
"""

import json
from typing import Dict, Any


class DeveloperPortal:
    """
    Renders developer documentation, OpenAPI specification viewer, and interactive SDK snippets.
    """

    @staticmethod
    def get_code_snippets(endpoint: str, method: str = "POST") -> Dict[str, str]:
        return {
            "curl": (
                f"curl -X {method} https://api.zonata.ai/api/public/v1{endpoint} \\\n"
                f"  -H 'Authorization: Bearer <YOUR_API_KEY>' \\\n"
                f"  -H 'Idempotency-Key: $(uuidgen)' \\\n"
                f"  -H 'Content-Type: application/json' \\\n"
                f"  -d '{{\"instruction\": \"Analyze quarterly variance\"}}'"
            ),
            "python": (
                "from zonata_sdk import ZonataClient\n\n"
                "client = ZonataClient(api_key='<YOUR_API_KEY>')\n"
                f"response = client.post('{endpoint}', data={{'instruction': 'Analyze quarterly variance'}})\n"
                "print(response)"
            ),
            "typescript": (
                "import { ZonataClient } from '@zonata/sdk';\n\n"
                "const client = new ZonataClient({ apiKey: '<YOUR_API_KEY>' });\n"
                f"const response = await client.post('{endpoint}', {{ instruction: 'Analyze quarterly variance' }});\n"
                "console.log(response);"
            ),
        }

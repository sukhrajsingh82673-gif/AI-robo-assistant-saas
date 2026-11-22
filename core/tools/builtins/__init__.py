"""ZONATA Sovereign Core — Builtin Tool Package.

Registers all Step 2E built-in tools into the global tool registry:
- Calculator (Deterministic exact Decimal arithmetic)
- Document (Search, Read with untrusted delimiter, Create)
- Folio (Read, Append)
- Ledger (Read, Post through ActionGateway)
- Email (Send through SMTP/Mailpit, Read)
- Calendar (Create RFC 5545, Read)
- KPI (Read current value and trend)
"""

from core.tools.registry import tool_registry

# Import tool classes
from core.tools.builtins.calculator_tool import CalculatorTool
from core.tools.builtins.document_tools import (
    DocumentSearchTool,
    DocumentReadTool,
    DocumentCreateTool,
)
from core.tools.builtins.folio_tools import FolioReadTool, FolioAppendTool
from core.tools.builtins.ledger_tools import LedgerReadTool, LedgerPostTool
from core.tools.builtins.email_tools import EmailSendTool, EmailReadTool
from core.tools.builtins.calendar_tools import CalendarCreateTool, CalendarReadTool
from core.tools.builtins.kpi_tools import KPIReadTool


def register_all_builtin_tools() -> None:
    """Registers all standard builtin tools into the global tool registry."""
    tools = [
        CalculatorTool(),
        DocumentSearchTool(),
        DocumentReadTool(),
        DocumentCreateTool(),
        FolioReadTool(),
        FolioAppendTool(),
        LedgerReadTool(),
        LedgerPostTool(),
        EmailSendTool(),
        EmailReadTool(),
        CalendarCreateTool(),
        CalendarReadTool(),
        KPIReadTool(),
    ]
    for t in tools:
        tool_registry.register(t)


# Register immediately on module import
register_all_builtin_tools()

__all__ = [
    "CalculatorTool",
    "DocumentSearchTool",
    "DocumentReadTool",
    "DocumentCreateTool",
    "FolioReadTool",
    "FolioAppendTool",
    "LedgerReadTool",
    "LedgerPostTool",
    "EmailSendTool",
    "EmailReadTool",
    "CalendarCreateTool",
    "CalendarReadTool",
    "KPIReadTool",
    "register_all_builtin_tools",
]

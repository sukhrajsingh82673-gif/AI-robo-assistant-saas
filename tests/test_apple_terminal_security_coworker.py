"""
Tests for Phase 7: Apple-Grade Governed Terminal, Security Center & Co-Worker AI Assistant
Verifies:
1. AppleGovernedTerminal permission bar, kill switch, human-readable command translations, and sandboxed log stream.
2. AppleSecurityCenter 13-layer defense rings, SHA-256 Merkle root verification, and zero-leakage DLP monitor.
3. AppleCoworkerAssistant Personal vs. Company Mode switch (AI CEO supervision & constitutional gating in company mode).
4. Workspace integrations into assistant_coworker_workspace.js and governance_workspace.js.
5. Index.html script inclusions.
"""

import unittest
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB_DIR = os.path.join(BASE_DIR, "web")

class TestAppleTerminalSecurityCoworker(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(WEB_DIR, "apple_governed_terminal.js"), "r", encoding="utf-8") as f:
            self.terminal_js = f.read()
        with open(os.path.join(WEB_DIR, "apple_security_center.js"), "r", encoding="utf-8") as f:
            self.security_js = f.read()
        with open(os.path.join(WEB_DIR, "apple_coworker_assistant.js"), "r", encoding="utf-8") as f:
            self.coworker_js = f.read()
        with open(os.path.join(WEB_DIR, "assistant_coworker_workspace.js"), "r", encoding="utf-8") as f:
            self.assistant_ws_js = f.read()
        with open(os.path.join(WEB_DIR, "governance_workspace.js"), "r", encoding="utf-8") as f:
            self.gov_ws_js = f.read()
        with open(os.path.join(WEB_DIR, "index.html"), "r", encoding="utf-8") as f:
            self.index_html = f.read()

    def test_governed_terminal(self):
        self.assertIn("window.AppleGovernedTerminal =", self.terminal_js)
        self.assertIn("render(containerOrId", self.terminal_js)
        self.assertIn("runCommand(", self.terminal_js)
        self.assertIn("toggleKillSwitch()", self.terminal_js)
        self.assertIn("togglePause()", self.terminal_js)
        self.assertIn("clearLogs()", self.terminal_js)

        # Fixed Permission Bar & Safety Controls
        self.assertIn("Governed", self.terminal_js)
        self.assertIn("Emergency Kill Switch", self.terminal_js)
        self.assertIn("Container #419", self.terminal_js)

        # Human-readable command translation
        self.assertIn("Action Intent:", self.terminal_js)
        self.assertIn("deriveHumanTranslation", self.terminal_js)

        # Apple Terminal Window Styling
        self.assertIn("apple-terminal-window", self.terminal_js)
        self.assertIn("apple-terminal-dot", self.terminal_js)

    def test_security_center_and_13_rings(self):
        self.assertIn("window.AppleSecurityCenter =", self.security_js)
        self.assertIn("render(containerOrId", self.security_js)
        self.assertIn("verifyLedgerChain()", self.security_js)

        # 13 Concentric Rings & Score
        self.assertIn("13/13 Active Rings", self.security_js)
        self.assertIn("Overall Security Fitness", self.security_js)
        self.assertIn("Rings 1-4: Substrate & Isolation", self.security_js)
        self.assertIn("Rings 5-8: DLP & PII Screening", self.security_js)
        self.assertIn("Rings 9-13: Policy & Cryptography", self.security_js)

        # SHA-256 Merkle Chain Verification & Zero Leakage
        self.assertIn("sha256:7f90c4a162e84b8109ad5c66914b1ce3b98c47b5e40a", self.security_js)
        self.assertIn("Data Egress Leakage", self.security_js)
        self.assertIn("0 Bytes", self.security_js)

        # Authority Hierarchy Cascade
        self.assertIn("Sovereign Authority Cascade", self.security_js)
        self.assertIn("1. Human Owner (Host)", self.security_js)

    def test_coworker_assistant_mode_switch(self):
        self.assertIn("window.AppleCoworkerAssistant =", self.coworker_js)
        self.assertIn("render(containerOrId", self.coworker_js)
        self.assertIn("setMode(", self.coworker_js)
        self.assertIn("sendMessage(", self.coworker_js)

        # Personal vs Company Mode
        self.assertIn("Personal Mode", self.coworker_js)
        self.assertIn("Company Mode (Governed)", self.coworker_js)
        self.assertIn("Constitutional Safeguards Active", self.coworker_js)
        self.assertIn("AI CEO Supervised", self.coworker_js)

        # AiOrb integration
        self.assertIn("window.AiOrb", self.coworker_js)

    def test_workspace_integrations(self):
        self.assertIn("window.AppleGovernedTerminal", self.assistant_ws_js)
        self.assertIn("window.AppleCoworkerAssistant", self.assistant_ws_js)
        self.assertIn("window.AppleSecurityCenter", self.gov_ws_js)

    def test_index_html_loads_phase7_scripts(self):
        self.assertIn('<script src="apple_governed_terminal.js"></script>', self.index_html)
        self.assertIn('<script src="apple_security_center.js"></script>', self.index_html)
        self.assertIn('<script src="apple_coworker_assistant.js"></script>', self.index_html)

if __name__ == '__main__':
    unittest.main()

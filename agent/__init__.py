"""
CompLexAI Agent Layer

Layer 2: Autonomous agent orchestration on top of the analysis engine.
Agents accept inputs (repos, binaries, firmware images), decide which
analysis tools to run, interpret results, and produce actionable reports.
"""

from agent.base import AnalysisAgent, AgentResult, AgentFinding
from agent.firmware_audit import FirmwareAuditAgent

__all__ = [
    "AnalysisAgent",
    "AgentResult",
    "AgentFinding",
    "FirmwareAuditAgent",
]

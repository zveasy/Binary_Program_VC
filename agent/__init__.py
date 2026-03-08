"""
CompLexAI Agent Layer

Layer 2: Autonomous agent orchestration on top of the analysis engine.
Agents accept inputs (repos, binaries, firmware images), decide which
analysis tools to run, interpret results, and produce actionable reports.
"""

from agent.base import AnalysisAgent, AgentResult, AgentFinding, Severity, FindingCategory
from agent.firmware_audit import FirmwareAuditAgent
from agent.pr_review import PRComplexityAgent
from agent.unified import UnifiedAuditAgent
from agent.patches import generate_sarif, suggest_patches

__all__ = [
    "AnalysisAgent",
    "AgentResult",
    "AgentFinding",
    "Severity",
    "FindingCategory",
    "FirmwareAuditAgent",
    "PRComplexityAgent",
    "UnifiedAuditAgent",
    "generate_sarif",
    "suggest_patches",
]

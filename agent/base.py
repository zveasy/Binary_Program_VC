"""
Base agent framework — defines the contract all CompLexAI agents follow.
"""

import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class Severity(str, Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class FindingCategory(str, Enum):
    INFINITE_LOOP = "infinite_loop"
    UNREACHABLE_CODE = "unreachable_code"
    HIGH_COMPLEXITY = "high_complexity"
    SUSPICIOUS_FUNCTION = "suspicious_function"
    NO_TIMEOUT = "no_timeout"
    RISK_SCORE = "risk_score"


@dataclass
class AgentFinding:
    """A single finding produced by the agent, with human-readable explanation."""
    category: FindingCategory
    severity: Severity
    title: str
    explanation: str
    addresses: Optional[List[int]] = None
    function_name: Optional[str] = None
    recommendation: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentResult:
    """Complete result from an agent analysis run."""
    agent_name: str
    input_path: str
    timestamp: float = field(default_factory=time.time)
    architecture: str = "Unknown"
    safety_verdict: str = "UNKNOWN"
    risk_score: float = 0.0
    complexity_heuristic: str = "Unknown"
    complexity_gnn: Optional[str] = None
    findings: List[AgentFinding] = field(default_factory=list)
    summary: str = ""
    report_path: Optional[str] = None
    dot_path: Optional[str] = None
    log_path: Optional[str] = None
    duration_seconds: float = 0.0

    @property
    def critical_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.CRITICAL)

    @property
    def warning_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.WARNING)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a JSON-compatible dictionary."""
        return {
            "agent_name": self.agent_name,
            "input_path": self.input_path,
            "timestamp": self.timestamp,
            "architecture": self.architecture,
            "safety_verdict": self.safety_verdict,
            "risk_score": round(self.risk_score, 3),
            "complexity_heuristic": self.complexity_heuristic,
            "complexity_gnn": self.complexity_gnn,
            "findings": [
                {
                    "category": f.category.value,
                    "severity": f.severity.value,
                    "title": f.title,
                    "explanation": f.explanation,
                    "recommendation": f.recommendation,
                    "addresses": f.addresses,
                    "function_name": f.function_name,
                }
                for f in self.findings
            ],
            "summary": self.summary,
            "critical_count": self.critical_count,
            "warning_count": self.warning_count,
            "duration_seconds": round(self.duration_seconds, 2),
            "report_path": self.report_path,
            "dot_path": self.dot_path,
            "log_path": self.log_path,
        }


class AnalysisAgent(ABC):
    """
    Base class for all CompLexAI analysis agents.

    An agent orchestrates the analysis pipeline:
    1. Accept input (binary, repo, firmware image)
    2. Decide which engine tools to run
    3. Collect and interpret results
    4. Produce findings with plain-English explanations
    5. Generate an actionable report
    """

    def __init__(self, name: str, output_dir: str = "agent_output"):
        self.name = name
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    @abstractmethod
    def analyze(self, input_path: str, **kwargs) -> AgentResult:
        """Run the full agent analysis pipeline. Must be implemented by subclasses."""
        ...

    @abstractmethod
    def explain(self, result: AgentResult) -> str:
        """Produce a plain-English summary of the analysis results."""
        ...

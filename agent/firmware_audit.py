"""
FirmwareAuditAgent — autonomous firmware binary audit agent.

Accepts a firmware binary (ELF), orchestrates the full analysis pipeline,
interprets results, ranks findings by severity, and produces an actionable
audit report with plain-English explanations and recommendations.

This is the first concrete agent built on top of the CompLexAI analysis engine.
"""

import os
import time
from typing import Optional

from engine.disassembler import DisassemblerEngine, DisassemblyResult
from engine.report import ReportGenerator
from engine.predictor import ComplexityPredictor
from agent.base import (
    AnalysisAgent, AgentResult, AgentFinding,
    Severity, FindingCategory,
)


class FirmwareAuditAgent(AnalysisAgent):
    """
    Firmware Binary Audit Agent.

    Given a firmware binary, this agent:
    1. Disassembles the binary and builds a CFG
    2. Detects infinite loops and control-flow bugs
    3. Estimates algorithm complexity (heuristic + optional GNN)
    4. Ranks findings by severity
    5. Explains findings in plain English
    6. Produces an actionable audit report

    Usage:
        agent = FirmwareAuditAgent()
        result = agent.analyze("firmware/my_firmware.bin")
        print(agent.explain(result))
    """

    def __init__(self, output_dir: str = "agent_output",
                 model_path: Optional[str] = None,
                 label_map_path: Optional[str] = None):
        super().__init__(name="FirmwareAuditAgent", output_dir=output_dir)

        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self._model_path = model_path or os.path.join(repo_root, "gat_model.pt")
        self._label_map_path = label_map_path or os.path.join(repo_root, "gat_label_map.json")

    def analyze(self, input_path: str, **kwargs) -> AgentResult:
        """Run the complete firmware audit pipeline."""
        start = time.time()
        result = AgentResult(agent_name=self.name, input_path=input_path)

        # Step 1: Disassemble and analyze
        engine = DisassemblerEngine(output_dir=self.output_dir)
        disasm = engine.analyze(input_path)

        result.architecture = disasm.architecture
        result.safety_verdict = disasm.safety_verdict
        result.risk_score = disasm.risk_score
        result.complexity_heuristic = disasm.complexity_heuristic
        result.dot_path = disasm.dot_path
        result.log_path = disasm.log_path

        # Step 2: Optional GNN complexity prediction
        predictor = ComplexityPredictor(self._model_path, self._label_map_path)
        if predictor.available and disasm.dot_path:
            result.complexity_gnn = predictor.predict(disasm.dot_path)

        # Step 3: Interpret findings — translate engine findings into agent findings
        result.findings = self._interpret_findings(disasm)

        # Step 4: Generate report
        report_path = os.path.join(self.output_dir, "audit_report.md")
        ReportGenerator.from_result(disasm, report_path, gnn_complexity=result.complexity_gnn)
        result.report_path = report_path

        # Step 5: Generate summary
        result.summary = self.explain(result)
        result.duration_seconds = time.time() - start

        return result

    def _interpret_findings(self, disasm: DisassemblyResult) -> list:
        """Convert raw engine findings into agent-level findings with explanations."""
        findings = []

        # Infinite loops — critical
        for i, loop in enumerate(disasm.infinite_loops, 1):
            addr_str = ", ".join(f"0x{a:x}" for a in loop)
            func_name = self._resolve_function(disasm, loop[0]) if loop else None

            findings.append(AgentFinding(
                category=FindingCategory.INFINITE_LOOP,
                severity=Severity.CRITICAL,
                title=f"Infinite loop #{i} at {addr_str}",
                explanation=(
                    f"An infinite loop was detected at address(es) {addr_str}. "
                    f"This loop has no exit condition — the program will spin "
                    f"indefinitely if this code path is reached. "
                    f"{'In function: ' + func_name + '. ' if func_name else ''}"
                    f"Risk: device lockup, watchdog timeout, or denial of service."
                ),
                addresses=loop,
                function_name=func_name,
                recommendation=(
                    "Add an exit condition (timeout, iteration limit, or hardware flag check). "
                    "If this is an intentional busy-wait, add a timeout path to prevent lockup."
                ),
            ))

        # Unreachable code — warning
        if disasm.unreachable_code:
            sample_addrs = disasm.unreachable_code[:5]
            addr_str = ", ".join(f"0x{a:x}" for a in sample_addrs)
            total = len(disasm.unreachable_code)

            findings.append(AgentFinding(
                category=FindingCategory.UNREACHABLE_CODE,
                severity=Severity.WARNING,
                title=f"{total} unreachable code block(s) detected",
                explanation=(
                    f"Found {total} code block(s) that cannot be reached from the "
                    f"program entry point. Sample addresses: {addr_str}. "
                    f"This may indicate dead code, compiler artifacts, or control-flow bugs "
                    f"where intended branches were never connected."
                ),
                addresses=disasm.unreachable_code[:20],
                recommendation=(
                    "Review whether these blocks are intentional (e.g. ISR handlers, "
                    "fallback code) or bugs. Remove dead code to reduce attack surface."
                ),
            ))

        # High complexity — warning
        if disasm.complexity_heuristic in ("O(n^2)", "O(n^2) or higher"):
            findings.append(AgentFinding(
                category=FindingCategory.HIGH_COMPLEXITY,
                severity=Severity.WARNING,
                title=f"High algorithmic complexity: {disasm.complexity_heuristic}",
                explanation=(
                    f"The control flow structure suggests {disasm.complexity_heuristic} "
                    f"complexity. This means execution time grows quadratically with input size. "
                    f"For firmware handling large data (network packets, sensor arrays), "
                    f"this could cause timing violations or watchdog resets."
                ),
                recommendation=(
                    "Consider restructuring nested loops. Use hash-based lookups, "
                    "sorting with binary search, or other O(n log n) patterns where possible."
                ),
            ))

        # Overall risk assessment — always present
        risk = disasm.risk_score
        risk_level = "LOW" if risk < 0.3 else "MEDIUM" if risk < 0.6 else "HIGH"
        findings.append(AgentFinding(
            category=FindingCategory.RISK_SCORE,
            severity=Severity.CRITICAL if risk >= 0.6 else Severity.WARNING if risk >= 0.3 else Severity.INFO,
            title=f"Overall risk: {risk_level} ({risk:.2f}/1.00)",
            explanation=(
                f"Combined risk score based on all detected issues: {risk:.2f}/1.00. "
                f"Risk level: {risk_level}. "
                + ("This firmware should be reviewed before deployment." if risk >= 0.3
                   else "No major structural concerns detected.")
            ),
        ))

        findings.sort(key=lambda f: {"critical": 0, "warning": 1, "info": 2}[f.severity.value])
        return findings

    def _resolve_function(self, disasm: DisassemblyResult, addr: int) -> Optional[str]:
        """Try to resolve a function name for a given address."""
        if addr in disasm.symbols:
            name, is_func = disasm.symbols[addr]
            if is_func and name:
                return name
        for sym_addr in sorted(disasm.symbols.keys(), reverse=True):
            if sym_addr <= addr:
                name, is_func = disasm.symbols[sym_addr]
                if is_func and name:
                    return name
                break
        return None

    def explain(self, result: AgentResult) -> str:
        """Produce a plain-English summary of the audit."""
        lines = []
        binary_name = os.path.basename(result.input_path)
        lines.append(f"Firmware Audit Summary for: {binary_name}")
        lines.append(f"Architecture: {result.architecture}")
        lines.append(f"Safety Verdict: {result.safety_verdict}")
        lines.append(f"Risk Score: {result.risk_score:.2f}/1.00")
        lines.append(f"Complexity: {result.complexity_heuristic}")
        if result.complexity_gnn:
            lines.append(f"Complexity (GNN): {result.complexity_gnn}")
        lines.append(f"Critical findings: {result.critical_count}")
        lines.append(f"Warnings: {result.warning_count}")
        lines.append(f"Analysis completed in {result.duration_seconds:.1f}s")
        lines.append("")

        if result.findings:
            lines.append("Key Findings:")
            for f in result.findings:
                icon = "🔴" if f.severity == Severity.CRITICAL else "🟡" if f.severity == Severity.WARNING else "🟢"
                lines.append(f"  {icon} {f.title}")
                lines.append(f"    → {f.explanation}")
                if f.recommendation:
                    lines.append(f"    💡 {f.recommendation}")
                lines.append("")

        return "\n".join(lines)

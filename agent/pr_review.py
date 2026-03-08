"""
PRComplexityAgent — PR complexity review agent.

Accepts a repository path, optionally a list of changed files or a diff,
builds source-level or binary-level CFGs for changed code, and produces
findings comparing complexity before and after the change.
"""

import os
import subprocess
import sys
import time
import tempfile
from typing import Dict, List, Optional

from engine.disassembler import DisassemblerEngine, DisassemblyResult
from engine.report import ReportGenerator
from agent.base import (
    AnalysisAgent, AgentResult, AgentFinding,
    Severity, FindingCategory,
)


def _compile_c_file(src_path: str, output_path: str) -> bool:
    """Compile a C/C++ source file to a binary. Returns True on success."""
    ext = os.path.splitext(src_path)[1].lower()
    compiler = "g++" if ext in (".cpp", ".cc", ".cxx") else "gcc"
    try:
        subprocess.run(
            [compiler, "-o", output_path, src_path],
            capture_output=True, check=True, timeout=30,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return False


class PRComplexityAgent(AnalysisAgent):
    """
    PR Complexity Review Agent.

    Given a repo path and a list of changed files, this agent:
    1. Identifies compilable source files in the changeset
    2. Compiles them to binaries
    3. Runs disassembly and CFG analysis on each
    4. Compares complexity and risk across changed files
    5. Produces a PR review with findings and recommendations

    Usage:
        agent = PRComplexityAgent()
        result = agent.analyze(".", changed_files=["src/parser.c", "src/router.c"])
        print(agent.explain(result))
    """

    COMPILABLE_EXTENSIONS = {".c", ".cpp", ".cc", ".cxx"}

    def __init__(self, output_dir: str = "agent_output"):
        super().__init__(name="PRComplexityAgent", output_dir=output_dir)
        self._engine = DisassemblerEngine(output_dir=output_dir)

    def analyze(self, input_path: str, **kwargs) -> AgentResult:
        """
        Analyze changed files in a repo for complexity regressions.

        Args:
            input_path: Path to the repository root.
            changed_files: List of changed file paths (relative to repo root).
                           If not provided, auto-detects via git diff.
        """
        start = time.time()
        result = AgentResult(agent_name=self.name, input_path=input_path)

        changed_files = kwargs.get("changed_files") or self._detect_changed_files(input_path)

        if not changed_files:
            result.summary = "No changed files to analyze."
            result.safety_verdict = "PASS"
            result.duration_seconds = time.time() - start
            return result

        compilable = [f for f in changed_files
                      if os.path.splitext(f)[1].lower() in self.COMPILABLE_EXTENSIONS]

        if not compilable:
            result.summary = (f"Found {len(changed_files)} changed file(s), "
                              "but none are compilable C/C++ sources.")
            result.safety_verdict = "PASS"
            result.duration_seconds = time.time() - start
            return result

        file_results: Dict[str, DisassemblyResult] = {}
        for src_file in compilable:
            full_path = os.path.join(input_path, src_file) if not os.path.isabs(src_file) else src_file
            if not os.path.isfile(full_path):
                continue

            with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as tmp:
                bin_path = tmp.name

            if _compile_c_file(full_path, bin_path):
                disasm = self._engine.analyze(bin_path)
                file_results[src_file] = disasm
            try:
                os.unlink(bin_path)
            except OSError:
                pass

        result.findings = self._interpret_results(file_results)
        result.safety_verdict = "FAIL" if any(
            f.severity == Severity.CRITICAL for f in result.findings
        ) else "PASS"
        result.risk_score = max(
            (fr.risk_score for fr in file_results.values()), default=0.0
        )

        total_loops = sum(len(fr.infinite_loops) for fr in file_results.values())
        complexities = [fr.complexity_heuristic for fr in file_results.values()]
        worst = max(complexities, key=lambda c: {"O(1)": 0, "O(n)": 1, "O(n^2)": 2}.get(c, 3), default="Unknown")
        result.complexity_heuristic = worst

        report_path = os.path.join(self.output_dir, "pr_review_report.md")
        self._write_report(file_results, result.findings, report_path)
        result.report_path = report_path

        result.summary = self.explain(result)
        result.duration_seconds = time.time() - start
        return result

    def _detect_changed_files(self, repo_path: str) -> List[str]:
        """Auto-detect changed files using git diff against the default branch."""
        try:
            diff = subprocess.run(
                ["git", "diff", "--name-only", "HEAD~1"],
                capture_output=True, text=True, cwd=repo_path, timeout=10,
            )
            if diff.returncode == 0:
                return [f.strip() for f in diff.stdout.strip().split("\n") if f.strip()]
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        return []

    def _interpret_results(self, file_results: Dict[str, DisassemblyResult]) -> List[AgentFinding]:
        """Produce findings from per-file analysis results."""
        findings = []
        for src_file, disasm in file_results.items():
            if disasm.infinite_loops:
                findings.append(AgentFinding(
                    category=FindingCategory.INFINITE_LOOP,
                    severity=Severity.CRITICAL,
                    title=f"Infinite loop introduced in {src_file}",
                    explanation=(
                        f"`{src_file}` contains {len(disasm.infinite_loops)} infinite loop(s). "
                        f"This will cause the program to hang indefinitely."
                    ),
                    recommendation="Add exit conditions (timeout, counter, or flag check) to all loops.",
                ))

            if disasm.complexity_heuristic in ("O(n^2)", "O(n^2) or higher"):
                findings.append(AgentFinding(
                    category=FindingCategory.HIGH_COMPLEXITY,
                    severity=Severity.WARNING,
                    title=f"High complexity in {src_file}: {disasm.complexity_heuristic}",
                    explanation=(
                        f"`{src_file}` shows {disasm.complexity_heuristic} algorithmic complexity. "
                        f"This may degrade performance under large inputs."
                    ),
                    recommendation=(
                        "Consider using hash-based lookups or sorting with binary search "
                        "to reduce nested iteration."
                    ),
                ))

        findings.sort(key=lambda f: {"critical": 0, "warning": 1, "info": 2}[f.severity.value])
        return findings

    def _write_report(self, file_results, findings, report_path):
        lines = ["# PR Complexity Review Report\n"]
        lines.append(f"**Files analyzed:** {len(file_results)}\n")

        lines.append("## Per-File Summary\n")
        lines.append("| File | Complexity | Loops | Risk |")
        lines.append("|------|-----------|-------|------|")
        for src, disasm in file_results.items():
            risk_pct = f"{disasm.risk_score:.0%}"
            lines.append(f"| `{src}` | {disasm.complexity_heuristic} | "
                         f"{len(disasm.infinite_loops)} | {risk_pct} |")
        lines.append("")

        if findings:
            lines.append("## Findings\n")
            for f in findings:
                icon = "🔴" if f.severity == Severity.CRITICAL else "🟡"
                lines.append(f"### {icon} {f.title}\n")
                lines.append(f"{f.explanation}\n")
                if f.recommendation:
                    lines.append(f"**Recommendation:** {f.recommendation}\n")
        else:
            lines.append("## Findings\n✅ No complexity or control-flow issues detected.\n")

        with open(report_path, "w") as f:
            f.write("\n".join(lines) + "\n")

    def explain(self, result: AgentResult) -> str:
        lines = [f"PR Complexity Review: {result.input_path}"]
        lines.append(f"Verdict: {result.safety_verdict}")
        lines.append(f"Worst complexity: {result.complexity_heuristic}")
        lines.append(f"Critical: {result.critical_count}, Warnings: {result.warning_count}")
        if result.findings:
            lines.append("\nKey findings:")
            for f in result.findings:
                lines.append(f"  - {f.title}")
        return "\n".join(lines)

    def format_as_pr_comment(self, result: AgentResult) -> str:
        """Format agent result as a GitHub PR comment."""
        lines = ["## 🔍 CompLexAI — PR Complexity Review\n"]

        verdict_icon = "✅" if result.safety_verdict == "PASS" else "❌"
        lines.append(f"**Verdict:** {verdict_icon} {result.safety_verdict}")
        lines.append(f"**Risk Score:** {result.risk_score:.2f}")
        lines.append(f"**Worst Complexity:** {result.complexity_heuristic}\n")

        if result.findings:
            lines.append("### Findings\n")
            for f in result.findings:
                icon = "🔴" if f.severity == Severity.CRITICAL else "🟡"
                lines.append(f"#### {icon} {f.title}\n")
                lines.append(f"{f.explanation}\n")
                if f.recommendation:
                    lines.append(f"> 💡 {f.recommendation}\n")
        else:
            lines.append("✅ No complexity or control-flow issues detected.\n")

        lines.append(f"\n<sub>Analysis completed in {result.duration_seconds:.1f}s by CompLexAI</sub>")
        return "\n".join(lines)

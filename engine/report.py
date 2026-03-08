"""
ReportGenerator — produce structured analysis reports from engine results.

Refactored from generate_report.py into a clean engine module that can work
both from DisassemblyResult objects and from raw log files.
"""

import os
import re
from typing import Optional

from engine.disassembler import DisassemblyResult


class ReportGenerator:
    """Generate Markdown analysis reports from DisassemblyResult or log files."""

    @staticmethod
    def from_result(result: DisassemblyResult, output_path: str,
                    gnn_complexity: Optional[str] = None) -> str:
        """Generate a Markdown report directly from a DisassemblyResult."""
        lines = []
        lines.append("# Firmware Analysis Report\n")
        lines.append(f"## Architecture\n- {result.architecture}\n")

        lines.append("## Firmware Safety Verification")
        lines.append(f"**Verdict: {result.safety_verdict}**\n")

        issues = []
        if result.infinite_loops:
            issues.append("Infinite loops detected")
        if result.unreachable_code:
            issues.append("Unreachable code (control flow bugs) detected")

        if issues:
            lines.append("Issues found:")
            for issue in issues:
                lines.append(f"- ⚠️ {issue}")
        else:
            lines.append("✅ No infinite loops or unreachable code detected. "
                         "Binary passes basic control-flow safety checks.")
        lines.append("")

        lines.append("## Risk Score")
        risk = result.risk_score
        risk_level = "LOW" if risk < 0.3 else "MEDIUM" if risk < 0.6 else "HIGH"
        lines.append(f"- **Score:** {risk:.2f} / 1.00 ({risk_level})")
        lines.append("")

        lines.append("## Algorithm Complexity (automatic estimate)")
        lines.append(f"- **Estimated complexity (heuristic):** "
                     f"`{result.complexity_heuristic}` (from CFG structure)")
        if gnn_complexity is not None:
            lines.append(f"- **Estimated complexity (GNN):** "
                         f"`{gnn_complexity}` (trained model)")
        lines.append("")

        lines.append("## Infinite Loop Detection")
        if result.infinite_loops:
            lines.append("⚠️ **Potential Infinite Loops Detected:**")
            for idx, loop in enumerate(result.infinite_loops, 1):
                loop_str = " → ".join(f"`0x{addr:x}`" for addr in loop)
                lines.append(f"- Loop {idx}: {loop_str}")
        else:
            lines.append("✅ **No Infinite Loops Detected**")
        lines.append("")

        lines.append("## Control Flow Bugs")
        if result.unreachable_code:
            lines.append("⚠️ **Unreachable code detected at addresses:**")
            for addr in result.unreachable_code[:20]:
                lines.append(f"- `0x{addr:x}`")
            if len(result.unreachable_code) > 20:
                lines.append(f"- ... and {len(result.unreachable_code) - 20} more")
        else:
            lines.append("✅ **No unreachable code detected.**")
        lines.append("")

        lines.append("## Printable Strings Extracted")
        if result.printable_strings:
            for addr, s in result.printable_strings[:50]:
                display = s if len(s) < 80 else s[:80] + "..."
                lines.append(f"- `{display}`")
            if len(result.printable_strings) > 50:
                lines.append(f"- ... and {len(result.printable_strings) - 50} more")
        else:
            lines.append("- No printable strings found.")
        lines.append("")

        lines.append("## Findings Summary")
        if result.findings:
            for finding in result.findings:
                icon = "🔴" if finding.severity == "critical" else "🟡" if finding.severity == "warning" else "🔵"
                lines.append(f"- {icon} **[{finding.severity.upper()}]** {finding.description}")
        else:
            lines.append("- ✅ No issues detected.")
        lines.append("")

        lines.append("## Recommendations")
        if result.infinite_loops or result.unreachable_code:
            lines.append("- ⚠️ **Review the code at the indicated addresses to resolve "
                         "infinite loops and/or unreachable code.**")
        else:
            lines.append("- ✅ **No immediate control-flow issues detected.**")

        report = "\n".join(lines) + "\n"
        with open(output_path, "w") as f:
            f.write(report)
        return report

    @staticmethod
    def from_log(log_path: str, output_path: str,
                 dot_path: Optional[str] = None) -> str:
        """Generate a report from a disassembly log file (backward-compatible)."""
        with open(log_path, 'r') as f:
            log_content = f.read()

        arch_match = re.search(r'\[INFO\] Architecture: (.+?)\.', log_content)
        architecture = arch_match.group(1).strip() if arch_match else 'Unknown'

        loops = re.findall(r'Loop\s+\d+:\s*(0x[0-9A-Fa-f]+)', log_content)
        unreachable = re.findall(r'Unreachable:\s*(0x[0-9A-Fa-f]+)', log_content)

        complexity_match = re.search(r'\[INFO\] Estimated complexity:\s*(.+)', log_content)
        complexity = complexity_match.group(1).strip() if complexity_match else 'Unknown'

        strings = re.findall(r'0x[0-9A-Fa-f]+:\s+\"(.+?)\"', log_content)

        safety_failures = []
        if loops:
            safety_failures.append("Infinite loops detected")
        if unreachable:
            safety_failures.append("Unreachable code detected")
        verdict = "FAIL" if safety_failures else "PASS"

        lines = []
        lines.append("# Firmware Analysis Report\n")
        lines.append(f"## Architecture\n- {architecture}\n")
        lines.append("## Firmware Safety Verification")
        lines.append(f"**Verdict: {verdict}**\n")

        if safety_failures:
            lines.append("Issues found:")
            for issue in safety_failures:
                lines.append(f"- ⚠️ {issue}")
        else:
            lines.append("✅ Binary passes basic control-flow safety checks.")
        lines.append("")

        lines.append(f"## Algorithm Complexity\n- **Estimated:** `{complexity}`\n")

        lines.append("## Infinite Loop Detection")
        if loops:
            for loop in loops:
                lines.append(f"- `{loop}`")
        else:
            lines.append("✅ No infinite loops detected.")
        lines.append("")

        lines.append("## Control Flow Bugs")
        if unreachable:
            for addr in unreachable:
                lines.append(f"- `{addr}`")
        else:
            lines.append("✅ No unreachable code detected.")
        lines.append("")

        report = "\n".join(lines) + "\n"
        with open(output_path, "w") as f:
            f.write(report)
        return report

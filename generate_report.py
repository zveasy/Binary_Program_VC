import re
import sys
import os

def generate_markdown_report(log_path, output_path, dot_path=None):
    with open(log_path, 'r') as log_file:
        log_content = log_file.read()

    architecture_match = re.search(r'\[INFO\] Architecture: (.+?)\.', log_content)
    architecture = architecture_match.group(1).strip() if architecture_match else 'Unknown'

    infinite_loops = re.findall(r'Loop\s+\d+:\s*(0x[0-9A-Fa-f]+)', log_content)
    if not infinite_loops:
        infinite_loops = re.findall(r'\[ALERT\] Potential infinite loops detected:\s*\n\s*Loop\s*\d+:\s*(0x[0-9A-Fa-f]+)', log_content)

    unreachable = re.findall(r'Unreachable:\s*(0x[0-9A-Fa-f]+)', log_content)

    complexity_match = re.search(r'\[INFO\] Estimated complexity:\s*(.+)', log_content)
    complexity_estimate = complexity_match.group(1).strip() if complexity_match else 'Unknown'

    # Optional: GNN prediction if model and cfg.dot exist
    gnn_complexity = None
    if dot_path is None:
        log_dir = os.path.dirname(os.path.abspath(log_path))
        dot_path = os.path.join(log_dir, "cfg.dot") if log_dir else "firmware/cfg.dot"
    _repo_root = os.path.dirname(os.path.abspath(__file__))
    _model_path = os.environ.get("GAT_MODEL_PATH", os.path.join(_repo_root, "gat_model.pt"))
    _label_map_path = os.environ.get("GAT_LABEL_MAP_PATH", os.path.join(_repo_root, "gat_label_map.json"))
    if os.path.isfile(dot_path) and os.path.isfile(_model_path) and os.path.isfile(_label_map_path):
        try:
            from predict_complexity import load_model_and_predict
            gnn_complexity = load_model_and_predict(dot_path, _model_path, _label_map_path)
        except Exception:
            pass

    printable_strings = re.findall(r'0x[0-9A-Fa-f]+:\s+\"(.+?)\"', log_content)

    # Firmware safety: FAIL if infinite loops or unreachable code detected
    safety_failures = []
    if infinite_loops:
        safety_failures.append("Infinite loops detected")
    if unreachable:
        safety_failures.append("Unreachable code (control flow bugs) detected")
    safety_verdict = "FAIL" if safety_failures else "PASS"

    with open(output_path, 'w') as report:
        report.write("# Firmware Analysis Report\n\n")
        report.write(f"## Architecture\n- {architecture}\n\n")

        report.write("## Firmware Safety Verification\n")
        report.write(f"**Verdict: {safety_verdict}**\n\n")
        if safety_failures:
            report.write("Issues found:\n")
            for f in safety_failures:
                report.write(f"- ⚠️ {f}\n")
        else:
            report.write("✅ No infinite loops or unreachable code detected. Binary passes basic control-flow safety checks.\n")
        report.write("\n")

        report.write("## Algorithm Complexity (automatic estimate)\n")
        report.write(f"- **Estimated complexity (heuristic):** `{complexity_estimate}` (from CFG structure)\n")
        if gnn_complexity is not None:
            report.write(f"- **Estimated complexity (GNN):** `{gnn_complexity}` (trained model)\n")
        report.write("\n")

        report.write("## Infinite Loop Detection\n")
        if infinite_loops:
            report.write("⚠️ **Potential Infinite Loops Detected at addresses:**\n")
            for loop in infinite_loops:
                report.write(f"- `{loop}`\n")
        else:
            report.write("✅ **No Infinite Loops Detected**\n")

        report.write("\n## Control Flow Bugs\n")
        if unreachable:
            report.write("⚠️ **Unreachable code detected at addresses:**\n")
            for addr in unreachable:
                report.write(f"- `{addr}`\n")
        else:
            report.write("✅ **No unreachable code detected.**\n")

        report.write("\n## Printable Strings Extracted\n")
        if printable_strings:
            for s in printable_strings:
                report.write(f"- `{s}`\n")
        else:
            report.write("- No printable strings found.\n")

        report.write("\n## Recommendations\n")
        if infinite_loops or unreachable:
            report.write("- ⚠️ **Review the code at the indicated addresses to resolve infinite loops and/or unreachable code.**\n")
        else:
            report.write("- ✅ **No immediate control-flow issues detected.**\n")

        # Optimization suggestions (e.g. "Grammarly for code" style hints)
        report.write("\n## Optimization suggestions\n")
        suggestions = []
        if complexity_estimate in ("O(n^2)", "O(n^2) or higher", "Unknown") or (gnn_complexity and "n2" in str(gnn_complexity).lower()):
            suggestions.append("**Higher complexity detected** — Consider optimizing nested loops, reducing redundant work, or using a more efficient algorithm (e.g. hash map for lookups).")
        for addr in infinite_loops[:5]:
            suggestions.append(f"**Infinite loop at {addr}** — Ensure the loop has a reachable exit condition or timeout; check for uninitialized or stuck flags.")
        for addr in unreachable[:5]:
            suggestions.append(f"**Unreachable code at {addr}** — Remove dead code or fix control flow so this path can be reached (or is intentionally unreachable).")
        if not suggestions:
            report.write("- No specific optimization hints for this binary.\n")
        else:
            for s in suggestions:
                report.write(f"- {s}\n")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 generate_report.py <log_path> <output_path> [dot_path]")
        sys.exit(1)
    dot_path = sys.argv[3] if len(sys.argv) > 3 else None
    generate_markdown_report(sys.argv[1], sys.argv[2], dot_path)
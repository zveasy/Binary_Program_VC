#!/usr/bin/env python3
"""
CompLexAI CLI — terminal interface for the analysis agents.

Layer 3: User experience layer.

Usage:
    python cli.py audit firmware/my_binary.bin
    python cli.py audit src/main.c                    # auto-compile + analyze
    python cli.py audit /path/to/repo                 # scan all source files
    python cli.py pr-review . --files src/parser.c    # PR complexity review
    python cli.py audit firmware/bin.bin --sarif out.sarif.json
    python cli.py audit firmware/bin.bin --json
    python cli.py audit firmware/bin.bin --patches
"""

import argparse
import json
import os
import sys

from agent.firmware_audit import FirmwareAuditAgent
from agent.pr_review import PRComplexityAgent
from agent.unified import UnifiedAuditAgent
from agent.patches import generate_sarif, suggest_patches


def cmd_audit(args):
    """Run the Unified Audit Agent (auto-detects binary, source, or repo)."""
    if not os.path.exists(args.input):
        print(f"Error: Path not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    agent = UnifiedAuditAgent(
        output_dir=args.output_dir,
        model_path=args.model,
        label_map_path=args.label_map,
    )

    print(f"CompLexAI Audit Agent")
    print(f"{'=' * 50}")
    print(f"Analyzing: {args.input}")
    print(f"Output directory: {args.output_dir}")
    print()

    result = agent.analyze(args.input)

    if args.sarif:
        sarif = generate_sarif(result, output_path=args.sarif)
        print(f"SARIF report saved to: {args.sarif}")

    if args.patches:
        patches = suggest_patches(result)
        if patches:
            print("\n--- Suggested Patches ---\n")
            for p in patches:
                print(f"Finding: {p['finding']}")
                print(f"  {p['description']}")
                print(f"  Before:\n    {p['before'].replace(chr(10), chr(10) + '    ')}")
                print(f"  After:\n    {p['after'].replace(chr(10), chr(10) + '    ')}")
                print()
        else:
            print("No patches to suggest.")

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print(result.summary)
        print(f"{'=' * 50}")
        if result.report_path:
            print(f"Report saved to: {result.report_path}")
        if result.dot_path:
            print(f"CFG saved to: {result.dot_path}")
        if result.log_path:
            print(f"Log saved to: {result.log_path}")

    return 0 if result.safety_verdict == "PASS" else 1


def cmd_pr_review(args):
    """Run the PR Complexity Review Agent."""
    repo_path = args.repo or "."
    if not os.path.isdir(repo_path):
        print(f"Error: Not a directory: {repo_path}", file=sys.stderr)
        sys.exit(1)

    agent = PRComplexityAgent(output_dir=args.output_dir)

    print(f"CompLexAI PR Complexity Review Agent")
    print(f"{'=' * 50}")
    print(f"Repository: {repo_path}")

    changed_files = args.files if args.files else None
    result = agent.analyze(repo_path, changed_files=changed_files)

    if args.sarif:
        generate_sarif(result, output_path=args.sarif)
        print(f"SARIF report saved to: {args.sarif}")

    if args.comment:
        comment = agent.format_as_pr_comment(result)
        print("\n--- PR Comment ---\n")
        print(comment)

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print(result.summary)
        print(f"{'=' * 50}")
        if result.report_path:
            print(f"Report saved to: {result.report_path}")

    return 0 if result.safety_verdict == "PASS" else 1


def main():
    parser = argparse.ArgumentParser(
        prog="complexai",
        description=(
            "CompLexAI — autonomous software reasoning agent "
            "powered by binary and graph analysis."
        ),
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # ── audit ──
    audit_parser = subparsers.add_parser(
        "audit",
        help="Audit a binary, source file, or repository"
    )
    audit_parser.add_argument("input", help="Path to binary, source file, or repo directory")
    audit_parser.add_argument("--output-dir", "-o", default="agent_output")
    audit_parser.add_argument("--model", "-m", default=None, help="Path to GAT model")
    audit_parser.add_argument("--label-map", "-l", default=None, help="Path to label map")
    audit_parser.add_argument("--json", "-j", action="store_true", help="Output JSON")
    audit_parser.add_argument("--sarif", default=None, help="Write SARIF report to path")
    audit_parser.add_argument("--patches", action="store_true", help="Show suggested patches")
    audit_parser.set_defaults(func=cmd_audit)

    # ── pr-review ──
    pr_parser = subparsers.add_parser(
        "pr-review",
        help="Review changed files for complexity regressions"
    )
    pr_parser.add_argument("repo", nargs="?", default=".", help="Repository path")
    pr_parser.add_argument("--files", nargs="+", help="Changed files to analyze")
    pr_parser.add_argument("--output-dir", "-o", default="agent_output")
    pr_parser.add_argument("--json", "-j", action="store_true", help="Output JSON")
    pr_parser.add_argument("--sarif", default=None, help="Write SARIF report to path")
    pr_parser.add_argument("--comment", action="store_true", help="Print as PR comment")
    pr_parser.set_defaults(func=cmd_pr_review)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(0)

    sys.exit(args.func(args))


if __name__ == "__main__":
    main()

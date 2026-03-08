#!/usr/bin/env python3
"""
CompLexAI CLI — terminal interface for the firmware audit agent.

Layer 3: User experience layer.

Usage:
    python cli.py audit firmware/my_binary.bin
    python cli.py audit firmware/my_binary.bin --output-dir results/
    python cli.py audit firmware/my_binary.bin --json
"""

import argparse
import json
import os
import sys

from agent.firmware_audit import FirmwareAuditAgent


def cmd_audit(args):
    """Run the Firmware Audit Agent on a binary."""
    if not os.path.isfile(args.input):
        print(f"Error: File not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    agent = FirmwareAuditAgent(
        output_dir=args.output_dir,
        model_path=args.model,
        label_map_path=args.label_map,
    )

    print(f"CompLexAI Firmware Audit Agent")
    print(f"{'=' * 50}")
    print(f"Analyzing: {args.input}")
    print(f"Output directory: {args.output_dir}")
    print()

    result = agent.analyze(args.input)

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print(result.summary)
        print(f"{'=' * 50}")
        print(f"Report saved to: {result.report_path}")
        print(f"CFG saved to: {result.dot_path}")
        print(f"Log saved to: {result.log_path}")

    return 0 if result.safety_verdict == "PASS" else 1


def main():
    parser = argparse.ArgumentParser(
        prog="complexai",
        description="CompLexAI — autonomous software reasoning agent powered by binary and graph analysis.",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # audit subcommand
    audit_parser = subparsers.add_parser(
        "audit",
        help="Run the Firmware Audit Agent on a binary"
    )
    audit_parser.add_argument(
        "input",
        help="Path to ELF/firmware binary to analyze"
    )
    audit_parser.add_argument(
        "--output-dir", "-o",
        default="agent_output",
        help="Directory for output files (default: agent_output/)"
    )
    audit_parser.add_argument(
        "--model", "-m",
        default=None,
        help="Path to trained GAT model (gat_model.pt)"
    )
    audit_parser.add_argument(
        "--label-map", "-l",
        default=None,
        help="Path to label map (gat_label_map.json)"
    )
    audit_parser.add_argument(
        "--json", "-j",
        action="store_true",
        help="Output results as JSON"
    )
    audit_parser.set_defaults(func=cmd_audit)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(0)

    sys.exit(args.func(args))


if __name__ == "__main__":
    main()

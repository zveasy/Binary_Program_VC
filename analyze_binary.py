#!/usr/bin/env python3
"""
Single entry point to analyze a firmware binary: disassemble, build CFG, generate report.

Usage:
  python analyze_binary.py path/to/firmware.bin
  python analyze_binary.py path/to/firmware.bin --report firmware/my_report.md

Output:
  - firmware/disassembly.log
  - firmware/cfg.dot, firmware/cfg.png (if graphviz available)
  - firmware/report.md (or --report path)
"""

import os
import sys
import argparse
import subprocess

_REPO_ROOT = os.path.dirname(os.path.abspath(__file__))


def main():
    parser = argparse.ArgumentParser(description="Analyze a firmware binary (disassemble, CFG, report).")
    parser.add_argument("binary", help="Path to ELF/binary")
    parser.add_argument("--report", "-r", default=None, help="Report output path (default: firmware/report.md)")
    parser.add_argument("--no-dot", action="store_true", help="Skip running graphviz dot to produce cfg.png")
    args = parser.parse_args()

    binary = args.binary
    if not os.path.isabs(binary):
        binary = os.path.join(_REPO_ROOT, binary)
    binary = os.path.abspath(binary)
    if not os.path.isfile(binary):
        print(f"Error: binary not found: {binary}", file=sys.stderr)
        sys.exit(1)

    firmware_dir = os.path.join(_REPO_ROOT, "firmware")
    os.makedirs(firmware_dir, exist_ok=True)
    log_path = os.path.join(firmware_dir, "disassembly.log")
    report_path = args.report or os.path.join(firmware_dir, "report.md")
    if not os.path.isabs(report_path):
        report_path = os.path.join(_REPO_ROOT, report_path)
    report_dir = os.path.dirname(report_path)
    if report_dir:
        os.makedirs(report_dir, exist_ok=True)
    cfg_dot = os.path.join(firmware_dir, "cfg.dot")
    cfg_png = os.path.join(firmware_dir, "cfg.png")

    rda = os.path.join(_REPO_ROOT, "rda_disassembler_enhanced.py")
    gen_report = os.path.join(_REPO_ROOT, "generate_report.py")
    if not os.path.isfile(rda) or not os.path.isfile(gen_report):
        print("Error: rda_disassembler_enhanced.py or generate_report.py not found.", file=sys.stderr)
        sys.exit(1)

    print("Running disassembler...")
    rc = subprocess.run([sys.executable, rda, binary], cwd=_REPO_ROOT)
    if rc.returncode != 0:
        print("Disassembler failed.", file=sys.stderr)
        sys.exit(rc.returncode)

    if not args.no_dot and os.path.isfile(cfg_dot):
        print("Generating CFG PNG...")
        subprocess.run(["dot", "-Tpng", cfg_dot, "-o", cfg_png], cwd=_REPO_ROOT)

    print("Generating report...")
    rc = subprocess.run([sys.executable, gen_report, log_path, report_path, cfg_dot], cwd=_REPO_ROOT)
    if rc.returncode != 0:
        print("Report generation failed.", file=sys.stderr)
        sys.exit(rc.returncode)

    print(f"Report written to {report_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

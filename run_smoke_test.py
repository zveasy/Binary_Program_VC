#!/usr/bin/env python3
"""
Smoke test: run generate_report and optionally prepare_gnn_sample without needing a real binary or angr.
Usage: python run_smoke_test.py
"""
import os
import sys

REPO = os.path.dirname(os.path.abspath(__file__))
os.chdir(REPO)

def test_report():
    log = os.path.join(REPO, "firmware", "test_smoke.log")
    report = os.path.join(REPO, "firmware", "smoke_report.md")
    dot = os.path.join(REPO, "firmware", "test_cfg.dot")
    if not os.path.isfile(log):
        print("Skip report test: firmware/test_smoke.log not found")
        return True
    sys.path.insert(0, REPO)
    from generate_report import generate_markdown_report
    generate_markdown_report(log, report, dot)
    if not os.path.isfile(report):
        print("FAIL: report not written")
        return False
    with open(report) as f:
        content = f.read()
    if "## Optimization suggestions" not in content:
        print("FAIL: Optimization suggestions section missing")
        return False
    if "Firmware Safety" not in content:
        print("FAIL: Firmware Safety section missing")
        return False
    print("OK: generate_report produced report with Optimization suggestions")
    return True

def test_prepare_gnn():
    dot = os.path.join(REPO, "firmware", "test_cfg.dot")
    if not os.path.isfile(dot):
        print("Skip GNN prep: firmware/test_cfg.dot not found")
        return True
    try:
        from convert_dot_to_pt import parse_dot_file, nx_to_pyg
        import torch
    except ImportError as e:
        print("Skip prepare_gnn (missing deps):", e)
        return True
    from prepare_gnn_sample import main as prep_main
    # Run with args
    sys.argv = ["prepare_gnn_sample.py", dot, "On", "-o", os.path.join(REPO, "firmware", "gnn_out")]
    try:
        prep_main()
    except SystemExit as e:
        if e.code != 0:
            print("FAIL: prepare_gnn_sample exited", e.code)
            return False
    out_dir = os.path.join(REPO, "firmware", "gnn_out")
    if not os.path.isdir(out_dir):
        out_dir = os.path.join(REPO, "joern_cfg_graphs")
    pt_files = [f for f in os.listdir(out_dir) if f.endswith(".pt")] if os.path.isdir(out_dir) else []
    if not pt_files and os.path.isdir(os.path.join(REPO, "joern_cfg_graphs")):
        pt_files = [f for f in os.listdir(os.path.join(REPO, "joern_cfg_graphs")) if f.endswith(".pt")]
    if pt_files:
        print("OK: prepare_gnn_sample produced .pt file(s)")
    else:
        print("OK: prepare_gnn_sample ran (no .pt in gnn_out; check GAT_DATA_DIR)")
    return True

if __name__ == "__main__":
    r1 = test_report()
    r2 = test_prepare_gnn()
    sys.exit(0 if (r1 and r2) else 1)

#!/usr/bin/env python3
"""
Predict algorithm complexity from a CFG .dot file (or from a binary by running the disassembler first).

Usage:
  python predict_complexity.py firmware/cfg.dot
  python predict_complexity.py --binary firmware/latest_firmware.bin

Requires a trained GAT model (gat_model.pt) and label map (gat_label_map.json) from train_gat_dataset.py.
"""

import os
import sys
import json
import argparse
import subprocess

import torch

# Reuse CFG parsing and PyG conversion from convert_dot_to_pt
from convert_dot_to_pt import parse_dot_file, nx_to_pyg

_REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
DEFAULT_MODEL_PATH = os.environ.get("GAT_MODEL_PATH", os.path.join(_REPO_ROOT, "gat_model.pt"))
DEFAULT_LABEL_MAP_PATH = os.environ.get("GAT_LABEL_MAP_PATH", os.path.join(_REPO_ROOT, "gat_label_map.json"))


def load_model_and_predict(dot_path: str, model_path: str, label_map_path: str) -> str:
    """Load a single .dot file, convert to PyG, run GAT, return predicted complexity label."""
    if not os.path.isfile(model_path):
        print(f"[ERROR] Model not found: {model_path}. Run train_gat_dataset.py first.", file=sys.stderr)
        sys.exit(1)
    if not os.path.isfile(label_map_path):
        print(f"[ERROR] Label map not found: {label_map_path}. Run train_gat_dataset.py first.", file=sys.stderr)
        sys.exit(1)

    checkpoint = torch.load(model_path, map_location="cpu")
    state_dict = checkpoint["state_dict"]
    in_dim = checkpoint["in_dim"]
    hidden_dim = checkpoint["hidden_dim"]
    out_dim = checkpoint["out_dim"]

    with open(label_map_path) as f:
        label_map = json.load(f)
    idx_to_label = {i: name for name, i in label_map.items()}

    from torch_geometric.data import Batch
    from gat_model import GAT

    model = GAT(in_dim=in_dim, hidden_dim=hidden_dim, out_dim=out_dim)
    model.load_state_dict(state_dict)
    model.eval()

    try:
        G = parse_dot_file(dot_path)
    except Exception as e:
        print(f"[ERROR] Failed to parse {dot_path}: {e}", file=sys.stderr)
        sys.exit(1)

    if G.number_of_nodes() == 0:
        print("[WARNING] Empty graph; cannot predict complexity.", file=sys.stderr)
        return "Unknown"

    data = nx_to_pyg(G)
    batch = Batch.from_data_list([data])

    with torch.no_grad():
        out = model(batch)
    logits = out.mean(dim=0, keepdim=True)
    pred_idx = int(logits.argmax(dim=1).item())
    label = idx_to_label.get(pred_idx, f"class_{pred_idx}")

    return label


def main():
    parser = argparse.ArgumentParser(description="Predict algorithm complexity from CFG .dot or binary.")
    parser.add_argument("input", nargs="?", help="Path to firmware/cfg.dot (or use --binary)")
    parser.add_argument("--binary", "-b", help="Path to ELF/binary; run disassembler first, then use firmware/cfg.dot")
    parser.add_argument("--model", "-m", default=DEFAULT_MODEL_PATH, help="Path to gat_model.pt")
    parser.add_argument("--label-map", "-l", default=DEFAULT_LABEL_MAP_PATH, help="Path to gat_label_map.json")
    parser.add_argument("--quiet", "-q", action="store_true", help="Print only the predicted label")
    args = parser.parse_args()

    dot_path = None
    if args.binary:
        if not os.path.isfile(args.binary):
            print(f"[ERROR] Binary not found: {args.binary}", file=sys.stderr)
            sys.exit(1)
        firmware_dir = os.path.join(_REPO_ROOT, "firmware")
        os.makedirs(firmware_dir, exist_ok=True)
        rda_script = os.path.join(_REPO_ROOT, "rda_disassembler_enhanced.py")
        if not os.path.isfile(rda_script):
            print(f"[ERROR] Disassembler not found: {rda_script}", file=sys.stderr)
            sys.exit(1)
        subprocess.run([sys.executable, rda_script, os.path.abspath(args.binary)], cwd=_REPO_ROOT, check=True)
        dot_path = os.path.join(firmware_dir, "cfg.dot")
    elif args.input:
        dot_path = os.path.abspath(args.input)
    else:
        dot_path = os.path.join(_REPO_ROOT, "firmware", "cfg.dot")
        if not os.path.isfile(dot_path):
            parser.error("Provide input (path to .dot), --binary <path>, or ensure firmware/cfg.dot exists")

    if not os.path.isfile(dot_path):
        print(f"[ERROR] DOT file not found: {dot_path}", file=sys.stderr)
        sys.exit(1)

    label = load_model_and_predict(dot_path, args.model, args.label_map)
    if args.quiet:
        print(label)
    else:
        print(f"[INFO] Predicted complexity (GNN): {label}")
    return label


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Prepare a single CFG .dot file for GNN training by converting it to PyG .pt format.

Usage:
  python prepare_gnn_sample.py firmware/cfg.dot O_n
  python prepare_gnn_sample.py path/to/cfg.dot On2 --out-dir joern_cfg_graphs

The output is saved to <out_dir>/<label>_<id>.pt. train_gat_dataset.py uses the first
underscore-segment of the filename as the label (e.g. "On_abc.pt" -> "On").
Use single-token labels: On (O(n)), On2 (O(n^2)), O1 (O(1)).
"""

import os
import sys
import argparse
import uuid

from convert_dot_to_pt import parse_dot_file, nx_to_pyg

_REPO_ROOT = os.path.dirname(os.path.abspath(__file__))


def main():
    parser = argparse.ArgumentParser(description="Convert a CFG .dot to .pt for GNN training.")
    parser.add_argument("dot_path", help="Path to .dot file (e.g. firmware/cfg.dot)")
    parser.add_argument("label", help="Complexity label (e.g. O_n, On2, O1). Use a single segment or train_gat_dataset will use first segment only.")
    parser.add_argument("--out-dir", "-o", default=None, help="Output directory (default: joern_cfg_graphs)")
    args = parser.parse_args()

    out_dir = args.out_dir or os.environ.get("GAT_DATA_DIR", os.path.join(_REPO_ROOT, "joern_cfg_graphs"))
    os.makedirs(out_dir, exist_ok=True)

    if not os.path.isfile(args.dot_path):
        print(f"[ERROR] File not found: {args.dot_path}", file=sys.stderr)
        sys.exit(1)

    try:
        G = parse_dot_file(args.dot_path)
    except Exception as e:
        print(f"[ERROR] Failed to parse {args.dot_path}: {e}", file=sys.stderr)
        sys.exit(1)

    if G.number_of_nodes() == 0:
        print("[ERROR] Empty graph.", file=sys.stderr)
        sys.exit(1)

    data = nx_to_pyg(G)
    short_id = str(uuid.uuid4())[:8]
    safe_label = args.label.replace(os.path.sep, "_").strip("_")
    out_name = f"{safe_label}_{short_id}.pt"
    out_path = os.path.join(out_dir, out_name)
    import torch
    torch.save(data, out_path)
    print(f"Saved {out_path} (nodes={G.number_of_nodes()}, edges={G.number_of_edges()}, label={safe_label})")


if __name__ == "__main__":
    main()

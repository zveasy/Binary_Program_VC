#!/usr/bin/env python3
import os
import shutil
import subprocess
import glob
import re
import time

import networkx as nx
import torch
from torch_geometric.data import Data
from tqdm import tqdm

# ---------------------------------------------------------------------
# Adjust these paths to match your setup
# ---------------------------------------------------------------------
JOERN_CFG_ROOT = "/Users/omnisceo/Desktop/spring_2025/Binary_Program_VC/joern_cfg_graphs"
PT_OUTPUT_DIR  = "/Users/omnisceo/Desktop/spring_2025/Binary_Program_VC/pt_cfg_files"

os.makedirs(PT_OUTPUT_DIR, exist_ok=True)

# ---------------------------------------------------------------------
def parse_dot_lines(lines):
    """
    A lenient parser for lines like:
      "12345" [label = < ... > ]
      "12345" -> "67890" [label=...]

    Steps:
     - Remove trailing semicolon
     - Strip bracketed "[ ... ]" text
     - If there's "->", treat as an edge
     - Otherwise treat as a node
     - Remove surrounding quotes from IDs
    """
    G = nx.DiGraph()
    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("//"):
            continue

        # Remove trailing semicolon if present
        if line.endswith(";"):
            line = line[:-1].strip()

        # Remove bracket segments [ ... ]
        line_no_label = re.sub(r'\[.*?\]', '', line).strip()

        if '->' in line_no_label:
            # Example: "146028888064" -> "128849018880"
            parts = line_no_label.split('->', 1)
            src = parts[0].strip()
            dst = parts[1].strip()

            # remove any surrounding quotes:
            src = src.strip('"')
            dst = dst.strip('"')

            if src and dst and src not in ("node","graph","edge") and dst not in ("node","graph","edge"):
                G.add_node(src)
                G.add_node(dst)
                G.add_edge(src, dst)
        else:
            # Possibly a node line: "146028888064"
            node_id = line_no_label.strip().strip('"')
            if node_id and node_id not in ("node","graph","edge"):
                G.add_node(node_id)

    return G


def unify_dot_files_in_folder(cfg2_path):
    """
    Combine all '*-cfg.dot' in 'cfg2/' into one big DiGraph.
    Returns None if no nodes/edges were successfully parsed.
    """
    dot_files = glob.glob(os.path.join(cfg2_path, "*-cfg.dot"))
    if not dot_files:
        return None

    big_G = nx.DiGraph()
    any_success = False

    for df in dot_files:
        try:
            with open(df, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
            subG = parse_dot_lines(lines)
            if subG.number_of_nodes() == 0 and subG.number_of_edges() == 0:
                continue
            any_success = True
            # merge into big_G
            big_G.add_nodes_from(subG.nodes())
            big_G.add_edges_from(subG.edges())
        except Exception as e:
            print(f"[WARNING] Could not parse {df}: {e}")
            continue

    if not any_success:
        return None
    return big_G


def nx_to_pyg(G: nx.DiGraph) -> Data:
    """
    Convert a NetworkX DiGraph to a PyTorch Geometric Data object,
      x = single float feature (out-degree)
      y = all zeros (dummy labels)
    """
    node_list = list(G.nodes)
    node_map = {nid: i for i, nid in enumerate(node_list)}

    edges = [(node_map[u], node_map[v]) for (u,v) in G.edges()]
    edge_index = torch.tensor(edges, dtype=torch.long).t().contiguous()

    x = torch.tensor([[G.out_degree(n)] for n in node_list], dtype=torch.float)
    y = torch.zeros(len(node_list), dtype=torch.long)  # dummy label

    return Data(x=x, edge_index=edge_index, y=y)


def main():
    start_time = time.time()

    subfolders = [d for d in os.listdir(JOERN_CFG_ROOT)
                  if os.path.isdir(os.path.join(JOERN_CFG_ROOT, d))]

    print(f"Found {len(subfolders)} subfolders in '{JOERN_CFG_ROOT}'.")
    print("Attempting to export CFG (if needed) and create .pt files...")

    # We'll use tqdm for a progress bar
    for folder in tqdm(subfolders, desc="Processing"):
        folder_path = os.path.join(JOERN_CFG_ROOT, folder)
        cpg_path    = os.path.join(folder_path, "cpg.bin.zip")
        if not os.path.isfile(cpg_path):
            continue

        # e.g. "O_n_s646259888" => complexity_label = "O_n"
        # you can tweak how we parse the label if needed
        complexity_label = folder.split("_s")[0]
        out_subdir = os.path.join(PT_OUTPUT_DIR, complexity_label)
        os.makedirs(out_subdir, exist_ok=True)

        pt_name = f"{folder}.pt"
        pt_path = os.path.join(out_subdir, pt_name)

        # skip if .pt already exists
        if os.path.exists(pt_path):
            # comment out if you want to redo them
            # tqdm already prints so let's just say pass or do a short message
            # print(f"[SKIP] {pt_name} already exists.")
            continue

        # Remove old cfg2/ if any
        cfg2_dir = os.path.join(folder_path, "cfg2")
        if os.path.isdir(cfg2_dir):
            shutil.rmtree(cfg2_dir)

        # 1) Export CFG to cfg2/
        try:
            subprocess.run([
                "joern-export",
                "--repr", "cfg",
                "--out", "cfg2",
                cpg_path
            ], cwd=folder_path, check=True)
        except subprocess.CalledProcessError as e:
            print(f"[WARNING] joern-export failed on {folder}: {e}")
            continue

        # 2) Parse .dot => big graph
        big_G = unify_dot_files_in_folder(cfg2_dir)
        if big_G is None or big_G.number_of_nodes() == 0:
            print(f"[SKIP] {folder}: no parseable .dot data.")
            continue

        # 3) Convert to PyG
        data = nx_to_pyg(big_G)
        torch.save(data, pt_path)
        print(f"[SAVED] {pt_path} ({big_G.number_of_nodes()} nodes, {big_G.number_of_edges()} edges)")

    elapsed = time.time() - start_time
    minutes = elapsed / 60.0
    print(f"\nDone! Took {elapsed:.1f} seconds ({minutes:.1f} minutes).")


if __name__ == "__main__":
    main()

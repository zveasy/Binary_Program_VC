import os
import subprocess
import json
import torch
from torch_geometric.data import Data
import networkx as nx
from tqdm import tqdm
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

DATA_ROOT = "/Users/omnisceo/Desktop/spring_2025/data_Set_Time"
OUTPUT_DIR = "joern_cfg_graphs"
os.makedirs(OUTPUT_DIR, exist_ok=True)

LABELS = sorted([f for f in os.listdir(DATA_ROOT) if os.path.isdir(os.path.join(DATA_ROOT, f))])
label_map = {label: i for i, label in enumerate(LABELS)}

JOERN_PARSE = "joern-parse"
JOERN_EXPORT = "joern-export"

def run_joern_extract(src_path, out_dir):
    out_cpg = os.path.join(out_dir, "cpg.bin.zip")
    subprocess.run([JOERN_PARSE, src_path, "--output", out_cpg], check=True)
    subprocess.run([JOERN_EXPORT, "--repr", "cfg", "--out", out_dir, out_cpg], check=True)

def build_pyg_from_cfg_json(cfg_json_path, label_id):
    with open(cfg_json_path) as f:
        data = json.load(f)

    G = nx.DiGraph()
    for node in data["nodes"]:
        G.add_node(node["id"], label=node.get("code", "unknown"))

    for edge in data["edges"]:
        if edge["label"] == "CFG":
            G.add_edge(edge["from"], edge["to"])

    node_list = list(G.nodes)
    node_map = {nid: i for i, nid in enumerate(node_list)}
    edge_index = torch.tensor([[node_map[e[0]], node_map[e[1]]] for e in G.edges], dtype=torch.long).t().contiguous()
    x = torch.tensor([[G.degree[n]] for n in node_list], dtype=torch.float)
    y = torch.full((x.size(0),), label_id, dtype=torch.long)

    return Data(x=x, edge_index=edge_index, y=y)

def process_file(label, filename):
    fpath = os.path.join(DATA_ROOT, label, filename)
    pt_output_path = os.path.join(OUTPUT_DIR, f"{label}_{filename}.pt")

    if os.path.exists(pt_output_path):
        return f"[SKIP] Already exists: {filename}"

    out_sub = os.path.join(OUTPUT_DIR, f"{label}_{filename.replace('.cpp','')}")
    os.makedirs(out_sub, exist_ok=True)

    try:
        run_joern_extract(fpath, out_sub)
        cfg_json = os.path.join(out_sub, "cfg/0.json")
        if os.path.exists(cfg_json):
            data = build_pyg_from_cfg_json(cfg_json, label_map[label])
            torch.save(data, pt_output_path)
            return f"[DONE] {filename}"
        else:
            return f"[MISSING CFG] {filename}"
    except subprocess.CalledProcessError as e:
        return f"[ERROR] {filename} - {e}"

if __name__ == "__main__":
    start_time = time.time()

    cpp_files = []
    for label in LABELS:
        label_path = os.path.join(DATA_ROOT, label)
        for filename in os.listdir(label_path):
            if filename.endswith(".cpp"):
                cpp_files.append((label, filename))

    total = len(cpp_files)
    print(f"Processing {total} C++ files...")

    with ProcessPoolExecutor() as executor:
        futures = [executor.submit(process_file, label, fname) for label, fname in cpp_files]
        for f in tqdm(as_completed(futures), total=total):
            print(f.result())

    elapsed = time.time() - start_time
    print(f"\n✅ Completed in {elapsed:.2f} seconds ({elapsed / 60:.2f} minutes)")

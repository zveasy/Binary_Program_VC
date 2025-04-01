import os
import torch
import pydot
import networkx as nx
from torch_geometric.data import Data
from tqdm import tqdm
import gc

JOERN_CFG_ROOT = "/Users/omnisceo/Desktop/spring_2025/Binary_Program_VC/joern_cfg_graphs"
PT_OUTPUT_DIR = "/Users/omnisceo/Desktop/spring_2025/Binary_Program_VC/ast_files"

def parse_dot_file(dot_path):
    try:
        graphs = pydot.graph_from_dot_file(dot_path)
        if not graphs:
            return None
        graph = graphs[0]
        nx_graph = nx.drawing.nx_pydot.from_pydot(graph)
        nx_graph = nx.DiGraph(nx_graph)
        mapping = {node: i for i, node in enumerate(nx_graph.nodes())}
        nx_graph = nx.relabel_nodes(nx_graph, mapping)
        edge_index = torch.tensor(list(nx_graph.edges)).t().contiguous()

        # AST Node Feature Extraction (simple binary features)
        node_features = []
        for node in nx_graph.nodes(data=True):
            label = node[1].get("label", "").lower()
            features = [
                int("if" in label),
                int("for" in label),
                int("while" in label),
                int("return" in label),
                int("call" in label)
            ]
            node_features.append(features)
        x = torch.tensor(node_features, dtype=torch.float)
        return Data(x=x, edge_index=edge_index)
    except Exception as e:
        print(f"[Error] {dot_path}: {e}")
        return None

def convert_all_ast_files():
    categories = [cat for cat in os.listdir(JOERN_CFG_ROOT) if os.path.isdir(os.path.join(JOERN_CFG_ROOT, cat))]
    for category in tqdm(categories, desc="Processing Categories"):
        category_path = os.path.join(JOERN_CFG_ROOT, category)
        output_dir = os.path.join(PT_OUTPUT_DIR, category)
        os.makedirs(output_dir, exist_ok=True)

        for sample_folder in os.listdir(category_path):
            cfg_folder = os.path.join(category_path, sample_folder, "cfg2")
            if not os.path.exists(cfg_folder): continue

            for dot_file in os.listdir(cfg_folder):
                if not dot_file.endswith(".dot"):
                    continue
                dot_path = os.path.join(cfg_folder, dot_file)
                pt_filename = f"{sample_folder}_{dot_file.replace('.dot', '')}.pt"
                pt_output = os.path.join(output_dir, pt_filename)

                if os.path.exists(pt_output): continue

                data = parse_dot_file(dot_path)
                if data:
                    torch.save(data, pt_output)
                    del data
                    gc.collect()

if __name__ == "__main__":
    convert_all_ast_files()

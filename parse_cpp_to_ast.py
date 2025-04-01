import os
import torch
from tqdm import tqdm
from tree_sitter import Parser
from tree_sitter_languages.languages import Cpp

# === CONFIG ===
INPUT_DIR = "/Users/omnisceo/Desktop/spring_2025/data_Set_Time"
OUTPUT_DIR = "/Users/omnisceo/Desktop/spring_2025/ast_files"

# === TREE-SITTER SETUP ===
parser = Parser()
parser.set_language(Cpp())

def parse_to_ast(file_path):
    try:
        with open(file_path, "rb") as f:
            code = f.read()
        tree = parser.parse(code)
        return tree.root_node.sexp().encode("utf-8")  # AST string
    except Exception as e:
        print(f"[!] Failed to parse {file_path}: {e}")
        return None

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

# === RECURSIVE PARSE ===
all_cpp_files = []
for root, dirs, files in os.walk(INPUT_DIR):
    for file in files:
        if file.endswith(".cpp"):
            full_path = os.path.join(root, file)
            all_cpp_files.append(full_path)

print(f"Total .cpp files found: {len(all_cpp_files)}")

for cpp_path in tqdm(all_cpp_files, desc="Parsing ASTs"):
    rel_path = os.path.relpath(cpp_path, INPUT_DIR)
    pt_path = os.path.join(OUTPUT_DIR, os.path.splitext(rel_path)[0] + ".pt")

    if os.path.exists(pt_path):
        continue  # skip already parsed

    ast_data = parse_to_ast(cpp_path)
    if ast_data:
        ensure_dir(os.path.dirname(pt_path))
        torch.save(ast_data, pt_path)

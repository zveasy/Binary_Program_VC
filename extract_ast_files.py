import os
import zipfile
import subprocess
from tqdm import tqdm

JOERN_BIN = "/Applications/joern/joern"  # Update if yours is different
JOERN_CFG_ROOT = "/Users/omnisceo/Desktop/spring_2025/Binary_Program_VC/joern_cfg_graphs"
AST_OUTPUT_DIR = "/Users/omnisceo/Desktop/spring_2025/Binary_Program_VC/ast_files"

os.makedirs(AST_OUTPUT_DIR, exist_ok=True)

folders = [os.path.join(JOERN_CFG_ROOT, d) for d in os.listdir(JOERN_CFG_ROOT) if os.path.isdir(os.path.join(JOERN_CFG_ROOT, d))]

for folder in tqdm(folders, desc="Extracting ASTs"):
    folder_name = os.path.basename(folder)
    ast_out_path = os.path.join(AST_OUTPUT_DIR, folder_name)

    # Skip if already extracted
    if os.path.exists(ast_out_path) and os.listdir(ast_out_path):
        continue

    os.makedirs(ast_out_path, exist_ok=True)

    zip_path = os.path.join(folder, "cpg.bin.zip")
    bin_path = os.path.join(folder, "cpg.bin")

    # ✅ Safely unzip if needed
    if os.path.isfile(zip_path) and not os.path.exists(bin_path):
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(folder)
        except zipfile.BadZipFile:
            print(f"⚠️ Skipping {folder_name} — BadZipFile.")
            continue

    if not os.path.exists(bin_path):
        print(f"⚠️ Skipping {folder_name} — No cpg.bin found.")
        continue

    # ✅ Extract ASTs via Joern
    try:
        subprocess.run([
            JOERN_BIN, "print", "--repr", "ast", "--out", ast_out_path, bin_path
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        print(f"❌ Joern failed on {folder_name}")

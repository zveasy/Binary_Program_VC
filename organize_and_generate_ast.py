#!/usr/bin/env python3

import os
import subprocess
from tqdm import tqdm

# ------------------------------------------------------------------------------
SOURCE_BASE_DIR = "/Users/omnisceo/Desktop/spring_2025/Binary_Program_VC/data_set_time/cpp_src"
OUTPUT_BASE_DIR = "/Users/omnisceo/Desktop/spring_2025/Binary_Program_VC/data_set_time_ast_json"
CLANG = "clang"  # Or "clang++", or full path like "/opt/homebrew/opt/llvm/bin/clang"
# ------------------------------------------------------------------------------


def generate_ast_json_for_cpp(source_file: str, output_file: str) -> bool:
    """
    Attempt to generate an AST JSON from a .cpp source file.
    Returns True if successful, False otherwise.
    """
    try:
        with open(output_file, "w") as f_out:
            subprocess.run(
                [
                    CLANG,
                    "-std=c++17",
                    "-ferror-limit=0",        # Don't stop after first error
                    "-Xclang", "-ast-dump=json",
                    "-fsyntax-only",
                    source_file
                ],
                stdout=f_out,
                stderr=subprocess.PIPE,
                check=True
            )
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n[✘] Failed to parse {source_file}")
        print(e.stderr.decode("utf-8"))
        return False


def collect_cpp_files(base_dir: str):
    """
    Recursively collect all .cpp files from base_dir.
    Returns a list of (source_path, relative_subdir, filename).
    """
    cpp_files = []
    for root, _, files in os.walk(base_dir):
        for file in files:
            if file.endswith(".cpp"):
                source_path = os.path.join(root, file)
                # relative_subdir is how we maintain the folder structure
                relative_subdir = os.path.relpath(root, base_dir)
                cpp_files.append((source_path, relative_subdir, file))
    return cpp_files


def main():
    cpp_files = collect_cpp_files(SOURCE_BASE_DIR)
    total = len(cpp_files)
    success = 0
    failed = 0
    skipped = 0

    print(f"🧠 Found {total} .cpp files. Starting AST JSON generation...\n")

    try:
        for source_path, relative_subdir, file in tqdm(cpp_files, desc="Processing", unit="file"):
            # Construct output path
            output_dir = os.path.join(OUTPUT_BASE_DIR, relative_subdir)
            os.makedirs(output_dir, exist_ok=True)

            base_name = os.path.splitext(file)[0]
            output_filename = f"{base_name}_ast.json"
            output_path = os.path.join(output_dir, output_filename)

            # If we've already parsed this file, skip it
            if os.path.exists(output_path):
                skipped += 1
                continue

            # Attempt to generate the AST
            if generate_ast_json_for_cpp(source_path, output_path):
                success += 1
            else:
                failed += 1

    except KeyboardInterrupt:
        print("\n⚠️  Interrupted by user.")

    print("\n📊 Summary:")
    print(f"  Total .cpp files         : {total}")
    print(f"  ✔ Successfully parsed    : {success}")
    print(f"  ✘ Failed to parse        : {failed}")
    print(f"  ⏭ Skipped (already done) : {skipped}")


if __name__ == "__main__":
    main()

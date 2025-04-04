#!/usr/bin/env python3

import os
import subprocess
import gzip
import shutil
from tqdm import tqdm

# ------------------------------------------------------------------------------
SOURCE_BASE_DIR = "/Users/omnisceo/Desktop/spring_2025/Binary_Program_VC/data_set_time/cpp_src"
OUTPUT_BASE_DIR = "/Users/omnisceo/Desktop/spring_2025/Binary_Program_VC/data_set_time_ast_json"
CLANG = "clang"  # or "clang++", or full path like "/opt/homebrew/opt/llvm/bin/clang"

# Log of successfully parsed files (relative paths)
SUCCESS_LOG_FILE = os.path.join(OUTPUT_BASE_DIR, "successful_parses.txt")
# ------------------------------------------------------------------------------

def load_successful_files(log_file: str):
    """
    Load a set of relative file paths that have been successfully parsed
    from a text file. One file path per line.
    """
    successful = set()
    if os.path.exists(log_file):
        with open(log_file, "r", encoding="utf-8") as f:
            for line in f:
                successful.add(line.strip())
    return successful


def save_successful_file(log_file: str, relative_path: str):
    """
    Append the newly successful file's relative path to the log file.
    """
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(relative_path + "\n")


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
                    "-ferror-limit=0",
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


def compress_json_file(input_path: str):
    """
    Compress the JSON file using gzip and delete the original.
    """
    output_path = input_path + ".gz"
    with open(input_path, 'rb') as f_in:
        with gzip.open(output_path, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)
    os.remove(input_path)
    return output_path


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
                relative_subdir = os.path.relpath(root, base_dir)
                cpp_files.append((source_path, relative_subdir, file))
    return cpp_files


def main():
    cpp_files = collect_cpp_files(SOURCE_BASE_DIR)
    total = len(cpp_files)

    successful_files = load_successful_files(SUCCESS_LOG_FILE)
    already_successful = len(successful_files)

    print(f"🧠 Found {total} .cpp files in total.\n")
    print(f"   Previously successful (from all runs so far): {already_successful}\n")
    print("Starting AST JSON generation...\n")

    this_run_success = 0
    this_run_failed = 0
    this_run_skipped = 0

    try:
        with tqdm(cpp_files, desc="Processing", unit="file") as pbar:
            for source_path, relative_subdir, filename in pbar:
                current_file = os.path.relpath(source_path, SOURCE_BASE_DIR)
                pbar.set_description(f"📄 {current_file}")

                rel_path_from_base = os.path.relpath(source_path, SOURCE_BASE_DIR)

                if rel_path_from_base in successful_files:
                    this_run_skipped += 1
                    continue

                output_dir = os.path.join(OUTPUT_BASE_DIR, relative_subdir)
                os.makedirs(output_dir, exist_ok=True)

                base_name = os.path.splitext(filename)[0]
                output_filename = f"{base_name}_ast.json"
                output_path = os.path.join(output_dir, output_filename)
                compressed_path = output_path + ".gz"

                if os.path.exists(compressed_path):
                    successful_files.add(rel_path_from_base)
                    this_run_skipped += 1
                    continue

                if generate_ast_json_for_cpp(source_path, output_path):
                    compress_json_file(output_path)
                    this_run_success += 1
                    successful_files.add(rel_path_from_base)
                    save_successful_file(SUCCESS_LOG_FILE, rel_path_from_base)
                else:
                    this_run_failed += 1

    except KeyboardInterrupt:
        print("\n⚠️  Interrupted by user.")

    final_success_count = len(successful_files)
    print("\n📊 Summary:")
    print(f"  Total .cpp files                : {total}")
    print(f"  Previously successful (all runs): {already_successful}")
    print(f"  ✔ Newly successful (this run)   : {this_run_success}")
    print(f"  ✘ Failed (this run)             : {this_run_failed}")
    print(f"  ⏭ Skipped (this run)            : {this_run_skipped}")
    print(f"  ✅ Overall success (all runs)    : {final_success_count}")
    print(f"\n📝 Success log file: {SUCCESS_LOG_FILE}")


if __name__ == "__main__":
    main()

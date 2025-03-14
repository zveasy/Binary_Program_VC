# Firmware Analysis Pipeline

## Overview
This repository implements a continuous integration (CI) pipeline that automatically compiles, analyzes, and verifies binary firmware files for potential issues, such as infinite loops.

## Workflow Description
The pipeline performs the following key steps:

1. **Checkout and Setup:**
   - Checks out the repository from GitHub.
   - Sets up Python (version 3.9).

2. **Dependencies Installation:**
   - Installs required Python packages (`angr`, `pydot`, and others specified in `requirements.txt`).
   - Installs `graphviz` to enable graphical representation of CFG.

3. **Firmware Compilation and Analysis:**
   - Compiles two test firmware binaries (`hello_world_test.bin` and `infinite_loop_test.bin`).
   - Analyzes these firmware binaries for control flow graph (CFG) generation and infinite loop detection.

## How Infinite Loop Detection Works

The Python script (`rda_disassembler_enhanced.py`) performs the following steps:

- Parses ELF files to identify their architecture.
- Uses Capstone and angr libraries to disassemble executable sections.
- Builds a Control Flow Graph (CFG) representing code execution paths.
- Analyzes the CFG to detect potential infinite loops, identified by loops in the graph structure where an instruction repeatedly jumps back to itself or creates a cyclic execution path.

### Example Test Files
- **`infinite_loop_test.bin`**: Contains an intentional infinite loop (`while (1) {}`) to validate the loop detection algorithm.
- **`hello_world_test.bin`**: Simple executable without loops used as a control to validate no false-positive detections.

## GitHub Actions Workflow

Your GitHub Actions workflow (`firmware_analysis.yml`) executes these tests automatically on every push. The key workflow steps include:

- **Firmware Analysis (Infinite Loop Test)**:
  - Detects infinite loops by analyzing the firmware binary.
  - The job fails if an infinite loop is detected (expected behavior).

- **Firmware Analysis (Hello World Test)**:
  - Ensures no false infinite loop detection occurs.

- The workflow outputs and uploads:
  - Disassembly logs (`firmware/disassembly.log`).
  - CFG graphs as PNG files for visual analysis.

## Verification Steps

### Visual and Functional Verification

After each push, perform:

1. **Visual Inspection**:
   - Download the generated CFG images.
   - Verify the accuracy and clarity of CFGs visually.

### Functional Verification:
- Check the disassembly log (`firmware/disassembly.log`) for explicit infinite loop alerts:
  - Infinite loop detected example:
    ```
    [ALERT] Potential infinite loops detected:
      Loop 1: 0x1131
    ```
  - No loop detection:
    ```
    [INFO] No infinite loops detected.
    ```

## Sample Results

- **Infinite loop file**:
  - ✅ **Infinite loop correctly detected.**

- **Hello World file**:
  - ✅ No infinite loops detected (expected).

## Usage Instructions

1. Add new firmware binaries to the `firmware` directory.
2. Push changes to trigger the GitHub Actions workflow.
3. Review artifacts and log outputs on the GitHub Actions page to verify the firmware.

## Troubleshooting

- Ensure ELF binaries exist in the specified paths.
- Ensure all dependencies (`angr`, `pydot`, `graphviz`) are correctly installed.
- Check GitHub Actions logs for detailed error information if the pipeline fails.

---



# Firmware Analysis Pipeline

## Overview
- Purpose of the pipeline
- Technologies used (Angr, NetworkX, Graphviz, etc.)

## Analysis Steps
1. Architecture detection (x86_64, AArch64, etc.)
2. Linear disassembly of executable sections
3. CFG (Control Flow Graph) generation
4. Detection of infinite loops
5. Extraction of printable strings

## How Infinite Loop Detection Works
- Explanation of CFG analysis
- Criteria used for detecting loops

## Analyzing Reports
- Instructions to access and interpret the generated Markdown reports (`firmware/report.md`).

## GitHub Actions Automation
- How the workflow file (`firmware_analysis.yml`) automates this process.

## Usage
- Steps to trigger and verify firmware analysis with new binaries.

**Maintained by:** Zakariya Veasy 
**Last Updated:** March 2025


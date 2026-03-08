# CompLexAI / Binary Program Analysis Pipeline

**Automated reasoning about program behavior — from binaries to CFGs to AI.**

READ This please!

---

## Vision: What This System Is Really For

This repo is more than infinite-loop detection. It’s a **binary → CFG → analysis → (optionally) GNN** pipeline toward:

- **Software verification at scale** — Answer “Does the *structure* of this program make sense?” without manual review.
- **Binary trust verification** — Analyze vendor/closed-source firmware when source isn’t available.
- **CI safety layer** — Run CFG and complexity checks before runtime tests.
- **Algorithm complexity detection** — Infer O(1), O(n), O(n²), etc. from binary structure (GNN on CFGs).
- **Long-term** — “Grammarly for code”: AI that suggests complexity and correctness improvements before ship.

**Current pipeline:**

```
Binaries → Disassembly → CFG → Analysis (loops, complexity, anomalies) → [GNN for algorithm reasoning]
```

**Key capabilities:**

- **Detect algorithm complexity automatically** — Infer complexity classes (e.g. O(n), O(n²)) from CFG structure via GNN models.
- **Detect infinite loops and control flow bugs** — Identify cycles with no exit and other structural issues in the control flow graph.
- **Verify firmware safety from binaries** — Analyze ELF firmware without source code; report loops, strings, and CFG structure for audit and CI.

**This is not an AI agent.** It’s **program analysis AI** — an auditor/analyzer that reasons about control flow, complexity, and binary structure instead of executing tasks. See [AI Agent vs. Program Analysis AI](docs/AI_AGENT_VS_PROGRAM_ANALYSIS.md) for the full distinction and product identity.

**Core product question:** Which single problem does this system solve better than anything else? Right now: (1) detect algorithm complexity automatically, (2) detect infinite loops and control flow bugs, (3) verify firmware safety from binaries. One of these can become the core product.

---

## Overview (Current Features)

This repository implements a **continuous integration (CI) pipeline** that automatically compiles, analyzes, and verifies binary firmware for:

- **Control flow graph (CFG)** generation  
- **Infinite loop** detection  
- **Printable string** extraction  
- **Optional:** Graph Neural Network (GNN) models for complexity/algorithm classification on CFGs  

Technologies: **Capstone**, **angr**, **NetworkX**, **Graphviz**, **PyTorch Geometric** (GCN/GAT).

### Pipeline components (this repo)

| Stage | Script / component | Purpose |
|-------|--------------------|--------|
| Binary → CFG | `rda_disassembler_enhanced.py` | Disassembly, CFG build, infinite-loop detection, strings |
| Log → report | `generate_report.py` | Markdown report from disassembly log |
| CI | `.github/workflows/firmware_analysis.yml` | Build test binaries, run analysis, assert loop detection |
| IDE | `FAT/` (VS Code extension) | Auto-analyze `firmware/latest_firmware.bin`, show CFG in webview |
| Source CFG | `joern_source_cfg_extractor.py` | Extract CFGs from source (Joern) |
| CFG → ML | `convert_dot_to_pt.py`, `cfg2_to_pt.py` | Convert CFG (e.g. .dot) to PyTorch Geometric format |
| Complexity GNN | `complexity_gnn.py`, `gnn_complexity_model_tf.py` | GCN/GNN models for complexity |
| Train on CFGs | `train_gat_dataset.py` | GAT training on labeled CFG graphs (e.g. O(n), O(n²)) |
| GNN inference | `predict_complexity.py` | Predict complexity class from `firmware/cfg.dot` (or binary) using saved GAT model |

**Dependencies:** Core pipeline uses `pip install -r requirements.txt`. For GNN training and inference (e.g. `train_gat_dataset.py`, `predict_complexity.py`), install additionally: `pip install -r requirements-gnn.txt` (adds `torch`, `torch-geometric`).

## Workflow Description (CI)
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
- For GNN scripts: install `pip install -r requirements-gnn.txt`; ensure `joern_cfg_graphs` (or `GAT_DATA_DIR`) contains `.pt` graphs for training.

## Roadmap / What's still optional

- **GNN inference:** Run `train_gat_dataset.py` to produce `gat_model.pt` and `gat_label_map.json`; then `predict_complexity.py firmware/cfg.dot` or `--binary <path>` to get GNN complexity. Reports automatically include GNN complexity when the model is present.
- **Configurable paths:** `convert_dot_to_pt.py`, `cfg2_to_pt.py`, and `joern_source_cfg_extractor.py` use env vars (`JOERN_CFG_ROOT`, `PT_OUTPUT_DIR`, `JOERN_DATA_ROOT`, etc.) with repo-relative defaults.
- **FAT extension:** Optional improvements: handle missing `latest_firmware.bin`, add "Analyze selected binary" command, show report in webview.

---

**Maintained by:** Zakariya Veasy  
**Last updated:** April 2025



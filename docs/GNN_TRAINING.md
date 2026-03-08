# GNN Training: Producing Labeled CFG Data

The GAT model in `train_gat_dataset.py` expects **PyTorch Geometric `.pt` files** in a directory (default: `joern_cfg_graphs`). Each file should be named so the **first underscore-segment** is the complexity label, e.g. `On_abc123.pt` → label `On`, `On2_def456.pt` → label `On2`.

## Label convention

Use **single-token labels** so `filename.split("_")[0]` is the full class:

| Label | Meaning   |
|-------|-----------|
| `O1`  | O(1)      |
| `On`  | O(n)      |
| `On2` | O(n²)     |

## Option 1: From this repo’s firmware CFG

After running the disassembler you get `firmware/cfg.dot`. Convert it to a training sample with a chosen label:

```bash
pip install -r requirements-gnn.txt
python prepare_gnn_sample.py firmware/cfg.dot On --out-dir joern_cfg_graphs
```

Repeat for many binaries (and labels) to build a dataset.

## Option 2: From Joern (source → CFG → .pt)

1. Install [Joern](https://joern.io/).
2. For each source file (or folder) with a known complexity label:
   - Run `joern-parse` and `joern-export --repr cfg` to get `.dot` files.
   - Use `convert_dot_to_pt.py` or `cfg2_to_pt.py` with `JOERN_CFG_ROOT` pointing at the Joern output; they write `.pt` files under `PT_OUTPUT_DIR`.
   - Ensure filenames (or folder names) start with the label, e.g. `On_something.pt`, so `train_gat_dataset`’s `split("_")[0]` gives the right class.
3. Set `GAT_DATA_DIR` to the directory containing these `.pt` files (or copy them into `joern_cfg_graphs`).

## Option 3: Minimal test set

Create a few samples by hand for a quick training test:

```bash
# After analyzing a binary, e.g. hello_world_test.bin
python rda_disassembler_enhanced.py firmware/hello_world_test.bin
python prepare_gnn_sample.py firmware/cfg.dot On -o joern_cfg_graphs
# Repeat for other binaries/labels, then:
python train_gat_dataset.py
```

## Training and inference

- **Training:** `python train_gat_dataset.py` (uses `GAT_DATA_DIR`, writes `gat_model.pt` and `gat_label_map.json`).
- **Inference:** `python predict_complexity.py firmware/cfg.dot` or `python predict_complexity.py --binary path/to/binary`.
- Reports from `generate_report.py` will include GNN complexity when the model and label map exist.

## Optional: TensorFlow/Spektral path

`gnn_complexity_model_tf.py` trains a GCN on token-based graphs from **Project_CodeNet**. Set `CODENET_DATASET_PATH` to the Project_CodeNet root. This path is separate from the GAT CFG pipeline and saves `complexity_gnn_tf.h5`.

# AGENTS.md

## Cursor Cloud specific instructions

### Project overview

CompLexAI is a binary program analysis pipeline: Binary → Disassembly → CFG → Analysis → (optionally) GNN complexity classification. See `README.md` for full details.

### Services

| Service | How to start | Port |
|---|---|---|
| FastAPI API | `source .venv/bin/activate && uvicorn api:app --host 0.0.0.0 --port 8000` | 8000 |

### Development environment

- **Python 3.9** is required (`angr` is incompatible with Python 3.12). A virtualenv at `.venv` is created with `python3.9 -m venv .venv`.
- Always activate the venv before running Python scripts: `source .venv/bin/activate`
- System packages required: `graphviz`, `libcapstone-dev`, `gcc`, `build-essential` (installed via `apt`).
- The API's `/analyze` endpoint writes to `/app/` (Docker path); in local dev, create it: `sudo mkdir -p /app && sudo chown $USER /app`.

### Running the pipeline

- Compile test binaries: `gcc hello_world.c -o firmware/hello_world_test.bin && gcc infinite_loop.c -o firmware/infinite_loop_test.bin`
- Analyze a binary: `python rda_disassembler_enhanced.py firmware/<binary>.bin`
- Generate report: `python generate_report.py firmware/disassembly.log firmware/report.md firmware/cfg.dot`
- Convert CFG to image: `dot -Tpng firmware/cfg.dot -o firmware/cfg.png`

### Lint / Build / Test

- **Lint (FAT extension):** `cd FAT && npm run lint`
- **Build (FAT extension):** `cd FAT && npm run compile`
- **Test script:** `bash test_loop_detection.sh` (compiles test binaries and validates loop detection)

### GNN (optional)

GNN training/inference requires `pip install -r requirements-gnn.txt` (PyTorch + PyTorch Geometric). This is not needed for the core pipeline.

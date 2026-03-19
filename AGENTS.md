# AGENTS.md

## Cursor Cloud specific instructions

### Project overview

CompLexAI is an autonomous software reasoning agent powered by binary and graph analysis. Architecture:

- **Layer 1 — Analysis Engine** (`engine/`): Disassembly, CFG, loop detection, complexity estimation, report generation.
- **Layer 2 — Agent Orchestration** (`agent/`): `FirmwareAuditAgent` that autonomously analyzes binaries and produces findings with plain-English explanations.
- **Layer 3 — User Experience**: CLI (`cli.py`), FastAPI API (`api.py`), VS Code extension (`FAT/`).

See `README.md` for full details.

### Services

| Service | How to start | Port |
|---|---|---|
| FastAPI API | `source .venv/bin/activate && uvicorn api:app --host 0.0.0.0 --port 8000` | 8000 |

### Production API (config and health)

- **Health:** `GET /health` (liveness), `GET /ready` (readiness).
- **Config (env):** `COMPLEXAI_MAX_UPLOAD_MB` (default 50), `COMPLEXAI_LOG_LEVEL`, `COMPLEXAI_FIRMWARE_DIR`, `COMPLEXAI_AUTO_SAVE_DIR`, `COMPLEXAI_AGENT_OUTPUT_DIR`, `COMPLEXAI_RATE_LIMIT` (e.g. `30/minute`), `COMPLEXAI_API_KEY` (optional; if set, requests must include `X-API-Key` header).
- **Uploads:** Only ELF binaries accepted; filename is sanitized; max size enforced.

### Development environment

- **Python 3.9** is required (`angr` is incompatible with Python 3.12). A virtualenv at `.venv` is created with `python3.9 -m venv .venv`.
- Always activate the venv before running Python scripts: `source .venv/bin/activate`
- System packages required: `graphviz`, `libcapstone-dev`, `gcc`, `build-essential` (installed via `apt`).
- The API's `/analyze` endpoint writes to `/app/` (Docker path); in local dev, create it: `sudo mkdir -p /app && sudo chown $USER /app`.

### Running the agent

- **CLI audit:** `python cli.py audit firmware/<binary>.bin` (full agent pipeline)
- **CLI JSON output:** `python cli.py audit firmware/<binary>.bin --json`
- **API agent endpoint:** `POST /agent/audit` with file upload
- **API audit report:** `GET /agent/audit/report`

### Running the engine directly (lower-level)

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

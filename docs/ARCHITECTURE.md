# CompLexAI Architecture

**An autonomous software reasoning agent powered by binary and graph analysis.**

## Three-Layer Architecture

```
┌─────────────────────────────────────────────────────────┐
│                 Layer 3: User Experience                  │
│                                                          │
│   CLI (cli.py)  │  FastAPI (api.py)  │  VS Code (FAT/)  │
└────────┬────────┴─────────┬──────────┴────────┬─────────┘
         │                  │                   │
┌────────▼──────────────────▼───────────────────▼─────────┐
│                Layer 2: Agent Orchestration               │
│                                                          │
│  FirmwareAuditAgent  │  PRComplexityAgent  │  Unified   │
│  Patches / SARIF     │  PR Comment Format  │  Dispatch  │
└────────┬─────────────┴─────────┬────────────┴───────────┘
         │                       │
┌────────▼───────────────────────▼────────────────────────┐
│                 Layer 1: Analysis Engine                  │
│                                                          │
│  DisassemblerEngine  │  ReportGenerator  │  Predictor   │
│  DotParser           │  GraphConverter   │  GAT / GCN   │
└─────────────────────────────────────────────────────────┘
         │
    ┌────▼────┐
    │ Binary  │  ← ELF firmware, compiled C/C++, etc.
    └─────────┘
```

## Layer 1 — Analysis Engine (`engine/`)

The engine is the moat. It provides deterministic, programmatic analysis:

| Module | Purpose |
|--------|---------|
| `engine/disassembler.py` | Disassembly, CFG construction, loop detection, complexity estimation |
| `engine/report.py` | Markdown report generation from analysis results |
| `engine/graph_conversion.py` | DOT parsing and NetworkX ↔ PyTorch Geometric conversion |
| `engine/predictor.py` | GNN-based complexity prediction using trained GAT model |
| `engine/models/gat.py` | Graph Attention Network model definition |
| `engine/models/gnn.py` | Graph Convolutional Network model definition |

### Key Data Types

- `DisassemblyResult` — complete analysis output (CFG, loops, complexity, strings, risk score)
- `Finding` — individual analysis finding with category, severity, addresses

## Layer 2 — Agent Orchestration (`agent/`)

Agents orchestrate the engine and interpret results:

| Agent | Purpose |
|-------|---------|
| `FirmwareAuditAgent` | Autonomous firmware binary audit with findings, explanations, recommendations |
| `PRComplexityAgent` | PR review — analyzes changed files for complexity regressions |
| `UnifiedAuditAgent` | Auto-detects input type (binary/source/repo) and dispatches |

### Supporting Modules

| Module | Purpose |
|--------|---------|
| `agent/base.py` | Base classes: `AnalysisAgent`, `AgentResult`, `AgentFinding` |
| `agent/patches.py` | SARIF report generation and code fix suggestions |

### Key Data Types

- `AgentResult` — structured agent output (findings, risk score, summary, report path)
- `AgentFinding` — finding with plain-English explanation and recommendation
- `Severity` — CRITICAL / WARNING / INFO
- `FindingCategory` — INFINITE_LOOP / UNREACHABLE_CODE / HIGH_COMPLEXITY / etc.

## Layer 3 — User Experience

### CLI (`cli.py`)

```bash
complexai audit firmware/my_binary.bin           # auto-detect input
complexai audit src/main.c                       # compile + analyze
complexai audit /path/to/repo                    # scan directory
complexai pr-review . --files src/parser.c       # PR review
complexai audit binary.bin --sarif out.sarif     # SARIF output
complexai audit binary.bin --patches             # show fix suggestions
```

### FastAPI (`api.py`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Health check + version |
| `/analyze` | POST | Engine-level disassembly (upload binary) |
| `/download` | GET | Download disassembly log |
| `/agent/audit` | POST | Full agent audit (upload binary) |
| `/agent/audit/report` | GET | Download latest audit report |

### VS Code Extension (`FAT/`)

The Firmware Analysis Tool extension runs `cli.py audit` on binaries and displays CFG + report in VS Code panels.

## Data Flow

```
Input (binary/source/repo)
    │
    ▼
UnifiedAuditAgent.analyze()
    │
    ├── Binary? → FirmwareAuditAgent
    ├── Source? → gcc compile → FirmwareAuditAgent
    └── Repo?  → PRComplexityAgent
            │
            ▼
    DisassemblerEngine.analyze()
        │
        ├── ELF parsing (pyelftools)
        ├── Disassembly (Capstone)
        ├── CFG construction (NetworkX)
        ├── Infinite loop detection
        ├── Unreachable code detection
        ├── Complexity estimation
        └── Optional: GNN prediction
            │
            ▼
    AgentResult
        │
        ├── findings[]  (with explanations + recommendations)
        ├── risk_score
        ├── safety_verdict
        ├── audit_report.md
        ├── cfg.dot
        └── disassembly.log
```

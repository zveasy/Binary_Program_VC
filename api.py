import os
import shutil
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import FileResponse, JSONResponse

from engine.disassembler import DisassemblerEngine
from agent.firmware_audit import FirmwareAuditAgent

FIRMWARE_DIR = "firmware"
os.makedirs(FIRMWARE_DIR, exist_ok=True)

app = FastAPI(
    title="CompLexAI",
    description="Autonomous software reasoning agent powered by binary and graph analysis.",
    version="0.3.0",
)

# --------------------------------------------------------------------------
# Core endpoints (uses engine directly)
# --------------------------------------------------------------------------

@app.get("/")
async def root():
    return {"message": "CompLexAI API is working!", "version": "0.3.0"}

@app.post("/analyze")
async def analyze_firmware(file: UploadFile = File(...)):
    """Disassemble and analyze an uploaded firmware binary using the engine."""
    file_location = os.path.join(FIRMWARE_DIR, file.filename)
    with open(file_location, "wb") as f:
        f.write(file.file.read())

    engine = DisassemblerEngine(output_dir=FIRMWARE_DIR)
    result = engine.analyze(file_location)

    AUTO_SAVE_DIR = "/app"
    os.makedirs(AUTO_SAVE_DIR, exist_ok=True)
    if result.log_path:
        shutil.copy(result.log_path, os.path.join(AUTO_SAVE_DIR, "disassembly_output.log"))

    return {
        "status": result.safety_verdict,
        "message": "Disassembly complete!",
        "architecture": result.architecture,
        "complexity": result.complexity_heuristic,
        "infinite_loops": len(result.infinite_loops),
        "risk_score": round(result.risk_score, 3),
        "log_saved_to": result.log_path,
    }

@app.get("/download")
async def download_disassembly():
    return FileResponse("firmware/disassembly.log", filename="disassembly.log")

# --------------------------------------------------------------------------
# Agent endpoints (new — Layer 3 API)
# --------------------------------------------------------------------------

@app.post("/agent/audit")
async def agent_audit(file: UploadFile = File(...)):
    """
    Run the Firmware Audit Agent on an uploaded binary.

    The agent will:
    1. Disassemble the binary and build a CFG
    2. Detect infinite loops and control-flow bugs
    3. Estimate algorithm complexity
    4. Rank findings by severity
    5. Explain findings in plain English
    6. Return a structured audit result with recommendations
    """
    file_location = os.path.join(FIRMWARE_DIR, file.filename)
    with open(file_location, "wb") as f:
        f.write(file.file.read())

    agent = FirmwareAuditAgent(output_dir="agent_output")
    result = agent.analyze(file_location)

    return JSONResponse(content=result.to_dict())

@app.get("/agent/audit/report")
async def agent_audit_report():
    """Download the latest audit report as Markdown."""
    report_path = "agent_output/audit_report.md"
    if not os.path.isfile(report_path):
        return JSONResponse(
            status_code=404,
            content={"error": "No audit report found. Run /agent/audit first."}
        )
    return FileResponse(report_path, filename="audit_report.md")

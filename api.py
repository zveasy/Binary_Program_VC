import os
import sys
import shutil
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import FileResponse, JSONResponse
import subprocess

from agent.firmware_audit import FirmwareAuditAgent

# Ensure the firmware directory exists
FIRMWARE_DIR = "firmware"
os.makedirs(FIRMWARE_DIR, exist_ok=True)

app = FastAPI(
    title="CompLexAI",
    description="Autonomous software reasoning agent powered by binary and graph analysis.",
    version="0.2.0",
)

# --------------------------------------------------------------------------
# Original endpoints (backward-compatible)
# --------------------------------------------------------------------------

@app.get("/")
async def root():
    return {"message": "CompLexAI API is working!", "version": "0.2.0"}

@app.post("/analyze")
async def analyze_firmware(file: UploadFile = File(...)):
    # Save the uploaded file
    file_location = os.path.join(FIRMWARE_DIR, file.filename)
    with open(file_location, "wb") as f:
        f.write(file.file.read())

    # Run the disassembler
    result = subprocess.run(
        [sys.executable, "rda_disassembler_enhanced.py", file_location], 
        capture_output=True, text=True
    )

    # Save output to a log file inside the container
    DISASSEMBLY_LOG = os.path.join(FIRMWARE_DIR, "disassembly.log")

    # Write disassembly results to the log file
    with open(DISASSEMBLY_LOG, "w") as log_file:
        log_file.write("=== Disassembly Results ===\n")
        log_file.write(result.stdout if result.stdout else "No output from disassembler.\n")

    # **Change Auto-Save Directory to `Binary_Program_VC`**
    AUTO_SAVE_DIR = "/app"
    os.makedirs(AUTO_SAVE_DIR, exist_ok=True)

    # Define the auto-save log file path
    AUTO_SAVE_PATH = os.path.join(AUTO_SAVE_DIR, "disassembly_output.log")

    # Save the disassembly output to the correct location
    shutil.copy(DISASSEMBLY_LOG, AUTO_SAVE_PATH)

    return {"status": "PASS", "message": "Disassembly complete!", "log_saved_to": AUTO_SAVE_PATH}

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

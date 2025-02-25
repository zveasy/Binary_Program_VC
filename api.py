import os
import sys
import shutil
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import FileResponse
import subprocess

# Ensure the firmware directory exists
FIRMWARE_DIR = "firmware"
os.makedirs(FIRMWARE_DIR, exist_ok=True)

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "API is working!"}

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

import os
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import FileResponse
import subprocess

app = FastAPI()

@app.post("/analyze")
async def analyze_firmware(file: UploadFile = File(...)):
    # Save the uploaded file
    file_location = f"firmware/{file.filename}"
    with open(file_location, "wb") as f:
        f.write(file.file.read())

    # Run the disassembler
    result = subprocess.run(
        ["python3", "rda_disassembler_enhanced.py", file_location], 
        capture_output=True, text=True
    )

    # Save output to a log file
    disassembly_log = "firmware/disassembly.log"
    with open(disassembly_log, "w") as log_file:
        log_file.write(result.stdout)

    return {"status": "PASS", "message": "Disassembly complete!", "log_file": "/download"}

@app.get("/download")
async def download_disassembly():
    return FileResponse("firmware/disassembly.log", filename="disassembly.log")

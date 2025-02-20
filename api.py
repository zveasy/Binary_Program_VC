import os
import sys  # ✅ Import sys
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import FileResponse
import subprocess

# Ensure the firmware directory exists
if not os.path.exists("firmware"):
    os.makedirs("firmware")

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "API is working!"}

@app.post("/analyze")
async def analyze_firmware(file: UploadFile = File(...)):
    # Save the uploaded file
    file_location = f"firmware/{file.filename}"
    with open(file_location, "wb") as f:
        f.write(file.file.read())

    # ✅ Run the disassembler using the same Python interpreter as FastAPI
    result = subprocess.run(
        [sys.executable, "rda_disassembler_enhanced.py", file_location], 
        capture_output=True, text=True
    )

    # Save output to a log file
    disassembly_log = "firmware/disassembly.log"
    with open(disassembly_log, "w") as log_file:
      
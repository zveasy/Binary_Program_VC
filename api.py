"""
CompLexAI FastAPI application — production-hardened.
"""
import logging
import os
import re
import shutil
import uuid
from typing import Optional

from fastapi import FastAPI, File, Request, UploadFile, HTTPException
from fastapi.responses import FileResponse, JSONResponse

from config import (
    AGENT_OUTPUT_DIR,
    API_KEY,
    AUTO_SAVE_DIR,
    FIRMWARE_DIR,
    LOG_LEVEL,
    MAX_UPLOAD_BYTES,
    RATE_LIMIT,
)
from engine.disassembler import DisassemblerEngine
from agent.firmware_audit import FirmwareAuditAgent

# --------------------------------------------------------------------------
# Logging
# --------------------------------------------------------------------------
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("complexai.api")

os.makedirs(FIRMWARE_DIR, exist_ok=True)

app = FastAPI(
    title="CompLexAI",
    description="Autonomous software reasoning agent powered by binary and graph analysis.",
    version="0.3.0",
)

# --------------------------------------------------------------------------
# Rate limiting (optional; requires slowapi)
# --------------------------------------------------------------------------
try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded

    limiter = Limiter(key_func=get_remote_address)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    limit_decorator = limiter.limit(RATE_LIMIT)
except ImportError:
    limiter = None
    limit_decorator = lambda f: f  # no-op when slowapi not installed


# --------------------------------------------------------------------------
# Optional API key auth
# --------------------------------------------------------------------------
def require_api_key(request: Request) -> None:
    if not API_KEY:
        return
    key = request.headers.get("X-API-Key") or request.headers.get("Authorization", "").replace("Bearer ", "")
    if key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


# --------------------------------------------------------------------------
# Upload validation
# --------------------------------------------------------------------------
ELF_MAGIC = b"\x7fELF"
SAFE_FILENAME_RE = re.compile(r"^[a-zA-Z0-9._-]+$")


def sanitize_filename(filename: Optional[str]) -> str:
    """Return a safe basename for saving uploads; prevent path traversal."""
    if not filename or not filename.strip():
        return f"upload_{uuid.uuid4().hex[:12]}.bin"
    base = os.path.basename(filename).strip()
    if not base or not SAFE_FILENAME_RE.match(base):
        return f"upload_{uuid.uuid4().hex[:12]}.bin"
    return base


def validate_elf_magic(data: bytes) -> bool:
    return len(data) >= 4 and data[:4] == ELF_MAGIC


async def read_upload_with_limit(file: UploadFile, max_bytes: int) -> bytes:
    """Read upload up to max_bytes; raise HTTPException 413 if exceeded."""
    chunks = []
    total = 0
    while True:
        chunk = await file.read(64 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size is {max_bytes // (1024*1024)} MiB.",
            )
        chunks.append(chunk)
    return b"".join(chunks)


# --------------------------------------------------------------------------
# Core endpoints
# --------------------------------------------------------------------------

@app.get("/")
async def root():
    return {"message": "CompLexAI API is working!", "version": "0.3.0"}


@app.get("/health")
async def health():
    """Liveness: service is running."""
    return {"status": "ok"}


@app.get("/ready")
async def ready():
    """Readiness: service can accept work (e.g. firmware dir writable)."""
    if not os.path.isdir(FIRMWARE_DIR):
        raise HTTPException(status_code=503, detail="Firmware directory not available")
    return {"status": "ready"}


@app.post("/analyze")
@limit_decorator
async def analyze_firmware(request: Request, file: UploadFile = File(...)):
    """Disassemble and analyze an uploaded firmware binary using the engine."""
    require_api_key(request)

    safe_name = sanitize_filename(file.filename)
    file_location = os.path.join(FIRMWARE_DIR, safe_name)

    try:
        data = await read_upload_with_limit(file, MAX_UPLOAD_BYTES)
    except HTTPException:
        raise

    if not data:
        raise HTTPException(status_code=400, detail="Empty file")
    if not validate_elf_magic(data):
        raise HTTPException(
            status_code=400,
            detail="File is not a valid ELF binary (magic 0x7f 'E' 'L' 'F' expected).",
        )

    try:
        with open(file_location, "wb") as f:
            f.write(data)
    except OSError as e:
        logger.exception("Failed to write upload to %s", file_location)
        raise HTTPException(status_code=500, detail="Failed to save upload")

    try:
        engine = DisassemblerEngine(output_dir=FIRMWARE_DIR)
        result = engine.analyze(file_location)
    except Exception as e:
        logger.exception("Disassembly failed for %s", file_location)
        raise HTTPException(status_code=500, detail="Analysis failed")

    if result.log_path and os.path.isfile(result.log_path):
        try:
            os.makedirs(AUTO_SAVE_DIR, exist_ok=True)
            shutil.copy(result.log_path, os.path.join(AUTO_SAVE_DIR, "disassembly_output.log"))
        except OSError:
            pass  # /app may not exist or be writable (e.g. local dev, tests)

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
    """Download the latest disassembly log. Returns 404 if no analysis has been run."""
    path = os.path.join(FIRMWARE_DIR, "disassembly.log")
    if not os.path.isfile(path):
        raise HTTPException(
            status_code=404,
            detail="No disassembly log found. Run POST /analyze first.",
        )
    return FileResponse(path, filename="disassembly.log")


# --------------------------------------------------------------------------
# Agent endpoints
# --------------------------------------------------------------------------

@app.post("/agent/audit")
@limit_decorator
async def agent_audit(request: Request, file: UploadFile = File(...)):
    """
    Run the Firmware Audit Agent on an uploaded binary.
    """
    require_api_key(request)

    safe_name = sanitize_filename(file.filename)
    file_location = os.path.join(FIRMWARE_DIR, safe_name)

    try:
        data = await read_upload_with_limit(file, MAX_UPLOAD_BYTES)
    except HTTPException:
        raise

    if not data:
        raise HTTPException(status_code=400, detail="Empty file")
    if not validate_elf_magic(data):
        raise HTTPException(
            status_code=400,
            detail="File is not a valid ELF binary (magic 0x7f 'E' 'L' 'F' expected).",
        )

    try:
        with open(file_location, "wb") as f:
            f.write(data)
    except OSError as e:
        logger.exception("Failed to write upload to %s", file_location)
        raise HTTPException(status_code=500, detail="Failed to save upload")

    try:
        agent = FirmwareAuditAgent(output_dir=AGENT_OUTPUT_DIR)
        result = agent.analyze(file_location)
    except Exception as e:
        logger.exception("Agent audit failed for %s", file_location)
        raise HTTPException(status_code=500, detail="Audit failed")

    return JSONResponse(content=result.to_dict())


@app.get("/agent/audit/report")
async def agent_audit_report():
    """Download the latest audit report as Markdown."""
    report_path = os.path.join(AGENT_OUTPUT_DIR, "audit_report.md")
    if not os.path.isfile(report_path):
        raise HTTPException(
            status_code=404,
            detail="No audit report found. Run POST /agent/audit first.",
        )
    return FileResponse(report_path, filename="audit_report.md")

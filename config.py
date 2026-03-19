"""
Production configuration from environment variables.
"""
import os

# Upload limits
MAX_UPLOAD_MB = float(os.environ.get("COMPLEXAI_MAX_UPLOAD_MB", "50"))
MAX_UPLOAD_BYTES = int(MAX_UPLOAD_MB * 1024 * 1024)

# Logging
LOG_LEVEL = os.environ.get("COMPLEXAI_LOG_LEVEL", "INFO").upper()

# Paths (allow override for Docker / different envs)
FIRMWARE_DIR = os.environ.get("COMPLEXAI_FIRMWARE_DIR", "firmware")
AUTO_SAVE_DIR = os.environ.get("COMPLEXAI_AUTO_SAVE_DIR", "/app")
AGENT_OUTPUT_DIR = os.environ.get("COMPLEXAI_AGENT_OUTPUT_DIR", "agent_output")

# Optional API key; if set, requests must include X-API-Key header
API_KEY = os.environ.get("COMPLEXAI_API_KEY", "").strip()

# Rate limit: requests per minute per IP (e.g. "60/min")
RATE_LIMIT = os.environ.get("COMPLEXAI_RATE_LIMIT", "30/minute")

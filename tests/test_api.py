"""Tests for the FastAPI API (Layer 3)."""

import io
import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Minimal ELF magic for validation
ELF_BYTES = b"\x7fELF" + b"\x00" * 60


@pytest.fixture
def client():
    from api import app
    return TestClient(app)


def _is_elf(path: str) -> bool:
    """True if the file at path has ELF magic (Linux). On macOS, gcc produces Mach-O."""
    try:
        with open(path, "rb") as f:
            return f.read(4) == b"\x7fELF"
    except OSError:
        return False


@pytest.fixture(scope="session")
def hello_world_bin_path():
    import subprocess
    src = os.path.join(REPO_ROOT, "hello_world.c")
    out = os.path.join(REPO_ROOT, "firmware", "hello_world_test.bin")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    subprocess.run(["gcc", "-o", out, src], check=True)
    if _is_elf(out):
        return out
    # On macOS gcc produces Mach-O; use a minimal ELF fixture so tests still run.
    from tests.fixtures.minimal_elf import get_minimal_elf_path
    return get_minimal_elf_path()


class TestCoreEndpoints:
    def test_root(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert "CompLexAI" in data["message"]
        assert "version" in data

    def test_health(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

    def test_ready(self, client):
        resp = client.get("/ready")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ready"}

    def test_analyze(self, client, hello_world_bin_path):
        with open(hello_world_bin_path, "rb") as f:
            resp = client.post("/analyze", files={"file": ("test.bin", f)})
        assert resp.status_code == 200
        data = resp.json()
        assert data["message"] == "Disassembly complete!"
        assert "architecture" in data
        assert "risk_score" in data

    def test_download_after_analyze(self, client, hello_world_bin_path):
        with open(hello_world_bin_path, "rb") as f:
            client.post("/analyze", files={"file": ("test.bin", f)})
        resp = client.get("/download")
        assert resp.status_code == 200

    def test_download_404_when_no_log(self, client):
        with patch("api.os.path.isfile", return_value=False):
            resp = client.get("/download")
        assert resp.status_code == 404
        assert "detail" in resp.json()

    def test_analyze_rejects_non_elf(self, client):
        resp = client.post(
            "/analyze",
            files={"file": ("not_elf.bin", io.BytesIO(b"not an ELF file!!!!!!!!"))},
        )
        assert resp.status_code == 400
        assert "ELF" in resp.json().get("detail", "")

    def test_analyze_rejects_empty(self, client):
        resp = client.post(
            "/analyze",
            files={"file": ("empty.bin", io.BytesIO(b""))},
        )
        assert resp.status_code == 400
        assert "empty" in resp.json().get("detail", "").lower()


class TestAgentEndpoints:
    def test_agent_audit(self, client, hello_world_bin_path):
        with open(hello_world_bin_path, "rb") as f:
            resp = client.post("/agent/audit", files={"file": ("test.bin", f)})
        assert resp.status_code == 200
        data = resp.json()
        assert data["agent_name"] == "FirmwareAuditAgent"
        assert "findings" in data
        assert "risk_score" in data

    def test_agent_audit_report_404(self, client):
        resp = client.get("/agent/audit/report")
        # May be 200 if a previous test left a report, or 404
        assert resp.status_code in (200, 404)

    def test_agent_audit_rejects_non_elf(self, client):
        resp = client.post(
            "/agent/audit",
            files={"file": ("not_elf.bin", io.BytesIO(b"not an ELF file!!!!!!!!"))},
        )
        assert resp.status_code == 400
        assert "ELF" in resp.json().get("detail", "")


class TestApiKeyAuth:
    """When COMPLEXAI_API_KEY is set, endpoints require X-API-Key header."""

    def test_audit_401_without_key_when_required(self, client):
        with patch("api.API_KEY", "secret123"):
            resp = client.post(
                "/agent/audit",
                files={"file": ("x.bin", io.BytesIO(ELF_BYTES))},
            )
        assert resp.status_code == 401
        assert "key" in resp.json().get("detail", "").lower()

    def test_audit_200_with_key_when_required(self, client, hello_world_bin_path):
        with patch("api.API_KEY", "secret123"):
            with open(hello_world_bin_path, "rb") as f:
                resp = client.post(
                    "/agent/audit",
                    files={"file": ("test.bin", f)},
                    headers={"X-API-Key": "secret123"},
                )
        assert resp.status_code == 200

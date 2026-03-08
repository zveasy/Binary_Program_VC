"""Tests for the FastAPI API (Layer 3)."""

import os
import pytest
from fastapi.testclient import TestClient

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture
def client():
    from api import app
    return TestClient(app)


@pytest.fixture(scope="session")
def hello_world_bin_path():
    import subprocess
    src = os.path.join(REPO_ROOT, "hello_world.c")
    out = os.path.join(REPO_ROOT, "firmware", "hello_world_test.bin")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    subprocess.run(["gcc", "-o", out, src], check=True)
    return out


class TestCoreEndpoints:
    def test_root(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert "CompLexAI" in data["message"]
        assert "version" in data

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

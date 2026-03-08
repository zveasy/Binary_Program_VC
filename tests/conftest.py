"""Shared test fixtures."""

import os
import subprocess
import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIRMWARE_DIR = os.path.join(REPO_ROOT, "firmware")


@pytest.fixture(scope="session")
def hello_world_bin():
    """Compile hello_world.c and return the binary path."""
    src = os.path.join(REPO_ROOT, "hello_world.c")
    out = os.path.join(FIRMWARE_DIR, "hello_world_test.bin")
    os.makedirs(FIRMWARE_DIR, exist_ok=True)
    subprocess.run(["gcc", "-o", out, src], check=True)
    return out


@pytest.fixture(scope="session")
def infinite_loop_bin():
    """Compile infinite_loop.c and return the binary path."""
    src = os.path.join(REPO_ROOT, "infinite_loop.c")
    out = os.path.join(FIRMWARE_DIR, "infinite_loop_test.bin")
    os.makedirs(FIRMWARE_DIR, exist_ok=True)
    subprocess.run(["gcc", "-o", out, src], check=True)
    return out


@pytest.fixture
def tmp_output_dir(tmp_path):
    """Return a temporary output directory for test results."""
    return str(tmp_path / "output")

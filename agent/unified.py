"""
UnifiedAuditAgent — accepts any input type and dispatches to the right agent.

Supports: ELF/binary files, C/C++ source files, and repository directories.
"""

import os
import subprocess
import tempfile
import time
from typing import Optional

from agent.base import AnalysisAgent, AgentResult, AgentFinding, Severity, FindingCategory
from agent.firmware_audit import FirmwareAuditAgent
from agent.pr_review import PRComplexityAgent


class UnifiedAuditAgent(AnalysisAgent):
    """
    Unified input agent that auto-detects input type and dispatches.

    Supported inputs:
    - ELF/binary file → FirmwareAuditAgent
    - C/C++ source file → compile then FirmwareAuditAgent
    - Directory (repo) → PRComplexityAgent on all source files

    Usage:
        agent = UnifiedAuditAgent()
        result = agent.analyze("firmware/my_binary.bin")
        result = agent.analyze("src/main.c")
        result = agent.analyze("/path/to/repo")
    """

    SOURCE_EXTENSIONS = {".c", ".cpp", ".cc", ".cxx"}

    def __init__(self, output_dir: str = "agent_output",
                 model_path: Optional[str] = None,
                 label_map_path: Optional[str] = None):
        super().__init__(name="UnifiedAuditAgent", output_dir=output_dir)
        self._model_path = model_path
        self._label_map_path = label_map_path

    def analyze(self, input_path: str, **kwargs) -> AgentResult:
        start = time.time()
        input_type = self._detect_input_type(input_path)

        if input_type == "binary":
            agent = FirmwareAuditAgent(
                output_dir=self.output_dir,
                model_path=self._model_path,
                label_map_path=self._label_map_path,
            )
            result = agent.analyze(input_path, **kwargs)
            result.agent_name = self.name
            return result

        elif input_type == "source":
            result = self._analyze_source(input_path)
            result.duration_seconds = time.time() - start
            return result

        elif input_type == "directory":
            source_files = self._find_source_files(input_path)
            if source_files:
                agent = PRComplexityAgent(output_dir=self.output_dir)
                result = agent.analyze(input_path, changed_files=source_files)
                result.agent_name = self.name
                return result
            else:
                binary_files = self._find_binary_files(input_path)
                if binary_files:
                    agent = FirmwareAuditAgent(
                        output_dir=self.output_dir,
                        model_path=self._model_path,
                        label_map_path=self._label_map_path,
                    )
                    result = agent.analyze(binary_files[0], **kwargs)
                    result.agent_name = self.name
                    return result

            result = AgentResult(agent_name=self.name, input_path=input_path)
            result.summary = "No analyzable files found in directory."
            result.safety_verdict = "PASS"
            result.duration_seconds = time.time() - start
            return result

        else:
            result = AgentResult(agent_name=self.name, input_path=input_path)
            result.summary = f"Unsupported input type: {input_path}"
            result.safety_verdict = "UNKNOWN"
            result.duration_seconds = time.time() - start
            return result

    def _detect_input_type(self, input_path: str) -> str:
        if os.path.isdir(input_path):
            return "directory"
        if not os.path.isfile(input_path):
            return "unknown"
        ext = os.path.splitext(input_path)[1].lower()
        if ext in self.SOURCE_EXTENSIONS:
            return "source"
        return "binary"

    def _analyze_source(self, src_path: str) -> AgentResult:
        """Compile a source file and analyze the resulting binary."""
        result = AgentResult(agent_name=self.name, input_path=src_path)
        ext = os.path.splitext(src_path)[1].lower()
        compiler = "g++" if ext in (".cpp", ".cc", ".cxx") else "gcc"

        with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as tmp:
            bin_path = tmp.name

        try:
            subprocess.run(
                [compiler, "-o", bin_path, src_path],
                capture_output=True, check=True, timeout=30,
            )
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            result.summary = f"Compilation failed for {src_path}: {e}"
            result.safety_verdict = "UNKNOWN"
            return result

        agent = FirmwareAuditAgent(
            output_dir=self.output_dir,
            model_path=self._model_path,
            label_map_path=self._label_map_path,
        )
        result = agent.analyze(bin_path)
        result.agent_name = self.name
        result.input_path = src_path

        try:
            os.unlink(bin_path)
        except OSError:
            pass
        return result

    def _find_source_files(self, dir_path: str) -> list:
        sources = []
        for root, dirs, files in os.walk(dir_path):
            dirs[:] = [d for d in dirs if d not in {".git", "node_modules", ".venv", "__pycache__"}]
            for f in files:
                if os.path.splitext(f)[1].lower() in self.SOURCE_EXTENSIONS:
                    sources.append(os.path.relpath(os.path.join(root, f), dir_path))
        return sources

    def _find_binary_files(self, dir_path: str) -> list:
        binaries = []
        for root, dirs, files in os.walk(dir_path):
            dirs[:] = [d for d in dirs if d not in {".git", "node_modules", ".venv"}]
            for f in files:
                if f.endswith((".bin", ".elf", ".so")):
                    binaries.append(os.path.join(root, f))
        return binaries

    def explain(self, result: AgentResult) -> str:
        return result.summary

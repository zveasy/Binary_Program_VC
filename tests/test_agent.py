"""Tests for the agent layer (Layer 2)."""

import json
import os
import pytest

from agent.firmware_audit import FirmwareAuditAgent
from agent.pr_review import PRComplexityAgent
from agent.unified import UnifiedAuditAgent
from agent.patches import generate_sarif, suggest_patches
from agent.base import Severity


class TestFirmwareAuditAgent:
    def test_safe_binary(self, hello_world_bin, tmp_output_dir):
        agent = FirmwareAuditAgent(output_dir=tmp_output_dir)
        result = agent.analyze(hello_world_bin)

        assert result.agent_name == "FirmwareAuditAgent"
        assert result.architecture == "x86_64"
        assert result.duration_seconds >= 0
        assert result.report_path is not None
        assert os.path.isfile(result.report_path)

    def test_unsafe_binary(self, infinite_loop_bin, tmp_output_dir):
        agent = FirmwareAuditAgent(output_dir=tmp_output_dir)
        result = agent.analyze(infinite_loop_bin)

        assert result.safety_verdict == "FAIL"
        assert result.risk_score >= 0.5
        assert result.critical_count >= 1
        loop_findings = [f for f in result.findings if f.category.value == "infinite_loop"]
        assert len(loop_findings) >= 1
        assert loop_findings[0].function_name == "main"

    def test_explain_produces_text(self, infinite_loop_bin, tmp_output_dir):
        agent = FirmwareAuditAgent(output_dir=tmp_output_dir)
        result = agent.analyze(infinite_loop_bin)
        summary = agent.explain(result)
        assert "infinite_loop_test.bin" in summary.lower() or "FAIL" in summary

    def test_to_dict_serializable(self, hello_world_bin, tmp_output_dir):
        agent = FirmwareAuditAgent(output_dir=tmp_output_dir)
        result = agent.analyze(hello_world_bin)
        d = result.to_dict()
        json_str = json.dumps(d)
        assert "agent_name" in json_str


class TestPRComplexityAgent:
    def test_analyze_c_files(self, tmp_output_dir):
        agent = PRComplexityAgent(output_dir=tmp_output_dir)
        result = agent.analyze(".", changed_files=["hello_world.c", "infinite_loop.c"])
        assert result.agent_name == "PRComplexityAgent"
        assert result.report_path is not None

    def test_no_files(self, tmp_output_dir):
        agent = PRComplexityAgent(output_dir=tmp_output_dir)
        result = agent.analyze(".", changed_files=[])
        assert result.safety_verdict == "PASS"

    def test_pr_comment_format(self, tmp_output_dir):
        agent = PRComplexityAgent(output_dir=tmp_output_dir)
        result = agent.analyze(".", changed_files=["infinite_loop.c"])
        comment = agent.format_as_pr_comment(result)
        assert "CompLexAI" in comment
        assert "Verdict" in comment


class TestUnifiedAuditAgent:
    def test_binary_input(self, hello_world_bin, tmp_output_dir):
        agent = UnifiedAuditAgent(output_dir=tmp_output_dir)
        result = agent.analyze(hello_world_bin)
        assert result.architecture == "x86_64"

    def test_source_input(self, tmp_output_dir):
        agent = UnifiedAuditAgent(output_dir=tmp_output_dir)
        result = agent.analyze("hello_world.c")
        assert result.architecture == "x86_64"

    def test_nonexistent_input(self, tmp_output_dir):
        agent = UnifiedAuditAgent(output_dir=tmp_output_dir)
        result = agent.analyze("/nonexistent/path")
        assert result.safety_verdict == "UNKNOWN"


class TestSARIF:
    def test_sarif_generation(self, infinite_loop_bin, tmp_output_dir):
        agent = FirmwareAuditAgent(output_dir=tmp_output_dir)
        result = agent.analyze(infinite_loop_bin)

        sarif_path = os.path.join(tmp_output_dir, "report.sarif.json")
        sarif = generate_sarif(result, output_path=sarif_path)

        assert sarif["version"] == "2.1.0"
        assert len(sarif["runs"]) == 1
        assert len(sarif["runs"][0]["results"]) > 0
        assert os.path.isfile(sarif_path)

    def test_sarif_valid_json(self, infinite_loop_bin, tmp_output_dir):
        agent = FirmwareAuditAgent(output_dir=tmp_output_dir)
        result = agent.analyze(infinite_loop_bin)

        sarif_path = os.path.join(tmp_output_dir, "report.sarif.json")
        generate_sarif(result, output_path=sarif_path)

        with open(sarif_path) as f:
            parsed = json.load(f)
        assert parsed["version"] == "2.1.0"


class TestPatches:
    def test_patch_suggestions(self, infinite_loop_bin, tmp_output_dir):
        agent = FirmwareAuditAgent(output_dir=tmp_output_dir)
        result = agent.analyze(infinite_loop_bin)

        patches = suggest_patches(result)
        assert len(patches) > 0
        assert "before" in patches[0]
        assert "after" in patches[0]

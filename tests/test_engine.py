"""Tests for the analysis engine (Layer 1)."""

import os
import pytest
from engine.disassembler import DisassemblerEngine, DisassemblyResult


class TestDisassemblerEngine:
    def test_hello_world_no_loops(self, hello_world_bin, tmp_output_dir):
        engine = DisassemblerEngine(output_dir=tmp_output_dir)
        result = engine.analyze(hello_world_bin)

        assert isinstance(result, DisassemblyResult)
        assert result.architecture == "x86_64"
        assert result.infinite_loops == []
        assert result.instruction_count > 0
        assert result.cfg_node_count > 0
        assert result.complexity_heuristic in ("O(1)", "O(n)")

    def test_infinite_loop_detected(self, infinite_loop_bin, tmp_output_dir):
        engine = DisassemblerEngine(output_dir=tmp_output_dir)
        result = engine.analyze(infinite_loop_bin)

        assert result.architecture == "x86_64"
        assert len(result.infinite_loops) >= 1
        assert result.safety_verdict == "FAIL"
        assert result.risk_score > 0.4

    def test_risk_score_range(self, hello_world_bin, tmp_output_dir):
        engine = DisassemblerEngine(output_dir=tmp_output_dir)
        result = engine.analyze(hello_world_bin)
        assert 0.0 <= result.risk_score <= 1.0

    def test_dot_file_generated(self, hello_world_bin, tmp_output_dir):
        engine = DisassemblerEngine(output_dir=tmp_output_dir)
        result = engine.analyze(hello_world_bin)
        assert result.dot_path is not None
        assert os.path.isfile(result.dot_path)

    def test_log_file_generated(self, hello_world_bin, tmp_output_dir):
        engine = DisassemblerEngine(output_dir=tmp_output_dir)
        result = engine.analyze(hello_world_bin)
        assert result.log_path is not None
        assert os.path.isfile(result.log_path)

    def test_printable_strings_extracted(self, hello_world_bin, tmp_output_dir):
        engine = DisassemblerEngine(output_dir=tmp_output_dir)
        result = engine.analyze(hello_world_bin)
        assert len(result.printable_strings) > 0

    def test_findings_populated(self, infinite_loop_bin, tmp_output_dir):
        engine = DisassemblerEngine(output_dir=tmp_output_dir)
        result = engine.analyze(infinite_loop_bin)
        assert len(result.findings) > 0
        categories = [f.category for f in result.findings]
        assert "infinite_loop" in categories

    def test_nonexistent_file(self, tmp_output_dir):
        engine = DisassemblerEngine(output_dir=tmp_output_dir)
        result = engine.analyze("/nonexistent/file.bin")
        assert result.instruction_count == 0


class TestReportGenerator:
    def test_from_result(self, hello_world_bin, tmp_output_dir):
        from engine.report import ReportGenerator
        engine = DisassemblerEngine(output_dir=tmp_output_dir)
        result = engine.analyze(hello_world_bin)

        report_path = os.path.join(tmp_output_dir, "test_report.md")
        report = ReportGenerator.from_result(result, report_path)

        assert os.path.isfile(report_path)
        assert "# Firmware Analysis Report" in report
        assert "Architecture" in report
        assert "Risk Score" in report

    def test_infinite_loop_report(self, infinite_loop_bin, tmp_output_dir):
        from engine.report import ReportGenerator
        engine = DisassemblerEngine(output_dir=tmp_output_dir)
        result = engine.analyze(infinite_loop_bin)

        report_path = os.path.join(tmp_output_dir, "loop_report.md")
        report = ReportGenerator.from_result(result, report_path)

        assert "FAIL" in report
        assert "Infinite Loop" in report


class TestGraphConversion:
    def test_dot_parser(self, hello_world_bin, tmp_output_dir):
        from engine.graph_conversion import DotParser
        engine = DisassemblerEngine(output_dir=tmp_output_dir)
        result = engine.analyze(hello_world_bin)

        G = DotParser.parse(result.dot_path)
        assert G.number_of_nodes() > 0

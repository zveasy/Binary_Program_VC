"""
DisassemblerEngine — programmatic API for binary disassembly and CFG analysis.

Refactored from rda_disassembler_enhanced.py into a clean, importable engine.
"""

import os
import sys
import string
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import networkx as nx
from elftools.elf.elffile import ELFFile
from elftools.elf.constants import SH_FLAGS
from elftools.elf.enums import ENUM_E_MACHINE
from capstone import (
    Cs, CS_ARCH_X86, CS_MODE_64, CS_ARCH_ARM, CS_MODE_ARM,
    CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN, CS_ARCH_MIPS, CS_MODE_32,
    CS_ARCH_PPC, CS_ARCH_RISCV,
)

try:
    from capstone import CS_MODE_RISC_V32, CS_MODE_RISC_V64
except ImportError:
    CS_MODE_RISC_V32 = 32
    CS_MODE_RISC_V64 = 64


@dataclass
class Finding:
    """A single analysis finding (loop, unreachable code, etc.)."""
    category: str
    severity: str  # "critical", "warning", "info"
    address: Optional[int] = None
    addresses: Optional[List[int]] = None
    description: str = ""


@dataclass
class DisassemblyResult:
    """Complete result from disassembling and analyzing a binary."""
    architecture: str = "Unknown"
    instruction_count: int = 0
    cfg_graph: Optional[nx.DiGraph] = None
    cfg_node_count: int = 0
    cfg_edge_count: int = 0
    infinite_loops: List[List[int]] = field(default_factory=list)
    unreachable_code: List[int] = field(default_factory=list)
    complexity_heuristic: str = "Unknown"
    printable_strings: List[Tuple[int, str]] = field(default_factory=list)
    findings: List[Finding] = field(default_factory=list)
    symbols: Dict[int, Tuple[str, bool]] = field(default_factory=dict)
    log_lines: List[str] = field(default_factory=list)
    dot_path: Optional[str] = None
    log_path: Optional[str] = None

    @property
    def risk_score(self) -> float:
        """Compute an overall risk score from 0.0 (safe) to 1.0 (critical)."""
        score = 0.0
        if self.infinite_loops:
            score += 0.4 + 0.05 * min(len(self.infinite_loops), 6)
        if self.unreachable_code:
            score += 0.15 + 0.01 * min(len(self.unreachable_code), 10)
        if self.complexity_heuristic in ("O(n^2)", "O(n^2) or higher"):
            score += 0.15
        elif self.complexity_heuristic == "O(n)":
            score += 0.05
        return min(score, 1.0)

    @property
    def safety_verdict(self) -> str:
        if self.infinite_loops or self.unreachable_code:
            return "FAIL"
        return "PASS"


class DisassemblerEngine:
    """
    Core disassembly and analysis engine.

    Usage:
        engine = DisassemblerEngine()
        result = engine.analyze("firmware/hello_world_test.bin")
        print(result.safety_verdict)
        print(result.infinite_loops)
    """

    def __init__(self, output_dir: str = "firmware", enable_angr: bool = False):
        self.output_dir = output_dir
        self.enable_angr = enable_angr
        os.makedirs(output_dir, exist_ok=True)

    def analyze(self, elf_path: str) -> DisassemblyResult:
        """Run full analysis pipeline on an ELF binary. Returns DisassemblyResult."""
        result = DisassemblyResult()

        if not os.path.exists(elf_path):
            result.log_lines.append(f"[ERROR] File not found: {elf_path}")
            return result

        with open(elf_path, "rb") as f:
            elffile = ELFFile(f)
            cs_arch, cs_mode, ptr_size = self._detect_arch(elffile, result)
            md = Cs(cs_arch, cs_mode)
            md.detail = True

            result.symbols = self._gather_symbols(elffile)

            exec_sections = self._load_executable_sections(elffile)
            all_insns = {}
            if exec_sections:
                for sec_name, data, base_addr, size in exec_sections:
                    result.log_lines.append(
                        f"[INFO] Section '{sec_name}' at 0x{base_addr:X}, size={size}"
                    )
                    sec_insns = self._linear_sweep(md, data, base_addr)
                    all_insns.update(sec_insns)

            result.instruction_count = len(all_insns)

            cfg_graph = self._build_cfg_graph(all_insns)
            result.cfg_graph = cfg_graph
            result.cfg_node_count = cfg_graph.number_of_nodes()
            result.cfg_edge_count = cfg_graph.number_of_edges()

            result.infinite_loops = self._detect_infinite_loops(cfg_graph)
            result.unreachable_code = self._detect_unreachable(cfg_graph)
            result.complexity_heuristic = self._estimate_complexity(cfg_graph)

            data_sections = self._load_data_sections(elffile)
            for sec_name, data, base_addr, size in data_sections:
                result.printable_strings.extend(
                    self._extract_strings(data, base_addr)
                )

        self._build_findings(result)

        dot_path = os.path.join(self.output_dir, "cfg.dot")
        self._write_dot(cfg_graph, all_insns, dot_path)
        result.dot_path = dot_path

        log_path = os.path.join(self.output_dir, "disassembly.log")
        self._write_log(result, all_insns, log_path)
        result.log_path = log_path

        return result

    # -- Architecture Detection --

    @staticmethod
    def _detect_arch(elffile, result: DisassemblyResult):
        e_machine = elffile.header.e_machine
        if isinstance(e_machine, str):
            e_machine = ENUM_E_MACHINE.get(e_machine, None)
        if e_machine is None:
            result.log_lines.append("[ERROR] Could not determine architecture.")
            return (CS_ARCH_X86, CS_MODE_64, 8)

        arch_map = {
            62: ("x86_64", CS_ARCH_X86, CS_MODE_64, 8),
            40: ("ARM (32-bit)", CS_ARCH_ARM, CS_MODE_ARM, 4),
            183: ("AArch64", CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN, 8),
            20: ("PowerPC 32-bit", CS_ARCH_PPC, CS_MODE_32, 4),
            21: ("PowerPC 64-bit", CS_ARCH_PPC, 8, 8),  # CS_MODE_64
            8: ("MIPS 32-bit", CS_ARCH_MIPS, CS_MODE_32, 4),
        }
        if e_machine in arch_map:
            name, arch, mode, ptr = arch_map[e_machine]
            result.architecture = name
            return (arch, mode, ptr)

        if e_machine == 243:  # RISC-V
            ei_class = elffile.header.e_ident['EI_CLASS']
            if ei_class == 1:
                result.architecture = "RISC-V 32-bit"
                return (CS_ARCH_RISCV, CS_MODE_RISC_V32, 4)
            result.architecture = "RISC-V 64-bit"
            return (CS_ARCH_RISCV, CS_MODE_RISC_V64, 8)

        result.architecture = f"Unknown (e_machine={e_machine})"
        return (CS_ARCH_X86, CS_MODE_64, 8)

    # -- Section Loading --

    @staticmethod
    def _load_executable_sections(elffile):
        results = []
        for section in elffile.iter_sections():
            if section['sh_flags'] & SH_FLAGS.SHF_EXECINSTR:
                results.append((
                    section.name, section.data(),
                    section['sh_addr'], section['sh_size']
                ))
        return results

    @staticmethod
    def _load_data_sections(elffile):
        results = []
        for section in elffile.iter_sections():
            flags = section['sh_flags']
            sh_type = section.header['sh_type']
            if not (flags & SH_FLAGS.SHF_EXECINSTR) and sh_type != 'SHT_NOBITS':
                data = section.data()
                if data:
                    results.append((
                        section.name, data,
                        section['sh_addr'], section['sh_size']
                    ))
        return results

    @staticmethod
    def _gather_symbols(elffile):
        sym_map = {}
        for section in elffile.iter_sections():
            if section.header['sh_type'] in ('SHT_SYMTAB', 'SHT_DYNSYM'):
                for sym in section.iter_symbols():
                    if sym['st_value'] != 0:
                        is_func = sym['st_info']['type'] in ['STT_FUNC', 'STT_GNU_IFUNC']
                        sym_map[sym['st_value']] = (sym.name, is_func)
        return sym_map

    # -- Disassembly --

    @staticmethod
    def _linear_sweep(md, code, base_addr):
        insn_map = {}
        for insn in md.disasm(code, base_addr):
            insn_map[insn.address] = (insn.mnemonic, insn.op_str, insn.size)
        return insn_map

    # -- CFG Construction --

    @staticmethod
    def _build_cfg_graph(insn_map):
        cfg = nx.DiGraph()
        sorted_addrs = sorted(insn_map.keys())
        branch_mnemonics = {"jmp", "b", "bl", "br", "cbz", "cbnz", "ret"}
        end_block = {"ret", "jmp", "br"}

        for addr in sorted_addrs:
            mnemonic, op_str, size = insn_map[addr]
            if mnemonic.lower() not in end_block:
                next_addr = addr + size
                if next_addr in insn_map:
                    cfg.add_edge(addr, next_addr)

            target = DisassemblerEngine._parse_immediate(op_str)
            if mnemonic.lower() in branch_mnemonics and target and target in insn_map:
                cfg.add_edge(addr, target)

        return cfg

    @staticmethod
    def _parse_immediate(operand_str):
        token = operand_str.strip().split(',')[0].strip().lstrip('#')
        if token.startswith("0x"):
            try:
                return int(token, 16)
            except ValueError:
                return None
        return None

    # -- Analysis --

    @staticmethod
    def _detect_infinite_loops(cfg_graph):
        infinite_loops = []
        for cycle in nx.simple_cycles(cfg_graph):
            cycle_set = set(cycle)
            has_exit = any(
                succ not in cycle_set
                for node in cycle
                for succ in cfg_graph.successors(node)
            )
            if not has_exit:
                infinite_loops.append(cycle)
        return infinite_loops

    @staticmethod
    def _detect_unreachable(cfg_graph):
        if cfg_graph.number_of_nodes() == 0:
            return []
        nodes = list(cfg_graph.nodes())
        entry = min(nodes)
        try:
            reachable = set(nx.descendants(cfg_graph, entry)) | {entry}
        except Exception:
            reachable = {entry}
        return [n for n in nodes if n not in reachable]

    @staticmethod
    def _estimate_complexity(cfg_graph):
        if cfg_graph.number_of_nodes() == 0:
            return "O(1)"
        n_nodes = cfg_graph.number_of_nodes()
        try:
            cycles = list(nx.simple_cycles(cfg_graph))
        except Exception:
            cycles = []
        n_cycles = len(cycles)
        max_cycle_len = max((len(c) for c in cycles), default=0)

        if n_nodes <= 3 and n_cycles == 0:
            return "O(1)"
        if n_cycles == 0:
            return "O(n)"
        if n_cycles == 1 and max_cycle_len <= 5:
            return "O(n)"
        if n_cycles >= 2 or max_cycle_len > 10:
            return "O(n^2)" if n_nodes < 200 else "O(n^2) or higher"
        return "O(n)"

    @staticmethod
    def _extract_strings(data, base_addr, min_len=4):
        results = []
        current_chars = []
        start_offset = 0
        is_printable = set(string.printable)

        for i, byte_val in enumerate(data):
            ch = chr(byte_val)
            if ch in is_printable and byte_val not in (0x0B, 0x0C):
                if not current_chars:
                    start_offset = i
                current_chars.append(ch)
            else:
                if len(current_chars) >= min_len:
                    results.append((base_addr + start_offset, ''.join(current_chars)))
                current_chars = []

        if len(current_chars) >= min_len:
            results.append((base_addr + start_offset, ''.join(current_chars)))

        return results

    # -- Findings Builder --

    @staticmethod
    def _build_findings(result: DisassemblyResult):
        for loop in result.infinite_loops:
            result.findings.append(Finding(
                category="infinite_loop",
                severity="critical",
                addresses=loop,
                description=f"Infinite loop detected: {' -> '.join(f'0x{a:x}' for a in loop)}"
            ))
        if result.unreachable_code:
            result.findings.append(Finding(
                category="unreachable_code",
                severity="warning",
                addresses=result.unreachable_code[:20],
                description=f"{len(result.unreachable_code)} unreachable code block(s) detected"
            ))
        if result.complexity_heuristic in ("O(n^2)", "O(n^2) or higher"):
            result.findings.append(Finding(
                category="high_complexity",
                severity="warning",
                description=f"Estimated complexity: {result.complexity_heuristic}"
            ))

    # -- Output Writers --

    @staticmethod
    def _write_dot(cfg_graph, insn_map, dot_path):
        import networkx.drawing.nx_pydot as nx_pydot
        nx_pydot.write_dot(cfg_graph, dot_path)

    @staticmethod
    def _write_log(result: DisassemblyResult, insn_map, log_path):
        with open(log_path, "w") as f:
            f.write("[INFO] Disassembly & Data Extraction Log Initialized.\n")
            f.write(f"[INFO] Architecture: {result.architecture}.\n")
            for line in result.log_lines:
                f.write(line + "\n")

            f.write("[INFO] Final Disassembly Results (executable sections):\n\n")
            for addr in sorted(insn_map.keys()):
                mnemonic, op_str, _ = insn_map[addr]
                sym_info = result.symbols.get(addr, ("", False))
                sym_hint = f"<{sym_info[0]}> " if sym_info[0] else ""
                f.write(f"0x{addr:08X}:  {sym_hint}{mnemonic} {op_str}\n")

            f.write("\n[INFO] Checking CFG for infinite loops...\n")
            if result.infinite_loops:
                f.write("[ALERT] Potential infinite loops detected:\n")
                for idx, loop in enumerate(result.infinite_loops, 1):
                    f.write(f"  Loop {idx}: {' -> '.join(f'0x{a:x}' for a in loop)}\n")
            else:
                f.write("[INFO] No infinite loops detected.\n")

            f.write(f"\n[INFO] Estimating algorithm complexity from CFG...\n")
            f.write(f"[INFO] Estimated complexity: {result.complexity_heuristic}\n")

            f.write("\n[INFO] Checking for unreachable code...\n")
            if result.unreachable_code:
                f.write("[ALERT] Unreachable code (control flow bug) detected at addresses:\n")
                for addr in result.unreachable_code[:20]:
                    f.write(f"  Unreachable: 0x{addr:x}\n")
            else:
                f.write("[INFO] No unreachable code detected.\n")

            if result.printable_strings:
                f.write("\n[INFO] Searching data sections for printable strings:\n")
                for addr, s in result.printable_strings:
                    display = s if len(s) < 100 else s[:100] + "..."
                    f.write(f"    0x{addr:08X}:  \"{display}\"\n")

            f.write(f"\n[INFO] CFG saved as {result.dot_path}\n")
            f.write("\n[INFO] Done. Full output is in firmware/disassembly.log.\n")

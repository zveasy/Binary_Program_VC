#!/usr/bin/env python3
"""
rda_enhanced_with_data_and_cfg.py

Extended from your original script to:
 1) Detect ELF architecture (x86_64, ARM, etc.)
 2) Disassemble all executable sections linearly
 3) Extract printable strings from non-executable data sections
 4) Build a BASIC Control Flow Graph (CFG) from the instruction-level disassembly

Usage:
  python rda_enhanced_with_data_and_cfg.py <firmware.elf>

Dependencies:
  pip install capstone pyelftools
  Also install Graphviz to convert .dot to .png: 'sudo apt-get install graphviz' (Linux)
"""

import sys
import os
import string
import angr
import argparse
from elftools.elf.elffile import ELFFile
from elftools.elf.constants import SH_FLAGS
from elftools.elf.enums import ENUM_E_MACHINE
from capstone import *
from angr.errors import SimTranslationError

# Handle older Capstone versions lacking RISC-V modes
try:
    from capstone import CS_MODE_RISC_V32, CS_MODE_RISC_V64
except ImportError:
    CS_MODE_RISC_V32 = 32
    CS_MODE_RISC_V64 = 64

# ------------------------------------------------------------------------------
# Logging Setup
# ------------------------------------------------------------------------------
LOG_PATH = "firmware/disassembly.log"
os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)

with open(LOG_PATH, "w") as f:
    f.write("[INFO] Disassembly & Data Extraction Log Initialized.\n")

def log_message(msg):
    """Log to file *and* print to terminal."""
    print(msg)
    with open(LOG_PATH, "a") as f:
        f.write(msg + "\n")

# ------------------------------------------------------------------------------
# Architecture Detection
# ------------------------------------------------------------------------------
def detect_arch(elffile):
    """
    Returns (cs_arch, cs_mode, ptr_size) for Capstone based on ELF e_machine.
    """
    e_machine = elffile.header.e_machine
    if isinstance(e_machine, str):
        e_machine = ENUM_E_MACHINE.get(e_machine, None)
    if e_machine is None:
        log_message("[ERROR] Could not determine architecture (e_machine=None).")
        sys.exit(1)

    arch_str = ENUM_E_MACHINE.get(e_machine, "UNKNOWN")
    log_message(f"[DEBUG] e_machine = {arch_str} (ID={e_machine})")

    if e_machine == 62:  # EM_X86_64
        log_message("[INFO] Architecture: x86_64.")
        return (CS_ARCH_X86, CS_MODE_64, 8)
    elif e_machine == 40:  # EM_ARM (32-bit)
        log_message("[INFO] Architecture: ARM (32-bit).")
        return (CS_ARCH_ARM, CS_MODE_ARM, 4)
    elif e_machine == 183:  # EM_AARCH64 (ARM64)
        log_message("[INFO] Architecture: AArch64.")
        return (CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN, 8)
    elif e_machine == 243:  # EM_RISCV
        ei_class = elffile.header.e_ident['EI_CLASS']
        if ei_class == 1:  # 32-bit
            log_message("[INFO] Architecture: RISC-V 32-bit.")
            return (CS_ARCH_RISCV, CS_MODE_RISC_V32, 4)
        else:  # 64-bit
            log_message("[INFO] Architecture: RISC-V 64-bit.")
            return (CS_ARCH_RISCV, CS_MODE_RISC_V64, 8)
    elif e_machine == 20:  # EM_PPC (32-bit)
        log_message("[INFO] Architecture: PowerPC 32-bit.")
        return (CS_ARCH_PPC, CS_MODE_32, 4)
    elif e_machine == 21:  # EM_PPC64 (64-bit)
        log_message("[INFO] Architecture: PowerPC 64-bit.")
        return (CS_ARCH_PPC, CS_MODE_64, 8)
    elif e_machine == 8:  # EM_MIPS (32-bit)
        log_message("[INFO] Architecture: MIPS 32-bit.")
        return (CS_ARCH_MIPS, CS_MODE_32, 4)

    log_message(f"[ERROR] Unsupported architecture: {e_machine} ({arch_str})")
    sys.exit(1)

# ------------------------------------------------------------------------------
# Section Loading
# ------------------------------------------------------------------------------
def load_executable_sections(elffile):
    """
    Returns [(name, bytes, base_addr, size)] for SHF_EXECINSTR sections.
    """
    results = []
    for section in elffile.iter_sections():
        flags = section['sh_flags']
        if flags & SH_FLAGS.SHF_EXECINSTR:
            results.append((section.name, section.data(),
                            section['sh_addr'], section['sh_size']))
    return results

def load_data_sections(elffile):
    """
    Returns [(name, bytes, base_addr, size)] for sections that are *not* executable
    but do have data (like .rodata, .data). Excludes SHT_NOBITS (e.g. .bss).
    """
    results = []
    for section in elffile.iter_sections():
        flags = section['sh_flags']
        sh_type = section.header['sh_type']
        # We'll skip empty/no-data sections like .bss or NOBITS, also skip symbol tables, etc.
        if not (flags & SH_FLAGS.SHF_EXECINSTR):  # Not executable
            # Exclude "NOBITS" sections which have no real data (like .bss).
            if sh_type != 'SHT_NOBITS':
                data = section.data()
                if data:  # Non-empty
                    results.append((section.name, data, section['sh_addr'], section['sh_size']))
    return results

# ------------------------------------------------------------------------------
# Symbol Table
# ------------------------------------------------------------------------------
def gather_symbols(elffile):
    """
    Return {addr: (symbol_name, is_func)} from SHT_SYMTAB or SHT_DYNSYM.
    """
    sym_map = {}
    for section in elffile.iter_sections():
        if section.header['sh_type'] in ('SHT_SYMTAB', 'SHT_DYNSYM'):
            for sym in section.iter_symbols():
                if sym['st_value'] != 0:
                    is_func = (sym['st_info']['type'] in ['STT_FUNC', 'STT_GNU_IFUNC'])
                    sym_map[sym['st_value']] = (sym.name, is_func)
    return sym_map

# ------------------------------------------------------------------------------
# Linear-Sweep Disassembly for Code Sections
# ------------------------------------------------------------------------------
def linear_sweep_disassemble(md, code, base_addr):
    """
    Disassemble code from start to end in one pass.
    Returns {addr: (mnemonic, op_str, size)} so we can build a CFG.
    """
    insn_map = {}
    for insn in md.disasm(code, base_addr):
        insn_map[insn.address] = (insn.mnemonic, insn.op_str, insn.size)
    return insn_map

# ------------------------------------------------------------------------------
# Extracting Printable ASCII Strings from Data Sections
# ------------------------------------------------------------------------------
def extract_printable_strings(data, base_addr, min_len=4):
    """
    Scan 'data' for runs of printable ASCII (length >= min_len).
    Returns list of (absolute_addr, string).
    """
    results = []
    current_chars = []
    start_offset = 0

    def flush_string(end_offset):
        s = ''.join(current_chars)
        absolute_addr = base_addr + start_offset
        results.append((absolute_addr, s))

    is_printable = set(string.printable)  # includes digits, letters, punctuation, whitespace

    for i, byte_val in enumerate(data):
        ch = chr(byte_val)
        if ch in is_printable and byte_val not in ("\x0B", "\x0C"):
            # Accumulate
            if not current_chars:
                start_offset = i
            current_chars.append(ch)
        else:
            if len(current_chars) >= min_len:
                flush_string(i)
            current_chars = []

    # leftover run
    if len(current_chars) >= min_len:
        flush_string(len(data))

    return results

##### ANGR INTEGRATION #####
def analyze_vex_ir_with_angr(binary_path):
    """
    1) Load the binary into angr
    2) Build a quick CFG (CFGFast)
    3) For each discovered function, print IR statements from each basic block
    """
    log_message("[ANGR] Loading binary with angr for IR analysis...")
    proj = angr.Project(binary_path, auto_load_libs=False)

    log_message("[ANGR] Building CFGFast...")
    cfg = proj.analyses.CFGFast()

    for func_addr, func in cfg.kb.functions.items():
        log_message(f"[ANGR] Function {func.name} at 0x{func_addr:x}")

        for block in func.blocks:
            try:
                irsb = block.vex  # Attempt to lift the block to VEX IR
            except SimTranslationError:
                log_message(f"  [WARN] Could not lift block at 0x{block.addr:x}, skipping.")
                continue  # Skip this block and move to the next

            log_message(f"  -- BasicBlock @ 0x{block.addr:x}, IR statements:")
            for i, stmt in enumerate(irsb.statements):
                log_message(f"    Stmt[{i}]: {stmt}")

    log_message("[ANGR] IR analysis complete.")

############################
# ------------------------------------------------------------------------------
# Basic CFG Builder
# ------------------------------------------------------------------------------
def build_cfg(insn_map):
    """
    Build a minimal control flow graph from {addr: (mnemonic, op_str, size)}.
    We'll produce a single DOT file 'firmware/cfg.dot'.

    Approach:
      - One node per instruction
      - If insn is *not* ret/jmp, add an edge to next insn (addr + size)
      - If insn is jmp/call/b/bl, parse immediate operand as hex => if found in insn_map, add edge
    """
    log_message("[INFO] Building a basic control-flow graph (CFG)...")

    # We'll gather edges in the form: (src_addr, dst_addr).
    # Then we'll output a single .dot file for everything.
    edges = []
    # Sort addresses so we can handle "fall-through"
    sorted_addrs = sorted(insn_map.keys())

    # Allowed "branch" mnemonics that might have an immediate
    branch_mnemonics = {"jmp", "call", "b", "bl"}

    # Instructions that typically end a function or block
    # so we won't add a fall-through edge
    end_block = {"ret", "jmp", "bra"}

    for i, addr in enumerate(sorted_addrs):
        (mnemonic, op_str, size) = insn_map[addr]

        # 1) Fall-through edge unless it's an end-block instruction
        if mnemonic.lower() not in end_block:
            next_addr = addr + size
            if next_addr in insn_map:
                edges.append((addr, next_addr))

        # 2) If it's a direct branch or call with an immediate operand, parse it
        if mnemonic.lower() in branch_mnemonics:
            target = parse_immediate(op_str)
            if target and target in insn_map:
                edges.append((addr, target))

    # Now output the .dot
    dot_path = "firmware/cfg.dot"
    log_message(f"[INFO] Writing CFG to {dot_path} ...")

    with open(dot_path, "w") as f:
        f.write("digraph RDA_CFG {\n")
        f.write("  rankdir=LR;\n")  # Lay out left to right
        # Create a node for each instruction
        for addr in sorted_addrs:
            (mnemonic, op_str, _) = insn_map[addr]
            label = f"{mnemonic} {op_str}"
            # Escape quotes
            label = label.replace("\"", "\\\"")
            f.write(f"  \"{addr:#x}\" [label=\"0x{addr:08X}: {label}\"];\n")

        # Create edges
        for (src, dst) in edges:
            f.write(f"  \"{src:#x}\" -> \"{dst:#x}\";\n")

        f.write("}\n")

    log_message("[INFO] CFG DOT file created. Convert to PNG with:\n"
                "       dot -Tpng firmware/cfg.dot -o cfg.png")


def parse_immediate(operand_str):
    """
    Very naive parse of an operand like "0x401050".
    Returns an int or None if we can't parse.
    """
    op = operand_str.strip()
    # If there's whitespace or commas, take the first token
    # e.g. "0x400080, #0x3" => "0x400080"
    token = op.split(',')[0].strip()
    # ARM might have '#' prefix => "#0x400080"
    token = token.lstrip('#')
    if token.startswith("0x"):
        try:
            return int(token, 16)
        except ValueError:
            return None
    return None

# ------------------------------------------------------------------------------
# Main
# ------------------------------------------------------------------------------

def main():
    # Argument Parsing
    parser = argparse.ArgumentParser()
    parser.add_argument("elf_path", help="Path to the firmware ELF file")
    parser.add_argument("--angr", action="store_true", help="Enable VEX IR analysis with angr")
    args = parser.parse_args()
    
    elf_path = args.elf_path  # Get firmware path from arguments

    if not os.path.exists(elf_path):
        log_message(f"[ERROR] File not found: {elf_path}")
        sys.exit(1)

    # 1) Open ELF and detect arch
    with open(elf_path, "rb") as f:
        elffile = ELFFile(f)
        cs_arch, cs_mode, ptr_size = detect_arch(elffile)

        # 2) Create Capstone disassembler
        md = Cs(cs_arch, cs_mode)
        md.detail = True

        # 3) Gather symbol info (function names, etc.)
        symbol_map = gather_symbols(elffile)

        # 4) Disassemble all executable sections *linearly*
        exec_sections = load_executable_sections(elffile)
        all_insns = {}
        if not exec_sections:
            log_message("[WARNING] No executable sections found.")
        else:
            log_message("[INFO] Disassembling executable sections (linear sweep).")
            for (sec_name, data, base_addr, size) in exec_sections:
                log_message(f"  >> Section '{sec_name}' at 0x{base_addr:X}, size={size}")
                sec_insns = linear_sweep_disassemble(md, data, base_addr)
                all_insns.update(sec_insns)

            # 5) Sort and log final code disassembly
            log_message("[INFO] Final Disassembly Results (executable sections):\n")
            for addr in sorted(all_insns.keys()):
                mnemonic, op_str, _size = all_insns[addr]
                sym_info = symbol_map.get(addr, ("", False))
                sym_name = sym_info[0]
                sym_hint = f"<{sym_name}> " if sym_name else ""
                line = f"0x{addr:08X}:  {sym_hint}{mnemonic} {op_str}"
                log_message(line)

        # 6) Dump data sections for strings
        data_sections = load_data_sections(elffile)
        if data_sections:
            log_message("\n[INFO] Searching data sections for printable strings:")
            for (sec_name, data, base_addr, size) in data_sections:
                log_message(f"\n  >> Section '{sec_name}' @0x{base_addr:X}, size={size} bytes")
                found_strings = extract_printable_strings(data, base_addr, min_len=4)
                if not found_strings:
                    log_message("    (No printable strings of length >= 4 found.)")
                else:
                    for (addr, s) in found_strings:
                        display_s = s if len(s) < 100 else s[:100] + "..."
                        log_message(f"    0x{addr:08X}:  \"{display_s}\"")

        # 7) Run angr analysis if --angr flag is used
        if args.angr:
            log_message("\n[INFO] Running angr for VEX IR analysis...")
            analyze_vex_ir_with_angr(elf_path)  # Call angr-based analysis

        log_message("\n[INFO] Done. Full output is in firmware/disassembly.log.")

if __name__ == "__main__":
    main()
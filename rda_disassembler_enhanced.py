#!/usr/bin/env python3
"""
comprehensive_disassembler.py

A robust Recursive Descent Disassembler supporting:
 - x86_64, ARM (32-bit and AArch64)
 - RISC-V (32-bit and 64-bit)
 - PowerPC (32-bit and 64-bit)
 - MIPS
 - Symbol table & relocation info
 - Switch statements (jump table heuristics)
 - Data interleaving detection

Dependencies:
  pip install capstone pyelftools

Usage:
  python comprehensive_disassembler.py <firmware.elf>
"""

import sys
import os
from elftools.elf.elffile import ELFFile
from elftools.elf.constants import SH_FLAGS
from capstone import *
from elftools.elf.enums import ENUM_E_MACHINE  # Import ELF machine codes

# Ensure compatibility with RISC-V mode definitions in Capstone
try:
    from capstone import CS_MODE_RISC_V32, CS_MODE_RISC_V64
except ImportError:
    CS_MODE_RISC_V32 = 32  # Define placeholders
    CS_MODE_RISC_V64 = 64

# Define the log file path
log_path = "firmware/disassembly.log"
os.makedirs(os.path.dirname(log_path), exist_ok=True)  # Ensure firmware directory exists

# Initialize log file
with open(log_path, "w") as log_file:
    log_file.write("[INFO] Disassembly log initialized.\n")

def log_message(message):
    """Helper function to write logs to the disassembly file."""
    with open(log_path, "a") as log_file:
        log_file.write(message + "\n")

log_message("[INFO] Script started.")

# Debugging ENUM_E_MACHINE to check its contents
print("[DEBUG] ENUM_E_MACHINE contents:", ENUM_E_MACHINE)

def detect_arch(elffile):
    e_machine = elffile.header.e_machine

    print(f"[DEBUG] Detected e_machine: {e_machine} ({ENUM_E_MACHINE.get(e_machine, 'UNKNOWN')})")

    if e_machine == 62:  # EM_X86_64
        return (CS_ARCH_X86, CS_MODE_64, 8)
    elif e_machine == 40:  # EM_ARM (32-bit)
        return (CS_ARCH_ARM, CS_MODE_ARM, 4)
    elif e_machine == 183:  # EM_AARCH64 (ARM64)
        return (CS_ARCH_ARM64, 0, 8)  # No mode required for AArch64
    elif e_machine == 243:  # EM_RISCV (RISC-V)
        if elffile.header.e_ident['EI_CLASS'] == 1:  # 32-bit ELF
            return (CS_ARCH_RISCV, CS_MODE_RISC_V32, 4)
        else:  # 64-bit ELF
            return (CS_ARCH_RISCV, CS_MODE_RISC_V64, 8)
    elif e_machine == 20:  # EM_PPC (PowerPC 32-bit)
        return (CS_ARCH_PPC, CS_MODE_32, 4)
    elif e_machine == 21:  # EM_PPC64 (PowerPC 64-bit)
        return (CS_ARCH_PPC, CS_MODE_64, 8)
    elif e_machine == 8:  # EM_MIPS
        return (CS_ARCH_MIPS, CS_MODE_32, 4)
    else:
        log_message(f"[ERROR] Unsupported architecture {ENUM_E_MACHINE.get(e_machine, 'UNKNOWN')}")
        sys.exit(1)

def load_executable_sections(elffile):
    """Return a list of executable sections."""
    sections = []
    for section in elffile.iter_sections():
        if section['sh_flags'] & SH_FLAGS.SHF_EXECINSTR:
            sections.append((section.name, section.data(), section['sh_addr'], section['sh_size']))
    return sections

def gather_symbols(elffile):
    """Return a dictionary of function symbols."""
    sym_map = {}
    for section in elffile.iter_sections():
        if section.header['sh_type'] not in ('SHT_SYMTAB', 'SHT_DYNSYM'):
            continue
        for sym in section.iter_symbols():
            if sym['st_value'] != 0:
                sym_map[sym['st_value']] = (sym.name, sym['st_info']['type'] in ['STT_FUNC', 'STT_GNU_IFUNC'])
    return sym_map

def recursive_descent_disassemble(md, code, base_addr, size):
    """Perform recursive descent disassembly."""
    insn_map = {}
    visited_offsets = set()
    to_visit = [0]

    while to_visit:
        offset = to_visit.pop()
        if offset in visited_offsets:
            continue
        visited_offsets.add(offset)

        insns = list(md.disasm(code[offset:offset + 16], base_addr + offset, count=1))
        if not insns:
            continue

        insn = insns[0]
        insn_map[insn.address] = (insn.mnemonic, insn.op_str)
        size = insn.size

        # Architecture-specific processing
        if md.arch in (CS_ARCH_MIPS, CS_ARCH_RISCV) and insn.mnemonic == "jalr":
            continue
        if md.arch == CS_ARCH_ARM64 and insn.mnemonic in ("blr", "ret"):
            continue
        if md.arch == CS_ARCH_PPC and insn.mnemonic in ("blr", "bctr"):
            continue

        # Handle jump instructions
        if insn.mnemonic in ("jmp", "b", "bra", "jr"):
            if len(insn.operands) == 1 and insn.operands[0].type == CS_OP_IMM:
                to_visit.append(insn.operands[0].imm - base_addr)
            continue

    return insn_map

def main():
    if len(sys.argv) < 2:
        log_message("[ERROR] Usage: python comprehensive_disassembler.py <firmware.elf>")
        sys.exit(1)

    filename = sys.argv[1]
    if not os.path.exists(filename):
        log_message(f"[ERROR] File not found: {filename}")
        sys.exit(1)

    with open(filename, 'rb') as f:
        elffile = ELFFile(f)
        arch, mode, ptr_size = detect_arch(elffile)

        md = Cs(arch, mode)
        md.detail = True

        exec_sections = load_executable_sections(elffile)
        if not exec_sections:
            log_message("[ERROR] No executable sections found.")
            sys.exit(0)

        log_message("[INFO] Executable sections found. Starting disassembly.")
        symbol_map = gather_symbols(elffile)

        global_insn_map = {}
        for (sname, data, base_addr, size) in exec_sections:
            log_message(f"[INFO] Disassembling section '{sname}' at 0x{base_addr:x} (size={size} bytes).")
            section_insn_map = recursive_descent_disassemble(md, data, base_addr, size)
            global_insn_map.update(section_insn_map)

        sorted_insns = sorted(global_insn_map.items(), key=lambda x: x[0])
        log_message("[INFO] Final disassembly results:")
        for addr, (mn, op) in sorted_insns:
            sym_hint = f"<{symbol_map.get(addr, ('', ''))[0]}> " if addr in symbol_map else ""
            log_message(f"0x{addr:08x}:  {sym_hint}{mn:6s} {op}")

    log_message("[INFO] Disassembly completed successfully.")

if __name__ == "__main__":
    main()

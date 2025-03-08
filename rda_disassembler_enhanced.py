#!/usr/bin/env python3
"""
rda_enhanced_with_data.py

A single script that:
 1) Detects the ELF architecture (x86_64, ARM, etc.).
 2) Disassembles all executable sections linearly.
 3) Extracts printable strings from non-executable data sections.

Usage:
  python rda_enhanced_with_data.py <firmware.elf>
  
Dependencies:
  pip install capstone pyelftools
"""

import sys
import os
import string
from elftools.elf.elffile import ELFFile
from elftools.elf.constants import SH_FLAGS
from elftools.elf.enums import ENUM_E_MACHINE
from capstone import *

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

    # Common architectures
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
    but do have data (i.e. sh_type != NOBITS). Typically includes .rodata, .data, etc.
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
    Returns {addr: (mnemonic, op_str)}.
    """
    insn_map = {}
    for insn in md.disasm(code, base_addr):
        insn_map[insn.address] = (insn.mnemonic, insn.op_str)
    return insn_map

# ------------------------------------------------------------------------------
# Extracting Printable ASCII Strings from Data Sections
# ------------------------------------------------------------------------------
def extract_printable_strings(data, base_addr, min_len=4):
    """
    Scan 'data' for sequences of printable ASCII (0x20..0x7E, plus tab, newline, etc.)
    that are at least 'min_len' in length.

    Returns a list of (absolute_address, string) for each discovered run of ASCII chars.
    """
    results = []
    current_chars = []
    start_offset = 0

    def flush_string(end_offset):
        # Convert accumulated chars to a string and add to results
        s = ''.join(current_chars)
        absolute_addr = base_addr + start_offset
        results.append((absolute_addr, s))

    is_printable = set(string.printable)  # 'printable' includes digits, letters, punctuation, whitespace
    # Note that string.printable goes up to ~0x7E, plus \t\n\r\x0b\x0c, etc.

    for i, byte_val in enumerate(data):
        ch = chr(byte_val)
        if ch in is_printable and byte_val != 0x0B and byte_val != 0x0C:
            # Accumulate
            if not current_chars:
                # Start of a new string
                start_offset = i
            current_chars.append(ch)
        else:
            # Non-printable or disallowed control character => flush if we have a run
            if len(current_chars) >= min_len:
                flush_string(i)
            current_chars = []

    # If there's a leftover run at the end
    if len(current_chars) >= min_len:
        flush_string(len(data))

    return results

# ------------------------------------------------------------------------------
# Main
# ------------------------------------------------------------------------------
def main():
    if len(sys.argv) < 2:
        log_message("[ERROR] Usage: python rda_enhanced_with_data.py <firmware.elf>")
        sys.exit(1)

    elf_path = sys.argv[1]
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
        if not exec_sections:
            log_message("[WARNING] No executable sections found.")
        else:
            log_message("[INFO] Disassembling executable sections (linear sweep).")
            all_insns = {}
            for (sec_name, data, base_addr, size) in exec_sections:
                log_message(f"  >> Section '{sec_name}' at 0x{base_addr:X}, size={size}")
                sec_insns = linear_sweep_disassemble(md, data, base_addr)
                all_insns.update(sec_insns)

            # 5) Sort and log the final code disassembly
            log_message("[INFO] Final Disassembly Results (executable sections):\n")
            for addr in sorted(all_insns.keys()):
                mnemonic, op_str = all_insns[addr]
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
                        # Show address + the string
                        # Truncate the string a bit if it's extremely long
                        display_s = s if len(s) < 100 else s[:100] + "..."
                        log_message(f"    0x{addr:08X}:  \"{display_s}\"")

        log_message("\n[INFO] Done. Full output is in firmware/disassembly.log.")

if __name__ == "__main__":
    main()
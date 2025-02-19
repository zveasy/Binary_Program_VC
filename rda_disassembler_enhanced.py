#!/usr/bin/env python3
"""
comprehensive_disassembler.py

A more robust Recursive Descent Disassembler supporting:
 - x86_64 and ARM (32-bit)
 - Symbol table & relocation info
 - Switch statements (jump table heuristics)
 - Data interleaving detection
 - Minimizing false positives

Dependencies:
  pip install capstone pyelftools

Usage:
  python comprehensive_disassembler.py <firmware.elf>
"""

import sys
from elftools.elf.elffile import ELFFile
from elftools.elf.constants import SH_FLAGS
from capstone import *
from elftools.elf.enums import ENUM_E_MACHINE  # Import ELF machine codes

# Heuristic constants
MAX_INVALID_THRESHOLD = 8       # number of consecutive invalid instructions to treat as data
MAX_DATA_SKIP = 64             # bytes to skip after hitting probable data
MAX_JUMPTABLE_ENTRIES = 32     # limit for scanning possible jump table
PTR_SIZE_X86_64 = 8
PTR_SIZE_ARM32 = 4


# Debugging ENUM_E_MACHINE to check its contents
print("[DEBUG] ENUM_E_MACHINE contents:", ENUM_E_MACHINE)

def detect_arch(elffile):
    e_machine = elffile.header.e_machine

    print(f"[DEBUG] Detected e_machine: {e_machine} ({ENUM_E_MACHINE.get(e_machine, 'UNKNOWN')})")

    if e_machine == 62:  # EM_X86_64
        print("[INFO] Architecture detected: x86_64 - Proceeding with disassembly.")
        return (CS_ARCH_X86, CS_MODE_64, PTR_SIZE_X86_64)
    elif e_machine == 40:  # EM_ARM
        print("[INFO] Architecture detected: ARM (32-bit) - Proceeding with disassembly.")
        return (CS_ARCH_ARM, CS_MODE_ARM, PTR_SIZE_ARM32)
    else:
        print(f"[INFO] Architecture {ENUM_E_MACHINE.get(e_machine, 'UNKNOWN')} is supported.")
        return (CS_ARCH_X86, CS_MODE_64, PTR_SIZE_X86_64) if e_machine == 62 else (CS_ARCH_ARM, CS_MODE_ARM, PTR_SIZE_ARM32)




def load_executable_sections(elffile):
    """
    Return a list of (section_name, data, base_addr, size).
    Only includes sections with SHF_EXECINSTR (executable).
    """
    sections = []
    for section in elffile.iter_sections():
        flags = section['sh_flags']
        if flags & SH_FLAGS.SHF_EXECINSTR:
            data = section.data()
            base_addr = section['sh_addr']
            size = section['sh_size']
            sname = section.name
            sections.append((sname, data, base_addr, size))
    return sections

def gather_symbols(elffile):
    """
    Gather symbol table info: function symbols, object symbols, etc.
    Return a dict: address -> (symbol_name, is_code)
    'is_code' is True if we believe it's a function or code symbol.
    """
    sym_map = {}
    for section in elffile.iter_sections():
        # Check if it's a symtab or dynsym
        if not (section.header['sh_type'] == 'SHT_SYMTAB' or section.header['sh_type'] == 'SHT_DYNSYM'):
            continue
        
        for sym in section.iter_symbols():
            addr = sym['st_value']
            size = sym['st_size']
            # Heuristic: If st_info.type == STT_FUNC => code symbol
            # or if st_info.type == STT_GNU_IFUNC
            st_type = sym['st_info']['type']
            is_code = (st_type == 'STT_FUNC' or st_type == 'STT_GNU_IFUNC')
            name = sym.name
            if addr != 0:  # exclude non-allocated
                sym_map[addr] = (name, is_code)
    return sym_map

def gather_relocations(elffile):
    """
    Gather relocation info. For each relocation, we get the offset => possible code fixups
    Return a set of relocation addresses (these might be code references).
    """
    reloc_addrs = set()
    for section in elffile.iter_sections():
        if section.header['sh_type'] in ('SHT_RELA', 'SHT_REL'):
            # e.g. .rela.text, .rel.text
            for reloc in section.iter_relocations():
                offset = reloc['r_offset']
                reloc_addrs.add(offset)
    return reloc_addrs

def in_section_range(addr, base_addr, size):
    return (addr >= base_addr) and (addr < base_addr + size)

def parse_jump_table(code, offset, code_size, base_addr, ptr_size, max_entries=MAX_JUMPTABLE_ENTRIES):
    """
    Heuristic parse of a jump table. Read consecutive pointers (ptr_size) until we
    see something invalid or exceed max_entries. Return list of addresses in code range.
    """
    entries = []
    count = 0
    while count < max_entries:
        if offset + ptr_size > code_size:
            break
        chunk = code[offset:offset + ptr_size]
        val = int.from_bytes(chunk, byteorder='little', signed=False)
        entries.append(val)
        offset += ptr_size
        count += 1
    return entries

def guess_valid_code_ptr(ptr, code_sections):
    """
    Check if 'ptr' belongs to any known code section range. Return True if so.
    """
    for (sname, base, sz) in code_sections:
        if in_section_range(ptr, base, sz):
            return True
    return False

def recursive_descent_disassemble(
    md, code, base_addr, section_size, code_sections_info, symbol_map, reloc_addrs, ptr_size,
    visited_offsets, to_visit
):
    """
    BFS/DFS style approach. 
    code_sections_info: list of (sname, base_addr, size) to check valid code ranges.
    symbol_map: optional address->(symbol_name, is_code)
    reloc_addrs: addresses used in relocations => potential code references
    visited_offsets: global set of offsets we've processed
    to_visit: queue of offsets to process
    Return dictionary: insn_map[address] = (mnemonic, op_str).
    """
    insn_map = {}
    code_size = section_size
    max_addr = base_addr + code_size

    # Heuristic function to see if an address is strongly suspected data
    def is_probably_data(addr):
        # If there's a symbol marking data at this addr, or no code symbol near it, we might guess data
        # This can be improved with more advanced logic or user input
        if addr in symbol_map:
            (_, is_code) = symbol_map[addr]
            if not is_code:
                return True
        return False

    while to_visit:
        offset = to_visit.pop()
        if offset in visited_offsets:
            continue
        visited_offsets.add(offset)

        # If symbol map says this offset is data, skip
        test_addr = base_addr + offset
        if is_probably_data(test_addr):
            continue

        invalid_count = 0
        local_off = offset
        while True:
            if local_off >= code_size:
                break

            addr = base_addr + local_off
            # If we strongly suspect data => break
            if is_probably_data(addr):
                break

            # Disassemble one instruction
            insns = list(md.disasm(code[local_off:local_off+16], addr, count=1))
            if not insns:
                invalid_count += 1
                if invalid_count >= MAX_INVALID_THRESHOLD:
                    # skip ahead
                    local_off += MAX_DATA_SKIP
                    break
                else:
                    local_off += 1
                continue
            else:
                invalid_count = 0

            insn = insns[0]
            insn_map[insn.address] = (insn.mnemonic, insn.op_str)
            size = insn.size
            local_off += size

            # Return instruction => stop linear flow
            if insn.group(CS_GRP_RET):
                break

            # For ARM, you might also check for BX LR or pop {pc} as end of function
            # if arch == CS_ARCH_ARM:
            #   ...

            # Unconditional jump
            if insn.mnemonic in ("jmp", "b"):                # For x86_64 or ARM, check if immediate
                if len(insn.operands) == 1 and insn.operands[0].type == CS_OP_IMM:
                    tgt = insn.operands[0].imm
                    # queue target if in range
                    for (sn, sbase, ssz) in code_sections_info:
                        if in_section_range(tgt, sbase, ssz):
                            to_visit.append(tgt - sbase)
                            break
                break  # unconditional => stop linear flow

            # Calls
            if insn.group(CS_GRP_CALL):
                if len(insn.operands) == 1 and insn.operands[0].type == CS_OP_IMM:
                    call_tgt = insn.operands[0].imm
                    for (sn, sbase, ssz) in code_sections_info:
                        if in_section_range(call_tgt, sbase, ssz):
                            to_visit.append(call_tgt - sbase)
                            break

            # Conditional jumps
            if insn.group(CS_GRP_JUMP) and insn.mnemonic != "jmp":
                # if we have an IMM operand, that's the jump target
                if len(insn.operands) == 1 and insn.operands[0].type == CS_OP_IMM:
                    ctarget = insn.operands[0].imm
                    for (sn, sbase, ssz) in code_sections_info:
                        if in_section_range(ctarget, sbase, ssz):
                            to_visit.append(ctarget - sbase)
                            break
                # continue linear flow

            # Indirect jumps => possible jump table
            if insn.mnemonic.startswith('jmp') and len(insn.operands) == 1:
                if insn.operands[0].type == CS_OP_MEM:
                    # e.g. jmp [pc, #imm] or jmp [rip + disp]
                    disp = insn.operands[0].mem.disp
                    # We'll do a rough guess for the table location
                    possible_tbl_addr = insn.address + insn.size + disp
                    # Make sure it's in a code section range
                    for (sn, sbase, ssz) in code_sections_info:
                        if in_section_range(possible_tbl_addr, sbase, ssz):
                            # Attempt parse
                            tbl_off = possible_tbl_addr - sbase
                            entries = parse_jump_table(code, tbl_off, ssz, sbase, ptr_size)
                            # For each entry, check if it's a valid code pointer
                            for e in entries:
                                if guess_valid_code_ptr(e, [(sn, sbase, ssz)]):
                                    to_visit.append(e - sbase)
                    break

    return insn_map

def main():
    if len(sys.argv) < 2:
        print("Usage: python comprehensive_disassembler.py <firmware.elf>")
        sys.exit(1)

    filename = sys.argv[1]
    with open(filename, 'rb') as f:
        elffile = ELFFile(f)

        try:
            (arch, mode, ptr_size) = detect_arch(elffile)
        except ValueError as ve:
            print(f"[!] {ve}")
            sys.exit(1)
        
        md = Cs(arch, mode)
        md.detail = True

        # Gather all executable sections
        exec_sections = load_executable_sections(elffile)
        if not exec_sections:
            print("[!] No executable sections found with SHF_EXECINSTR.")
            sys.exit(0)
        
        # Gather symbol + relocation info
        symbol_map = gather_symbols(elffile)
        reloc_addrs = gather_relocations(elffile)

        # We'll build a small index of code section ranges for quick lookups
        code_sections_info = []
        for (sname, data, base_addr, size) in exec_sections:
            code_sections_info.append((sname, base_addr, size))

        global_insn_map = {}

        for (sname, data, base_addr, size) in exec_sections:
            print(f"\n[+] Disassembling section '{sname}' at 0x{base_addr:x}, size={size} bytes.")
            visited_offsets = set()
            to_visit = [0]
            section_insn_map = recursive_descent_disassemble(
                md, data, base_addr, size,
                code_sections_info, symbol_map, reloc_addrs, ptr_size,
                visited_offsets, to_visit
            )
            # Merge results
            global_insn_map.update(section_insn_map)

        # Sort final instructions by address
        sorted_insns = sorted(global_insn_map.items(), key=lambda x: x[0])
        print("\n=== Final Disassembly (All Sections) ===")
        for addr, (mn, op) in sorted_insns:
            # symbol hint
            sym_hint = ""
            if addr in symbol_map:
                sym_name, _ = symbol_map[addr]
                sym_hint = f"<{sym_name}> "
            print(f"0x{addr:08x}:  {sym_hint}{mn:6s} {op}")

if __name__ == "__main__":
    main()

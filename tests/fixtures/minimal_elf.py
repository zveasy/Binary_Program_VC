"""
Generate a minimal valid ELF64 (x86_64) Linux executable for tests.
Used on macOS where gcc produces Mach-O; this provides an ELF so analyze/audit tests can run.
"""
import os
import struct

# ELF64 header (64 bytes) + one PT_LOAD program header (56 bytes) + minimal code
# e_entry = 0x78 (120) so code starts at offset 120
# Layout: [ELF header 64][Phdr 56][padding 0][code 8]

def build_minimal_elf() -> bytes:
    # e_ident: magic, class=2(64), data=1(LE), version=1, rest 0
    e_ident = b"\x7fELF" + bytes([2, 1, 1, 0] + [0] * 8)
    # ELF64 header (little-endian)
    e_type = 2       # ET_EXEC
    e_machine = 62   # EM_X86_64
    e_version = 1
    e_entry = 0x78
    e_phoff = 64
    e_shoff = 0
    e_flags = 0
    e_ehsize = 64
    e_phentsize = 56
    e_phnum = 1
    e_shentsize = 64
    e_shnum = 0
    e_shstrndx = 0
    ehdr = struct.pack(
        "<16sHHIQQQIHHHHHH",
        e_ident, e_type, e_machine, e_version, e_entry, e_phoff, e_shoff,
        e_flags, e_ehsize, e_phentsize, e_phnum, e_shentsize, e_shnum, e_shstrndx,
    )
    assert len(ehdr) == 64

    # Program header: PT_LOAD, load from offset 0, vaddr 0, filesz/memsz to cover code
    p_type = 1    # PT_LOAD
    p_flags = 5   # PF_R | PF_X
    p_offset = 0
    p_vaddr = 0
    p_paddr = 0
    p_filesz = 128
    p_memsz = 128
    p_align = 0x1000
    phdr = struct.pack(
        "<IIQQQQQQ",
        p_type, p_flags, p_offset, p_vaddr, p_paddr, p_filesz, p_memsz, p_align,
    )
    assert len(phdr) == 56

    # Minimal code at offset 0x78: xor eax,eax; ret (so we have at least one instruction for CFG)
    code = b"\x31\xc0\xc3"  # xor eax, eax; ret
    padding = b"\x00" * (0x78 - 64 - 56 - len(code))
    return ehdr + phdr + padding + code


def get_minimal_elf_path() -> str:
    """Return path to a minimal ELF file, creating it if needed."""
    directory = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(directory, "minimal_x64.elf")
    if not os.path.isfile(path):
        with open(path, "wb") as f:
            f.write(build_minimal_elf())
    return path

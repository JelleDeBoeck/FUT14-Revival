from pathlib import Path
import struct

from capstone import Cs, CS_ARCH_X86, CS_MODE_32

DLL = Path(r"C:\Program Files\EA Games\FIFA 14\Game\CardsDLLzf.dll")

TARGETS = {
    "Before Addon_GoToWC": 0x8A7A0,
}

BEFORE = 0x1800
AFTER = 0x100


def u16(data, off):
    return struct.unpack_from("<H", data, off)[0]


def u32(data, off):
    return struct.unpack_from("<I", data, off)[0]


data = DLL.read_bytes()

pe_off = u32(data, 0x3C)
coff = pe_off + 4

num_sections = u16(data, coff + 2)
size_optional = u16(data, coff + 16)

optional = coff + 20

if u16(data, optional) != 0x10B:
    raise RuntimeError("PE32 verwacht")

image_base = u32(data, optional + 28)
section_table = optional + size_optional

sections = []

for i in range(num_sections):
    off = section_table + i * 40

    name = (
        data[off:off + 8]
        .split(b"\x00", 1)[0]
        .decode("ascii", errors="replace")
    )

    rva = u32(data, off + 12)
    raw_size = u32(data, off + 16)
    raw_ptr = u32(data, off + 20)

    sections.append({
        "name": name,
        "rva": rva,
        "raw_size": raw_size,
        "raw_ptr": raw_ptr,
    })


def file_to_rva(file_offset):
    for s in sections:
        start = s["raw_ptr"]
        end = start + s["raw_size"]

        if start <= file_offset < end:
            return s["rva"] + (file_offset - start)

    return None


def file_to_va(file_offset):
    rva = file_to_rva(file_offset)

    if rva is None:
        return None

    return image_base + rva


md = Cs(CS_ARCH_X86, CS_MODE_32)

print(f"[INFO] DLL        : {DLL}")
print(f"[INFO] image base : 0x{image_base:08X}")
print()


for name, target in TARGETS.items():

    start = max(0, target - BEFORE)
    end = min(len(data), target + AFTER)

    start_va = file_to_va(start)
    target_va = file_to_va(target)

    print("=" * 100)
    print(name)
    print("=" * 100)

    print(f"target file : 0x{target:X}")
    print(f"target VA   : 0x{target_va:08X}")
    print(f"range       : 0x{start:X} - 0x{end:X}")
    print()

    code = data[start:end]

    for insn in md.disasm(code, start_va):

        insn_file = start + (insn.address - start_va)

        marker = ""

        if insn_file <= target < insn_file + insn.size:
            marker = "   <== TARGET"

        raw = " ".join(
            f"{b:02X}"
            for b in insn.bytes
        )

        print(
            f"file=0x{insn_file:08X}  "
            f"VA=0x{insn.address:08X}  "
            f"{raw:<24} "
            f"{insn.mnemonic:<8} "
            f"{insn.op_str}"
            f"{marker}"
        )

    print()

print("[DONE]")
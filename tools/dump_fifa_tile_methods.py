from pathlib import Path
import struct

from capstone import Cs, CS_ARCH_X86, CS_MODE_32

EXE = Path(
    r"C:\Program Files\EA Games\FIFA 14\Game\fifa14.exe"
)

OUT = Path(
    r"D:\Afbeeldingen\FUT14-Revival\extracted\fifa_tile_methods.txt"
)

TARGETS = {
    "vtable+0x28": 0x00D691A0,
    "vtable+0x34": 0x00D691C0,
    "vtable+0x38": 0x00D691B0,
}

data = EXE.read_bytes()


def u16(off):
    return struct.unpack_from("<H", data, off)[0]


def u32(off):
    return struct.unpack_from("<I", data, off)[0]


# ---------------------------------------------------------
# Minimal PE parser
# ---------------------------------------------------------

if data[:2] != b"MZ":
    raise RuntimeError("Geen geldig PE/MZ-bestand")

pe_off = u32(0x3C)

if data[pe_off:pe_off + 4] != b"PE\x00\x00":
    raise RuntimeError("PE header niet gevonden")

coff = pe_off + 4

number_of_sections = u16(coff + 2)
optional_size = u16(coff + 16)

optional = coff + 20

magic = u16(optional)

if magic != 0x10B:
    raise RuntimeError(
        f"Verwacht 32-bit PE32, magic=0x{magic:X}"
    )

image_base = u32(optional + 28)

section_table = optional + optional_size

sections = []

for i in range(number_of_sections):
    off = section_table + i * 40

    name = (
        data[off:off + 8]
        .split(b"\x00", 1)[0]
        .decode("ascii", errors="replace")
    )

    virtual_size = u32(off + 8)
    virtual_address = u32(off + 12)
    raw_size = u32(off + 16)
    raw_offset = u32(off + 20)

    sections.append({
        "name": name,
        "rva": virtual_address,
        "vsize": virtual_size,
        "raw_size": raw_size,
        "raw": raw_offset,
    })


def rva_to_file(rva):
    for s in sections:
        size = max(s["vsize"], s["raw_size"])

        if s["rva"] <= rva < s["rva"] + size:
            return s["raw"] + (rva - s["rva"])

    raise RuntimeError(
        f"RVA 0x{rva:X} zit niet in een PE section"
    )


md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = False

lines = []

lines.append(f"EXE: {EXE}")
lines.append(f"ImageBase: 0x{image_base:08X}")
lines.append("")

lines.append("Sections:")
for s in sections:
    lines.append(
        f"  {s['name']:<8} "
        f"RVA=0x{s['rva']:08X} "
        f"RAW=0x{s['raw']:08X} "
        f"VSIZE=0x{s['vsize']:08X} "
        f"RAWSIZE=0x{s['raw_size']:08X}"
    )

lines.append("")
lines.append("=" * 90)

# Dump ruim rondom iedere concrete target.
# Overlap is expres nuttig: deze adressen liggen maar
# 0x10 bytes uit elkaar en kunnen thunks/wrappers zijn.

for name, rva in TARGETS.items():

    start_rva = max(0, rva - 0x40)
    file_off = rva_to_file(start_rva)

    blob = data[file_off:file_off + 0x140]

    start_va = image_base + start_rva
    target_va = image_base + rva

    lines.append("")
    lines.append(
        f"{name}: RVA=0x{rva:08X} "
        f"VA=0x{target_va:08X}"
    )
    lines.append("-" * 90)

    for ins in md.disasm(blob, start_va):

        marker = ">>" if ins.address == target_va else "  "

        ins_file = file_off + (
            ins.address - start_va
        )

        raw = bytes(ins.bytes).hex(" ").upper()

        lines.append(
            f"{marker} "
            f"FILE=0x{ins_file:08X} "
            f"VA=0x{ins.address:08X} "
            f"{raw:<28} "
            f"{ins.mnemonic:<8} "
            f"{ins.op_str}"
        )

    lines.append("=" * 90)


# ---------------------------------------------------------
# Extra: zoek statische verwijzingen naar de drie VA's.
# Dit kan constructors/vtables/call tables blootleggen.
# ---------------------------------------------------------

lines.append("")
lines.append("")
lines.append("LITERAL VA REFERENCES")
lines.append("=" * 90)

for name, rva in TARGETS.items():

    va = image_base + rva
    needle = struct.pack("<I", va)

    positions = []

    pos = 0

    while True:
        pos = data.find(needle, pos)

        if pos < 0:
            break

        positions.append(pos)
        pos += 1

    lines.append("")
    lines.append(
        f"{name}: VA=0x{va:08X} "
        f"refs={len(positions)}"
    )

    for p in positions[:50]:
        lines.append(
            f"  file offset 0x{p:08X}"
        )


OUT.parent.mkdir(
    parents=True,
    exist_ok=True
)

OUT.write_text(
    "\n".join(lines),
    encoding="utf-8"
)

print(f"Geschreven: {OUT}")
print("")
print("Targets:")
for name, rva in TARGETS.items():
    print(f"  {name}: RVA 0x{rva:08X}")
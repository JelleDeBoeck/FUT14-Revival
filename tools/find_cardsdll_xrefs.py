from pathlib import Path
import struct

DLL = Path(r"C:\Program Files\EA Games\FIFA 14\Game\CardsDLLzf.dll")

TERMS = [
    "data\\ui\\layout\\fut\\FutFluxHubCfg.xml",
    "data\\ui\\layout\\fut\\FutFluxHubWCCfg.xml",
    "external.ion_fut.components.Tile.Addon_GoToWC",
    "GOTO_WORLD_CUP",
]


def u16(data, off):
    return struct.unpack_from("<H", data, off)[0]


def u32(data, off):
    return struct.unpack_from("<I", data, off)[0]


def find_all(data, needle):
    hits = []
    pos = 0

    while True:
        pos = data.find(needle, pos)

        if pos == -1:
            break

        hits.append(pos)
        pos += 1

    return hits


data = DLL.read_bytes()

if data[:2] != b"MZ":
    raise RuntimeError("Geen geldig PE/MZ bestand")

pe_off = u32(data, 0x3C)

if data[pe_off:pe_off + 4] != b"PE\x00\x00":
    raise RuntimeError("PE signature niet gevonden")

coff = pe_off + 4

num_sections = u16(data, coff + 2)
size_optional = u16(data, coff + 16)

optional = coff + 20
magic = u16(data, optional)

if magic != 0x10B:
    raise RuntimeError(
        f"Dit script verwacht PE32, magic=0x{magic:X}"
    )

image_base = u32(data, optional + 28)

section_table = optional + size_optional

sections = []

for i in range(num_sections):
    off = section_table + i * 40

    name = data[off:off + 8]
    name = name.split(b"\x00", 1)[0].decode(
        "ascii",
        errors="replace",
    )

    virtual_size = u32(data, off + 8)
    virtual_address = u32(data, off + 12)
    raw_size = u32(data, off + 16)
    raw_ptr = u32(data, off + 20)

    sections.append({
        "name": name,
        "va": virtual_address,
        "vsize": virtual_size,
        "raw_size": raw_size,
        "raw_ptr": raw_ptr,
    })


def file_to_rva(file_offset):
    for section in sections:
        start = section["raw_ptr"]
        end = start + section["raw_size"]

        if start <= file_offset < end:
            return (
                section["va"]
                + (file_offset - start)
            )

    return None


def section_name(file_offset):
    for section in sections:
        start = section["raw_ptr"]
        end = start + section["raw_size"]

        if start <= file_offset < end:
            return section["name"]

    return "?"


def context(offset, radius=32):
    start = max(0, offset - radius)
    end = min(len(data), offset + 4 + radius)

    result = []

    for pos in range(start, end):
        if pos == offset:
            result.append("[")

        result.append(f"{data[pos]:02X}")

        if pos == offset + 3:
            result.append("]")

    return " ".join(result)


print(f"[INFO] DLL        : {DLL}")
print(f"[INFO] size       : {len(data):,}")
print(f"[INFO] image base : 0x{image_base:08X}")
print()

print("[SECTIONS]")

for section in sections:
    print(
        f"  {section['name']:<8} "
        f"RVA=0x{section['va']:08X} "
        f"RAW=0x{section['raw_ptr']:08X} "
        f"SIZE=0x{section['raw_size']:X}"
    )

print()

for term in TERMS:
    print("=" * 90)
    print(term)
    print("=" * 90)

    string_hits = find_all(
        data.lower(),
        term.lower().encode("ascii"),
    )

    if not string_hits:
        print("[STRING NOT FOUND]")
        print()
        continue

    for string_offset in string_hits:
        rva = file_to_rva(string_offset)

        print()
        print(
            f"String file offset : "
            f"0x{string_offset:X}"
        )

        print(
            f"String section     : "
            f"{section_name(string_offset)}"
        )

        if rva is None:
            print("RVA                : [UNKNOWN]")
            continue

        va = image_base + rva

        print(f"String RVA         : 0x{rva:08X}")
        print(f"String VA          : 0x{va:08X}")

        va_bytes = struct.pack("<I", va)
        rva_bytes = struct.pack("<I", rva)

        va_refs = find_all(data, va_bytes)
        rva_refs = find_all(data, rva_bytes)

        print()
        print(
            f"Absolute VA refs ({len(va_refs)}):"
        )

        if not va_refs:
            print("  [NONE]")

        for ref in va_refs:
            print(
                f"  file=0x{ref:X} "
                f"section={section_name(ref)}"
            )
            print(f"    {context(ref)}")

        print()
        print(f"RVA refs ({len(rva_refs)}):")

        if not rva_refs:
            print("  [NONE]")

        for ref in rva_refs:
            print(
                f"  file=0x{ref:X} "
                f"section={section_name(ref)}"
            )
            print(f"    {context(ref)}")

        print()

print("[DONE]")
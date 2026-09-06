from pathlib import Path
import struct

EXE = Path(r"C:\Program Files\EA Games\FIFA 14\Game\fifa14.exe")

TERMS = [
    "MAINHUB_FUT_DP",
    "USER_MSG_FUT_WC_HUB",
    "USER_MSG_FUT_FIFA_HUB",
    "ACTION_WORLDCUP_BUYNOW",
]


def u16(data, off):
    return struct.unpack_from("<H", data, off)[0]


def u32(data, off):
    return struct.unpack_from("<I", data, off)[0]


data = EXE.read_bytes()

# ----------------------------------------------------------------------
# PE header lezen
# ----------------------------------------------------------------------

if data[:2] != b"MZ":
    raise RuntimeError("Geen geldig MZ/PE bestand")

pe_off = u32(data, 0x3C)

if data[pe_off:pe_off + 4] != b"PE\x00\x00":
    raise RuntimeError("PE signature niet gevonden")

coff = pe_off + 4

num_sections = u16(data, coff + 2)
size_optional = u16(data, coff + 16)

optional = coff + 20
magic = u16(data, optional)

if magic == 0x10B:
    # PE32
    image_base = u32(data, optional + 28)
elif magic == 0x20B:
    raise RuntimeError("PE32+ aangetroffen; dit script verwacht FIFA 14 PE32")
else:
    raise RuntimeError(f"Onbekende optional-header magic: 0x{magic:X}")

section_table = optional + size_optional

sections = []

for i in range(num_sections):
    off = section_table + i * 40

    raw_name = data[off:off + 8]
    name = raw_name.split(b"\x00", 1)[0].decode(
        "ascii",
        errors="replace"
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


def file_offset_to_rva(file_offset):
    for s in sections:
        start = s["raw_ptr"]
        end = start + s["raw_size"]

        if start <= file_offset < end:
            return s["va"] + (file_offset - start)

    return None


def section_for_file_offset(file_offset):
    for s in sections:
        start = s["raw_ptr"]
        end = start + s["raw_size"]

        if start <= file_offset < end:
            return s["name"]

    return "?"


def find_all(blob, needle):
    hits = []
    start = 0

    while True:
        pos = blob.find(needle, start)

        if pos == -1:
            break

        hits.append(pos)
        start = pos + 1

    return hits


def hex_context(pos, radius=24):
    start = max(0, pos - radius)
    end = min(len(data), pos + 4 + radius)

    chunk = data[start:end]

    parts = []

    for i, b in enumerate(chunk):
        absolute = start + i

        if absolute == pos:
            parts.append("[")
        parts.append(f"{b:02X}")
        if absolute == pos + 3:
            parts.append("]")

    return " ".join(parts)


print(f"[INFO] bestand    : {EXE}")
print(f"[INFO] grootte    : {len(data):,}")
print(f"[INFO] image base : 0x{image_base:08X}")
print(f"[INFO] sections   : {num_sections}")

print()

for s in sections:
    print(
        f"  {s['name']:<8} "
        f"RVA=0x{s['va']:08X} "
        f"RAW=0x{s['raw_ptr']:08X} "
        f"SIZE=0x{s['raw_size']:X}"
    )

print()


# ----------------------------------------------------------------------
# Strings + references zoeken
# ----------------------------------------------------------------------

for term in TERMS:
    needle = term.encode("ascii")

    string_hits = find_all(data, needle)

    print("=" * 80)
    print(term)
    print("=" * 80)

    if not string_hits:
        print("[STRING NOT FOUND]")
        print()
        continue

    for string_offset in string_hits:
        rva = file_offset_to_rva(string_offset)

        print()
        print(f"String file offset : 0x{string_offset:X}")
        print(f"String section     : {section_for_file_offset(string_offset)}")

        if rva is None:
            print("RVA                : onbekend")
            continue

        va = image_base + rva

        print(f"String RVA         : 0x{rva:08X}")
        print(f"String VA          : 0x{va:08X}")

        va_bytes = struct.pack("<I", va)
        rva_bytes = struct.pack("<I", rva)

        va_refs = find_all(data, va_bytes)
        rva_refs = find_all(data, rva_bytes)

        # De string zelf kan toevallig dezelfde bytes bevatten;
        # alleen daadwerkelijke 4-byte waarden worden hier gevonden.

        print()
        print(f"Absolute VA refs ({len(va_refs)}):")

        if not va_refs:
            print("  [NONE]")

        for ref in va_refs[:50]:
            print(
                f"  file=0x{ref:X} "
                f"section={section_for_file_offset(ref)}"
            )
            print(f"    {hex_context(ref)}")

        if len(va_refs) > 50:
            print(f"  ... plus {len(va_refs) - 50} meer")

        print()
        print(f"RVA refs ({len(rva_refs)}):")

        if not rva_refs:
            print("  [NONE]")

        for ref in rva_refs[:50]:
            print(
                f"  file=0x{ref:X} "
                f"section={section_for_file_offset(ref)}"
            )
            print(f"    {hex_context(ref)}")

        if len(rva_refs) > 50:
            print(f"  ... plus {len(rva_refs) - 50} meer")

        print()

print("[DONE]")
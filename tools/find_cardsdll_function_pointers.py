from pathlib import Path
import struct

DLL = Path(r"C:\Program Files\EA Games\FIFA 14\Game\CardsDLLzf.dll")

TARGETS = {
    "WC_HUB_CFG_LOADER": 0x10086D10,
    "NORMAL_HUB_CFG_LOADER": 0x100883F0,
}


def u16(data, off):
    return struct.unpack_from("<H", data, off)[0]


def u32(data, off):
    return struct.unpack_from("<I", data, off)[0]


def find_all(data, needle):
    out = []
    pos = 0

    while True:
        pos = data.find(needle, pos)

        if pos == -1:
            break

        out.append(pos)
        pos += 1

    return out


data = DLL.read_bytes()

pe_off = u32(data, 0x3C)
coff = pe_off + 4

num_sections = u16(data, coff + 2)
size_optional = u16(data, coff + 16)

optional = coff + 20
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


def section_name(file_offset):
    for s in sections:
        start = s["raw_ptr"]
        end = start + s["raw_size"]

        if start <= file_offset < end:
            return s["name"]

    return "?"


def dump_dwords(center, radius=0x60):
    start = max(0, center - radius)
    end = min(len(data), center + radius)

    start &= ~3

    for pos in range(start, end, 4):
        if pos + 4 > len(data):
            break

        value = u32(data, pos)

        marker = ""

        if pos == center:
            marker = "  <== TARGET POINTER"

        print(
            f"    file=0x{pos:08X}  "
            f"value=0x{value:08X}"
            f"{marker}"
        )


print(f"[INFO] DLL : {DLL}")
print()


for name, va in TARGETS.items():

    print("=" * 90)
    print(name)
    print("=" * 90)

    needle = struct.pack("<I", va)
    refs = find_all(data, needle)

    print(f"Target VA : 0x{va:08X}")
    print(f"Refs      : {len(refs)}")
    print()

    if not refs:
        print("[NONE]")
        print()
        continue

    for i, ref in enumerate(refs, 1):

        print(
            f"[REF {i}] "
            f"file=0x{ref:X} "
            f"section={section_name(ref)}"
        )

        dump_dwords(ref)

        print()

print("[DONE]")
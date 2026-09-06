from pathlib import Path
import struct

DLL = Path(r"C:\Program Files\EA Games\FIFA 14\Game\CardsDLLzf.dll")

# File offsets van het begin van de twee kleine functies.
#
# Afgeleid uit de xref-context:
#   WC     string push @ 0x8611C
#   Normal string push @ 0x877FC
#
# De prologue "55 8B EC" begint 7 bytes eerder.
TARGETS = {
    "WC_HUB_CFG_LOADER": 0x86110,
    "NORMAL_HUB_CFG_LOADER": 0x877F0,
}


def u16(data, off):
    return struct.unpack_from("<H", data, off)[0]


def u32(data, off):
    return struct.unpack_from("<I", data, off)[0]


data = DLL.read_bytes()

if data[:2] != b"MZ":
    raise RuntimeError("Geen geldig MZ bestand")

pe_off = u32(data, 0x3C)

if data[pe_off:pe_off + 4] != b"PE\x00\x00":
    raise RuntimeError("PE signature niet gevonden")

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

    name = data[off:off + 8]
    name = name.split(b"\x00", 1)[0].decode(
        "ascii",
        errors="replace",
    )

    va = u32(data, off + 12)
    raw_size = u32(data, off + 16)
    raw_ptr = u32(data, off + 20)

    sections.append({
        "name": name,
        "va": va,
        "raw_size": raw_size,
        "raw_ptr": raw_ptr,
    })


def file_to_rva(file_offset):
    for s in sections:
        start = s["raw_ptr"]
        end = start + s["raw_size"]

        if start <= file_offset < end:
            return s["va"] + (file_offset - start)

    return None


def rva_to_file(rva):
    for s in sections:
        start = s["va"]
        end = start + s["raw_size"]

        if start <= rva < end:
            return s["raw_ptr"] + (rva - start)

    return None


def section_name(file_offset):
    for s in sections:
        start = s["raw_ptr"]
        end = start + s["raw_size"]

        if start <= file_offset < end:
            return s["name"]

    return "?"


def dump_hex(center, before=64, after=64):
    start = max(0, center - before)
    end = min(len(data), center + after)

    for row in range(start, end, 16):
        chunk = data[row:min(row + 16, end)]

        hexpart = " ".join(
            f"{b:02X}" for b in chunk
        )

        print(f"    0x{row:08X}: {hexpart}")


print(f"[INFO] DLL        : {DLL}")
print(f"[INFO] image base : 0x{image_base:08X}")
print()


for name, target_file in TARGETS.items():

    print("=" * 90)
    print(name)
    print("=" * 90)

    target_rva = file_to_rva(target_file)

    if target_rva is None:
        print(
            f"[ERROR] target file offset "
            f"0x{target_file:X} niet gemapt"
        )
        continue

    target_va = image_base + target_rva

    print(f"Target file : 0x{target_file:X}")
    print(f"Target RVA  : 0x{target_rva:08X}")
    print(f"Target VA   : 0x{target_va:08X}")
    print()

    callers = []

    # Zoek alle x86 near CALL instructies:
    #
    # E8 xx xx xx xx
    #
    # bestemming =
    # RVA_na_de_call + signed_rel32
    #
    for pos in range(len(data) - 5):

        if data[pos] != 0xE8:
            continue

        call_rva = file_to_rva(pos)

        if call_rva is None:
            continue

        rel = struct.unpack_from(
            "<i",
            data,
            pos + 1
        )[0]

        destination_rva = call_rva + 5 + rel

        if destination_rva == target_rva:
            callers.append(pos)

    print(f"CALLERS: {len(callers)}")
    print()

    if not callers:
        print("  [NONE]")
        print()
        continue

    for i, caller in enumerate(callers, 1):

        caller_rva = file_to_rva(caller)

        print(
            f"[CALLER {i}] "
            f"file=0x{caller:X} "
            f"RVA=0x{caller_rva:08X} "
            f"section={section_name(caller)}"
        )

        dump_hex(
            caller,
            before=96,
            after=96,
        )

        print()

print("[DONE]")
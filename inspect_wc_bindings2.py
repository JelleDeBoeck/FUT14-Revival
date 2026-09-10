from pathlib import Path
import struct

data = Path("CardsDLLzf_analysis.dll").read_bytes()
IMAGE_BASE = 0x10000000

sections = [
    (0x1000,   0x183200, 0x400),
    (0x185000, 0x32000,  0x183600),
    (0x1B7000, 0x1E400,  0x1B5600),
]

def rva_to_offset(rva):
    for va, raw_size, raw_ptr in sections:
        if va <= rva < va + raw_size:
            return raw_ptr + (rva - va)
    return None

def read_u32_rva(rva):
    off = rva_to_offset(rva)
    if off is None:
        return None
    return struct.unpack_from("<I", data, off)[0]

def read_cstr_va(va, limit=100):
    if not (IMAGE_BASE <= va < IMAGE_BASE + 0x300000):
        return None

    rva = va - IMAGE_BASE
    off = rva_to_offset(rva)
    if off is None:
        return None

    raw = data[off:off+limit]
    raw = raw.split(b"\x00", 1)[0]

    try:
        s = raw.decode("ascii")
    except:
        return None

    if not s:
        return None

    if all(32 <= ord(c) < 127 for c in s):
        return s

    return None


print("===== registration area around LoadActiveSquad =====")

for rva in range(0x1D6CC0, 0x1D6DC0, 4):
    value = read_u32_rva(rva)

    if value is None:
        continue

    extra = ""

    s = read_cstr_va(value)
    if s:
        extra = f'  STRING="{s}"'
    elif IMAGE_BASE <= value < IMAGE_BASE + 0x183200:
        extra = f"  CODE_RVA=0x{value-IMAGE_BASE:X}"

    print(
        f"RVA 0x{rva:07X}  "
        f"VA 0x{IMAGE_BASE+rva:08X}  "
        f"= 0x{value:08X}{extra}"
    )


print("\n===== nearby name strings =====")

for rva in range(0x195280, 0x195380):
    off = rva_to_offset(rva)
    if off is None:
        continue

    if data[off] < 32 or data[off] >= 127:
        continue

    if rva > 0x195280:
        prev = rva_to_offset(rva - 1)
        if prev is not None and 32 <= data[prev] < 127:
            continue

    raw = data[off:off+100].split(b"\x00", 1)[0]

    try:
        s = raw.decode("ascii")
    except:
        continue

    if len(s) >= 3:
        print(f"RVA 0x{rva:X}: {s}")


print("\n===== wrappers =====")

def dump(rva, size):
    off = rva_to_offset(rva)
    blob = data[off:off+size]

    print(f"\n--- RVA 0x{rva:X} ---")

    for i in range(0, len(blob), 16):
        b = blob[i:i+16]
        print(
            f"{IMAGE_BASE+rva+i:08X}  "
            + " ".join(f"{x:02X}" for x in b)
        )

for rva in [
    0x738E0,
    0x73AF0,
    0x73B20,
]:
    dump(rva, 0x50)

from pathlib import Path
import struct

data = Path("CardsDLLzf_analysis.dll").read_bytes()
BASE = 0x10000000

sections = [
    (0x1000,   0x183200, 0x400),
    (0x185000, 0x32000,  0x183600),
    (0x1B7000, 0x1E400,  0x1B5600),
]

def rva_off(rva):
    for va, size, raw in sections:
        if va <= rva < va + size:
            return raw + rva - va
    return None

def u32_rva(rva):
    o = rva_off(rva)
    if o is None:
        return None
    return struct.unpack_from("<I", data, o)[0]

# Zoek kandidaat-vtables waarvan +0x24 een codepointer is.
# Extra eis: omliggende slots +10..+40 moeten grotendeels
# eveneens naar .text wijzen. Zo filteren we de ruis sterk.
candidates = []

for rva in range(0x185000, 0x1DF000, 4):
    vals = []
    good = 0

    for slot in range(0x10, 0x44, 4):
        v = u32_rva(rva + slot)
        vals.append((slot, v))

        if v is not None and BASE+0x1000 <= v < BASE+0x183200:
            good += 1

    target = dict(vals).get(0x24)

    if (
        target is not None
        and BASE+0x1000 <= target < BASE+0x183200
        and good >= 8
    ):
        candidates.append((rva, vals))

print("===== VM vtable candidates =====")

for rva, vals in candidates:
    print(f"\nVTABLE RVA 0x{rva:X}")
    for slot, va in vals:
        if va is None:
            continue
        if BASE+0x1000 <= va < BASE+0x183200:
            print(
                f"  +0x{slot:02X} -> "
                f"RVA 0x{va-BASE:X}"
            )

print(f"\nTOTAL={len(candidates)}")

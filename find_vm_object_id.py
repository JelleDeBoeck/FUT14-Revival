from pathlib import Path
import struct

data = Path("CardsDLLzf_analysis.dll").read_bytes()

BASE = 0x10000000
VALUE = 0x084A36BC
needle = struct.pack("<I", VALUE)

# PE mapping voor relevante secties
sections = [
    (0x1000,   0x183200, 0x400),
    (0x185000, 0x32000,  0x183600),
    (0x1B7000, 0x1E400,  0x1B5600),
]

def raw_to_rva(raw):
    for va, size, roff in sections:
        if roff <= raw < roff + size:
            return va + (raw - roff)
    return None

hits = []
p = 0

while True:
    p = data.find(needle, p)
    if p < 0:
        break
    hits.append(p)
    p += 1

print("===== refs to 0x084A36BC =====")
print("TOTAL =", len(hits))

for raw in hits:
    rva = raw_to_rva(raw)

    if rva is None:
        print(f"\nfile offset 0x{raw:X} (unmapped)")
        continue

    print(
        f"\n--- RVA 0x{rva:X} / "
        f"VA 0x{BASE+rva:X} / raw 0x{raw:X} ---"
    )

    start = max(0, raw - 0x40)
    end = min(len(data), raw + 0x50)
    blob = data[start:end]

    start_rva = raw_to_rva(start)

    if start_rva is None:
        continue

    for i in range(0, len(blob), 16):
        b = blob[i:i+16]
        print(
            f"{BASE+start_rva+i:08X}  "
            + " ".join(f"{x:02X}" for x in b)
        )

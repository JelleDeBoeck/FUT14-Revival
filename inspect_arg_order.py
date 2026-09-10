from pathlib import Path

data = Path("CardsDLLzf_analysis.dll").read_bytes()
IMAGE_BASE = 0x10000000

def rva_to_offset(rva):
    sections = [
        (0x1000,   0x183200, 0x400),
        (0x185000, 0x32000,  0x183600),
        (0x1B7000, 0x1E400,  0x1B5600),
    ]
    for va, size, raw in sections:
        if va <= rva < va + size:
            return raw + (rva - va)
    raise ValueError(hex(rva))

def dump(rva, size):
    off = rva_to_offset(rva)
    blob = data[off:off+size]

    print(
        f"===== RVA 0x{rva:X} / "
        f"VA 0x{IMAGE_BASE+rva:X} ====="
    )

    for i in range(0, len(blob), 16):
        b = blob[i:i+16]
        print(
            f"{IMAGE_BASE+rva+i:08X}  "
            + " ".join(f"{x:02X}" for x in b)
        )

# Volledige AddPlayerToSquad wrapper + volgende binding.
dump(0x73B20, 0x180)

# Argument helper family rond 1AAD0.
dump(0x1AA80, 0xC0)

from pathlib import Path

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
    raise ValueError(hex(rva))

def dump(rva, size):
    off = rva_to_offset(rva)
    blob = data[off:off + size]

    print(
        f"===== RVA 0x{rva:X} "
        f"/ VA 0x{IMAGE_BASE+rva:X} ====="
    )

    for i in range(0, len(blob), 16):
        b = blob[i:i+16]
        hx = " ".join(f"{x:02X}" for x in b)
        asc = "".join(
            chr(x) if 32 <= x < 127 else "."
            for x in b
        )
        print(
            f"{IMAGE_BASE+rva+i:08X}  "
            f"{hx:<47}  {asc}"
        )

# Rest van LoadActiveSquad:
dump(0xA8080, 0x180)

# Volledige interessante staart van completion handler:
dump(0xA6B80, 0x180)

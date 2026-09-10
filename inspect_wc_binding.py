from pathlib import Path
import struct

DLL = Path("CardsDLLzf_analysis.dll")
data = DLL.read_bytes()

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
    raise ValueError(f"RVA 0x{rva:X} not mapped")

def dump(rva, size):
    off = rva_to_offset(rva)
    blob = data[off:off+size]

    print(f"\n===== RVA 0x{rva:X} / VA 0x{IMAGE_BASE+rva:X} =====")
    for i in range(0, len(blob), 16):
        b = blob[i:i+16]
        hx = " ".join(f"{x:02X}" for x in b)
        asc = "".join(chr(x) if 32 <= x < 127 else "." for x in b)
        print(f"{IMAGE_BASE+rva+i:08X}  {hx:<47}  {asc}")

for rva, size in [
    (0x73AF0, 0x40),   # AS LoadActiveSquad binding
    (0x75250, 0x60),   # wrapper -> FutSquadServiceImpl
    (0xA7F90, 0x100),  # actual LoadActiveSquad implementation
    (0xA6A50, 0x180),  # completion/event routing
    (0x1AAD0, 0x30),   # script argument getter
]:
    dump(rva, size)

# Zoek alle absolute references naar the LoadActiveSquad binding metadata.
needle = struct.pack("<I", IMAGE_BASE + 0x19530C)
print("\n===== refs to VA 0x1019530C ('LoadActiveSquad') =====")
start = 0
while True:
    pos = data.find(needle, start)
    if pos < 0:
        break
    print(f"raw file offset = 0x{pos:X}")
    start = pos + 1

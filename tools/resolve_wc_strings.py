from pathlib import Path
import struct

DLL = Path(r"C:\Program Files\EA Games\FIFA 14\Game\CardsDLLzf.dll")
data = DLL.read_bytes()

IMAGE_BASE = 0x10000000

# Uit onze PE-analyse:
RDATA_RVA = 0x185000
RDATA_RAW = 0x183600

addresses = [
    0x10197014,
    0x10196FDC,
    0x10198B84,
    0x101938F8,
    0x10197AEC,
]

def va_to_file(va):
    rva = va - IMAGE_BASE
    return RDATA_RAW + (rva - RDATA_RVA)

for va in addresses:
    off = va_to_file(va)

    end = data.find(b"\x00", off)
    if end == -1:
        text = "<geen terminator>"
    else:
        text = data[off:end].decode("ascii", errors="replace")

    print(f"0x{va:08X} -> file 0x{off:08X} -> {text!r}")
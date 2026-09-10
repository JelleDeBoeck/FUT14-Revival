from pathlib import Path

data = Path("CardsDLLzf_analysis.dll").read_bytes()

RDATA_RVA = 0x185000
RDATA_RAW = 0x183600

needle = b"SaveSquad\x00"

p = 0
while True:
    p = data.find(needle, p)
    if p < 0:
        break

    if RDATA_RAW <= p:
        rva = RDATA_RVA + (p - RDATA_RAW)
        print(
            f"SaveSquad string: "
            f"RVA 0x{rva:X} / VA 0x{0x10000000+rva:X}"
        )
    else:
        print(f"SaveSquad raw hit: 0x{p:X}")

    p += 1

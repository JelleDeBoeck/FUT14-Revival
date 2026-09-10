from pathlib import Path

data = Path("CardsDLLzf_analysis.dll").read_bytes()

BASE = 0x10000000

RVA  = 0x185250
SIZE = 0x1C0

# .rdata
RAW_BASE = 0x183600
RVA_BASE = 0x185000

off = RAW_BASE + (RVA - RVA_BASE)
blob = data[off:off+SIZE]

print("===== .rdata 0x185250 - 0x185410 =====")

for i in range(0, len(blob), 16):
    b = blob[i:i+16]

    hx = " ".join(f"{x:02X}" for x in b)

    asc = "".join(
        chr(x) if 32 <= x < 127 else "."
        for x in b
    )

    print(
        f"{BASE+RVA+i:08X}  "
        f"{hx:<47}  {asc}"
    )

print("\n===== pointer targets =====")

for rva in [
    0x185294,
    0x1852B0,
    0x1852C0,
    0x1852CC,
]:
    o = RAW_BASE + (rva - RVA_BASE)

    s = bytearray()

    while o < len(data) and len(s) < 128:
        c = data[o]
        if c == 0:
            break
        s.append(c)
        o += 1

    print(
        f"RVA 0x{rva:X}: "
        + s.decode("ascii", errors="replace")
    )

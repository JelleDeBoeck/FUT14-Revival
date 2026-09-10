from pathlib import Path
import struct

data = Path("CardsDLLzf_analysis.dll").read_bytes()
BASE = 0x10000000

# Zoek directe machine-code references naar global 0x101D5390
needle = struct.pack("<I", 0x101D5390)

print("refs to global 0x101D5390:")

p = 0
hits = []

while True:
    p = data.find(needle, p)
    if p < 0:
        break

    hits.append(p)
    print(f"file offset 0x{p:X}")
    p += 1

print(f"\nTOTAL = {len(hits)}")

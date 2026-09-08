from pathlib import Path
import struct

APT = Path(
    r"D:\Afbeeldingen\FUT14-Revival\extracted\helperfunctions_inner\00_0"
)

data = APT.read_bytes()

# Zoek alle LE DWORDs met de waarde 0x0C1C.
target = 0x0C1C

print(f"APT size = 0x{len(data):X}")
print(f"TARGET   = 0x{target:X}")
print()

hits = []

for off in range(0, len(data) - 3, 4):
    v = struct.unpack_from("<I", data, off)[0]
    if v == target:
        hits.append(off)

print(f"HITS = {len(hits)}")
for off in hits:
    lo = max(0, off - 32)
    hi = min(len(data), off + 36)

    print()
    print(f"APT+0x{off:X}")
    print(" ".join(f"{b:02X}" for b in data[lo:hi]))

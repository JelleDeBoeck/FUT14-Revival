from pathlib import Path
import struct

SRC = Path(
    r"D:\Afbeeldingen\FUT14-Revival\extracted\main_inner\00_0"
)

data = SRC.read_bytes()

TABLE = 0x1BC
COUNT = 11

offsets = [
    struct.unpack_from("<I", data, TABLE + i * 4)[0]
    for i in range(COUNT)
]

print("[OFFSETS]")
for i, off in enumerate(offsets):
    print(f"{i:2}: 0x{off:05X}")

print()

for i, start in enumerate(offsets):
    end = offsets[i + 1] if i + 1 < len(offsets) else min(start + 0x80, len(data))

    print("=" * 72)
    print(f"RECORD {i}: 0x{start:05X} .. 0x{end:05X} ({end-start} bytes)")
    print("=" * 72)

    blob = data[start:end]

    for rel in range(0, len(blob), 16):
        chunk = blob[rel:rel + 16]

        hexpart = " ".join(f"{b:02X}" for b in chunk)
        asciipart = "".join(
            chr(b) if 0x20 <= b < 0x7F else "."
            for b in chunk
        )

        print(
            f"0x{start + rel:05X}  "
            f"{hexpart:<47}  "
            f"{asciipart}"
        )

    print()
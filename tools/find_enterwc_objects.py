from pathlib import Path
import struct

SRC = Path(
    r"D:\Afbeeldingen\FUT14-Revival"
    r"\extracted\enterwc_inner\00_0"
)

data = SRC.read_bytes()

print(f"[INFO] size = 0x{len(data):X}")
print()

candidates = []

# Zoek DWORDs die eruitzien als interne file-offsets.
# We nemen alleen offsets:
# - binnen het bestand
# - 4-byte aligned
# - niet in de eerste 0x100 bytes zelf
for pos in range(0, min(0x200, len(data) - 3), 4):
    value = struct.unpack_from("<I", data, pos)[0]

    if value < 0x100:
        continue

    if value >= len(data):
        continue

    if value % 4 != 0:
        continue

    candidates.append((pos, value))

print("[CANDIDATE INTERNAL OFFSETS]")

for pos, value in candidates:
    print(
        f"header+0x{pos:03X} -> "
        f"0x{value:04X}"
    )

print()

print("[UNIQUE TARGETS]")

targets = sorted({
    value
    for _, value in candidates
})

for value in targets:
    blob = data[value:value + 16]

    print(
        f"0x{value:04X}  "
        f"{blob.hex(' ')}"
    )
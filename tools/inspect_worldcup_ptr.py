from pathlib import Path
import struct

CONST = Path(
    r"D:\Afbeeldingen\FUT14-Revival\extracted\helperfunctions_inner\02_1"
)

data = CONST.read_bytes()

target = 0x3404

print(f"CONST size = 0x{len(data):X}")
print(f"TARGET    = 0x{target:X}")
print()

for off in range(0xC1C - 0x40, 0xC1C + 0x80, 4):
    if off + 4 > len(data):
        break

    v = struct.unpack_from("<I", data, off)[0]

    print(
        f"CONST+0x{off:04X}: "
        f"{v:08X}"
        + ("  <-- TARGET OFFSET" if v == target else "")
    )

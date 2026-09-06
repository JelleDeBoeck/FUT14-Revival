from pathlib import Path
import struct

SRC = Path(
    r"D:\Afbeeldingen\FUT14-Revival\extracted\globalframework_inner\00_0"
)

data = SRC.read_bytes()

OBJECTS = {
    1: 0x106D0,
    2: 0x0A98,
    3: 0x0D4C,
    4: 0x1484,
    5: 0x1918,
    6: 0x1C80,
    7: 0x2038,
    8: 0x22F4,
    9: 0x2364,
    10: 0x2C78,
    11: 0x4EDC,
    12: 0x56BC,
    13: 0x5750,
    14: 0x5A18,
    15: 0x5AC0,
    16: 0x620C,
    17: 0x6BF4,
    18: 0x7534,
    19: 0x7D64,
    20: 0xC014,
    21: 0xCAC0,
    22: 0xD028,
    23: 0xDF5C,
    24: 0xE7C4,
}

for obj_id, off in OBJECTS.items():
    print("=" * 70)
    print(f"OBJECT {obj_id:2} @ 0x{off:05X}")
    print("=" * 70)

    for p in range(off, min(off + 0x40, len(data)), 4):
        value = struct.unpack_from("<I", data, p)[0]
        raw = data[p:p+4]

        print(
            f"0x{p:05X}: "
            f"{raw.hex(' ').upper():11} "
            f"0x{value:08X}"
        )

    print()